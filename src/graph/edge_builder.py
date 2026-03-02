"""Edge builder — KU 간 관계(edge) 후보 선정 + LLM 판정.

2-Tier 접근:
  Tier 1: Within-chapter (전수) — 같은 챕터 내 top-k
  Tier 2: Cross-chapter (centroid 샘플링) — 챕터 대표 KU 간 연결
  Cross-domain: 도메인 간 centroid 연결
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from src.db.models import get_ku, insert_edge
from src.ingest.llm_cache import get_or_call

load_dotenv()

logger = logging.getLogger(__name__)

RELATION_TYPES = [
    "supports",
    "contradicts",
    "extends",
    "explains",
    "example_of",
    "analogous_to",
]

EDGE_JUDGE_SYSTEM_PROMPT = """\
You are a knowledge graph expert. Given two Knowledge Units (KU_A and KU_B), \
determine their relationship.

Respond ONLY with a JSON object:
{
  "relation_type": "supports|contradicts|extends|explains|example_of|analogous_to|none",
  "strength": <float 0.0-1.0>,
  "description": "<1-sentence description of the relationship>"
}

Relation types:
- supports: KU_B provides evidence or reinforcement for KU_A's claim
- contradicts: KU_B challenges or opposes KU_A's claim
- extends: KU_B builds upon or adds nuance to KU_A
- explains: KU_B provides mechanism or reasoning for KU_A
- example_of: KU_B is a concrete instance of KU_A's general principle
- analogous_to: KU_A and KU_B describe similar patterns in different contexts
- none: No meaningful relationship

If the relationship is "none" or too weak (strength < 0.3), set relation_type to "none".
"""


def _get_chapter_kus(conn, book_id: str) -> dict[str, list[dict]]:
    """책의 KU를 챕터별로 그룹화. source_spans에서 챕터 추출."""
    rows = conn.execute(
        "SELECT * FROM knowledge_units WHERE book_id = ? ORDER BY id",
        (book_id,),
    ).fetchall()

    chapter_kus: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        d = dict(row)
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        d["source_spans"] = json.loads(d["source_spans"]) if d["source_spans"] else []

        # 챕터 추출: source_spans의 첫 번째에서 ch## 패턴
        chapter = "unknown"
        if d["source_spans"]:
            # span ID format: {book_id}-ch{##}-p{###}-s{###}
            span_id = d["source_spans"][0]
            parts = span_id.split("-")
            for part in parts:
                if part.startswith("ch"):
                    chapter = part
                    break
        chapter_kus[chapter].append(d)

    return chapter_kus


def _get_all_kus(conn) -> list[dict]:
    """모든 KU 가져오기."""
    rows = conn.execute(
        "SELECT * FROM knowledge_units ORDER BY id"
    ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        d["source_spans"] = json.loads(d["source_spans"]) if d["source_spans"] else []
        results.append(d)
    return results


def _get_embeddings_by_ids(col, ku_ids: list[str]) -> dict[str, list[float]]:
    """ChromaDB에서 KU ID별 임베딩 벡터 가져오기."""
    if not ku_ids:
        return {}
    result = col.get(ids=ku_ids, include=["embeddings"])
    return dict(zip(result["ids"], result["embeddings"]))


def _compute_centroids(
    col, chapter_kus: dict[str, list[dict]], centroids_per_ch: int = 5
) -> dict[str, list[dict]]:
    """각 챕터에서 centroid KU 선정.

    알고리즘: 챕터 내 모든 KU 임베딩의 평균 벡터 계산 →
    평균 벡터와 가장 가까운 KU centroids_per_ch개 선정.
    """
    chapter_centroids: dict[str, list[dict]] = {}

    for chapter, kus in chapter_kus.items():
        if len(kus) <= centroids_per_ch:
            chapter_centroids[chapter] = kus
            continue

        ku_ids = [ku["id"] for ku in kus]
        embeddings = _get_embeddings_by_ids(col, ku_ids)

        if not embeddings:
            chapter_centroids[chapter] = kus[:centroids_per_ch]
            continue

        # 평균 벡터 계산
        vectors = [embeddings[kid] for kid in ku_ids if kid in embeddings]
        if not vectors:
            chapter_centroids[chapter] = kus[:centroids_per_ch]
            continue

        centroid_vec = np.mean(vectors, axis=0)

        # cosine similarity로 가장 가까운 KU 선정
        similarities = []
        for ku in kus:
            if ku["id"] in embeddings:
                vec = np.array(embeddings[ku["id"]])
                norm_a = np.linalg.norm(centroid_vec)
                norm_b = np.linalg.norm(vec)
                if norm_a > 0 and norm_b > 0:
                    sim = float(np.dot(centroid_vec, vec) / (norm_a * norm_b))
                else:
                    sim = 0.0
                similarities.append((ku, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        chapter_centroids[chapter] = [s[0] for s in similarities[:centroids_per_ch]]

    return chapter_centroids


def find_within_chapter_candidates(
    col, conn, book_id: str, top_k: int = 5, threshold: float = 0.35
) -> list[tuple[str, str, float]]:
    """Tier 1: 같은 챕터 내 KU 간 후보 쌍 검색.

    각 KU → 같은 챕터 내 ChromaDB top-k 검색, threshold 필터.
    Returns: [(ku_a_id, ku_b_id, similarity), ...]
    """
    chapter_kus = _get_chapter_kus(conn, book_id)
    candidates: list[tuple[str, str, float]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for chapter, kus in chapter_kus.items():
        if len(kus) < 2:
            continue

        ku_ids = [ku["id"] for ku in kus]
        embeddings = _get_embeddings_by_ids(col, ku_ids)

        for ku in kus:
            if ku["id"] not in embeddings:
                continue

            query_emb = embeddings[ku["id"]]

            # ChromaDB query with book_id filter — 같은 챕터 내 KU만
            # ChromaDB에는 챕터 메타데이터가 없으므로 ku_ids로 필터
            results = col.query(
                query_embeddings=[query_emb],
                n_results=min(top_k + 1, len(ku_ids)),  # +1 for self
                include=["distances"],
                where={"book_id": book_id},
            )

            if not results["ids"] or not results["ids"][0]:
                continue

            for rid, dist in zip(results["ids"][0], results["distances"][0]):
                if rid == ku["id"]:
                    continue
                if rid not in ku_ids:  # 같은 챕터 아닌 KU 제외
                    continue

                similarity = 1.0 - dist  # cosine distance → similarity
                if similarity < threshold:
                    continue

                pair = tuple(sorted([ku["id"], rid]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                candidates.append((ku["id"], rid, similarity))

    logger.info(
        "Within-chapter candidates for %s: %d pairs", book_id, len(candidates)
    )
    return candidates


def find_cross_chapter_candidates(
    col, conn, book_id: str,
    centroids_per_ch: int = 5, top_k: int = 3, threshold: float = 0.35
) -> list[tuple[str, str, float]]:
    """Tier 2: 챕터 간 centroid KU 연결 후보.

    각 챕터 centroid → 다른 챕터 centroid와 top-k 검색.
    """
    chapter_kus = _get_chapter_kus(conn, book_id)
    chapter_centroids = _compute_centroids(col, chapter_kus, centroids_per_ch)

    # 모든 centroid KU id 수집
    all_centroid_ids: set[str] = set()
    chapter_of_ku: dict[str, str] = {}
    for chapter, kus in chapter_centroids.items():
        for ku in kus:
            all_centroid_ids.add(ku["id"])
            chapter_of_ku[ku["id"]] = chapter

    centroid_embeddings = _get_embeddings_by_ids(col, list(all_centroid_ids))

    candidates: list[tuple[str, str, float]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for chapter, centroids in chapter_centroids.items():
        for ku in centroids:
            if ku["id"] not in centroid_embeddings:
                continue

            query_emb = centroid_embeddings[ku["id"]]
            results = col.query(
                query_embeddings=[query_emb],
                n_results=top_k + len(chapter_centroids.get(chapter, [])) + 1,
                include=["distances"],
                where={"book_id": book_id},
            )

            if not results["ids"] or not results["ids"][0]:
                continue

            count = 0
            for rid, dist in zip(results["ids"][0], results["distances"][0]):
                if count >= top_k:
                    break
                if rid == ku["id"]:
                    continue
                # 다른 챕터의 centroid만
                if rid not in all_centroid_ids:
                    continue
                if chapter_of_ku.get(rid) == chapter:
                    continue

                similarity = 1.0 - dist
                if similarity < threshold:
                    continue

                pair = tuple(sorted([ku["id"], rid]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                candidates.append((ku["id"], rid, similarity))
                count += 1

    logger.info(
        "Cross-chapter candidates for %s: %d pairs", book_id, len(candidates)
    )
    return candidates


def find_cross_domain_candidates(
    col, conn, centroids_per_ch: int = 5, top_k: int = 3, threshold: float = 0.35
) -> list[tuple[str, str, float]]:
    """Cross-domain: 각 책의 centroid → 다른 도메인 전체에서 top-k 검색."""
    # 모든 책 가져오기
    books = conn.execute("SELECT * FROM books").fetchall()
    books = [dict(b) for b in books]

    if len(books) < 2:
        logger.info("Cross-domain: need at least 2 books, found %d", len(books))
        return []

    # 각 책의 centroid 수집
    book_centroids: dict[str, list[dict]] = {}
    book_domain: dict[str, str] = {}
    all_centroid_ids: set[str] = set()

    for book in books:
        chapter_kus = _get_chapter_kus(conn, book["id"])
        centroids = _compute_centroids(col, chapter_kus, centroids_per_ch)
        flat_centroids = [ku for kus in centroids.values() for ku in kus]
        book_centroids[book["id"]] = flat_centroids
        book_domain[book["id"]] = book["domain"]
        for ku in flat_centroids:
            all_centroid_ids.add(ku["id"])

    centroid_embeddings = _get_embeddings_by_ids(col, list(all_centroid_ids))

    candidates: list[tuple[str, str, float]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for book in books:
        my_domain = book_domain[book["id"]]
        for ku in book_centroids[book["id"]]:
            if ku["id"] not in centroid_embeddings:
                continue

            query_emb = centroid_embeddings[ku["id"]]

            # 다른 도메인의 모든 KU에서 검색
            other_domains = [
                b["domain"] for b in books if b["domain"] != my_domain
            ]
            if not other_domains:
                continue

            results = col.query(
                query_embeddings=[query_emb],
                n_results=top_k * 3,  # 여유분 확보
                include=["distances", "metadatas"],
            )

            if not results["ids"] or not results["ids"][0]:
                continue

            count = 0
            for rid, dist, meta in zip(
                results["ids"][0],
                results["distances"][0],
                results["metadatas"][0],
            ):
                if count >= top_k:
                    break
                if rid == ku["id"]:
                    continue

                # 같은 도메인 제외 — book_id에서 도메인 추론
                rid_book = meta.get("book_id", "")
                rid_domain = book_domain.get(rid_book, "")
                if rid_domain == my_domain:
                    continue

                similarity = 1.0 - dist
                if similarity < threshold:
                    continue

                pair = tuple(sorted([ku["id"], rid]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                candidates.append((ku["id"], rid, similarity))
                count += 1

    logger.info("Cross-domain candidates: %d pairs", len(candidates))
    return candidates


def judge_edge(
    client: OpenAI,
    ku_a_data: dict,
    ku_b_data: dict,
    model: str = "gpt-4.1-mini",
    cache_db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """LLM으로 두 KU 간 관계 판정.

    Returns: {"relation_type", "strength", "description"} or None (관계 없음)
    """
    user_text = (
        f"KU_A:\n"
        f"  ID: {ku_a_data['id']}\n"
        f"  Domain: {ku_a_data.get('domain', '')}\n"
        f"  Claim: {ku_a_data.get('claim', '')}\n"
        f"  Evidence: {ku_a_data.get('evidence_summary', '')}\n"
        f"\n"
        f"KU_B:\n"
        f"  ID: {ku_b_data['id']}\n"
        f"  Domain: {ku_b_data.get('domain', '')}\n"
        f"  Claim: {ku_b_data.get('claim', '')}\n"
        f"  Evidence: {ku_b_data.get('evidence_summary', '')}\n"
    )

    response_text = get_or_call(
        client,
        model,
        EDGE_JUDGE_SYSTEM_PROMPT,
        user_text,
        temperature=0.2,
        max_tokens=300,
        cache_db_path=cache_db_path,
    )

    try:
        # JSON 파싱 (markdown 코드블록 제거)
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response: %s", response_text[:100])
        return None

    relation = result.get("relation_type", "none")
    if relation == "none" or relation not in RELATION_TYPES:
        return None

    strength = float(result.get("strength", 0.5))
    if strength < 0.3:
        return None

    return {
        "relation_type": relation,
        "strength": strength,
        "description": result.get("description", ""),
    }


def _make_edge_id(from_ku_id: str, to_ku_id: str) -> str:
    """Edge ID 생성: edge-{from_ku_short}-{to_ku_short}."""
    # ku-econ-001-0042 → econ-001-0042
    from_short = from_ku_id.replace("ku-", "", 1)
    to_short = to_ku_id.replace("ku-", "", 1)
    return f"edge-{from_short}-{to_short}"


def build_edges(
    conn,
    col,
    candidates: list[tuple[str, str, float]],
    *,
    model: str = "gpt-4.1-mini",
    cache_db_path: str | Path | None = None,
    max_workers: int = 5,
    source: str = "auto",
) -> dict[str, Any]:
    """후보 쌍에 대해 LLM 판정 → edge 생성.

    ThreadPoolExecutor 패턴 (ku_extractor.py와 동일).
    KU 데이터를 미리 로드하여 쓰레드에서 SQLite 접근 방지.
    Returns: {"total_candidates", "edges_created", "edges_rejected"}
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    total = len(candidates)
    logger.info("Building edges: %d candidates, workers=%d", total, max_workers)

    # KU 데이터 미리 로드 (메인 쓰레드에서 SQLite 접근)
    needed_ids = set()
    for a, b, _ in candidates:
        needed_ids.add(a)
        needed_ids.add(b)
    ku_cache: dict[str, dict | None] = {}
    for kid in needed_ids:
        ku_cache[kid] = get_ku(conn, kid)
    logger.info("Pre-loaded %d KU records for edge judging", len(ku_cache))

    def _judge_one(idx: int, ku_a_id: str, ku_b_id: str, sim: float):
        ku_a = ku_cache.get(ku_a_id)
        ku_b = ku_cache.get(ku_b_id)
        if not ku_a or not ku_b:
            return idx, None
        result = judge_edge(client, ku_a, ku_b, model, cache_db_path)
        if result:
            result["from_ku_id"] = ku_a_id
            result["to_ku_id"] = ku_b_id
            result["similarity"] = sim
        return idx, result

    # LLM 판정 (병렬)
    judgments: list[dict | None] = [None] * total

    if max_workers > 1 and total > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_judge_one, i, a, b, s): i
                for i, (a, b, s) in enumerate(candidates)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    _, result = future.result()
                    judgments[idx] = result
                except Exception as e:
                    logger.error("Edge judge error at %d: %s", idx, e)
                if (idx + 1) % 50 == 0:
                    logger.info("Progress: %d/%d judged", idx + 1, total)
    else:
        for i, (a, b, s) in enumerate(candidates):
            _, result = _judge_one(i, a, b, s)
            judgments[i] = result
            if (i + 1) % 50 == 0:
                logger.info("Progress: %d/%d judged", i + 1, total)

    # DB 저장 (순차)
    edges_created = 0
    for j in judgments:
        if j is None:
            continue
        edge_id = _make_edge_id(j["from_ku_id"], j["to_ku_id"])
        insert_edge(
            conn,
            id=edge_id,
            from_ku_id=j["from_ku_id"],
            to_ku_id=j["to_ku_id"],
            relation_type=j["relation_type"],
            strength=j["strength"],
            source=source,
            description=j["description"],
        )
        edges_created += 1

    metrics = {
        "total_candidates": total,
        "edges_created": edges_created,
        "edges_rejected": total - edges_created,
    }
    logger.info(
        "Edge building done: %d created, %d rejected out of %d candidates",
        edges_created, total - edges_created, total,
    )
    return metrics
