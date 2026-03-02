"""Dispute Axis 자동 요약 — contradicts edge 클러스터링 + LLM 요약.

contradicts edge를 임베딩 기반으로 클러스터링하고,
각 클러스터에 대해 LLM이 "논쟁 축(dispute axis)" 이름과 설명을 생성.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from sklearn.cluster import AgglomerativeClustering

from src.graph.edge_builder import _get_embeddings_by_ids
from src.ingest.llm_cache import get_or_call

load_dotenv()

logger = logging.getLogger(__name__)

AXIS_SUMMARY_SYSTEM_PROMPT = """\
You are a knowledge graph analyst. Given pairs of contradicting knowledge claims, \
identify the underlying dispute axis (논쟁 축).

Respond ONLY with a JSON object:
{
  "axis_name": "<concise name for the dispute axis, in Korean>",
  "description": "<1-2 sentence summary of the dispute, in Korean>",
  "stance_a": "<core argument of one side, in Korean>",
  "stance_b": "<core argument of the opposing side, in Korean>"
}

Guidelines:
- axis_name should capture the fundamental tension (e.g., "시장 효율성 vs 행동경제학")
- description should explain why this dispute matters
- stance_a and stance_b should be balanced and fair representations
"""

MIN_CLUSTER_SIZE = 10


def load_contradicts(conn) -> list[dict]:
    """edges 테이블에서 relation_type='contradicts' 전체 로드.

    양쪽 KU의 claim, domain, book_id를 조인하여 반환.
    """
    rows = conn.execute("""
        SELECT
            e.id AS edge_id,
            e.from_ku_id,
            e.to_ku_id,
            e.strength,
            e.description AS edge_desc,
            a.claim AS from_claim,
            a.domain AS from_domain,
            a.book_id AS from_book_id,
            b.claim AS to_claim,
            b.domain AS to_domain,
            b.book_id AS to_book_id
        FROM edges e
        JOIN knowledge_units a ON e.from_ku_id = a.id
        JOIN knowledge_units b ON e.to_ku_id = b.id
        WHERE e.relation_type = 'contradicts'
        ORDER BY e.strength DESC
    """).fetchall()

    results = [dict(r) for r in rows]
    logger.info("Loaded %d contradicts edges", len(results))
    return results


def cluster_disputes(
    contradicts: list[dict],
    col,
    *,
    distance_threshold: float = 0.5,
) -> list[dict]:
    """contradicts edge를 임베딩 기반 클러스터링.

    각 edge의 "dispute vector" = mean(from_ku_emb, to_ku_emb).
    AgglomerativeClustering으로 주제별 클러스터 생성.

    Returns: [{cluster_id, edges: [...], centroid_edge_idx}, ...]
    """
    if not contradicts:
        return []

    # 필요한 KU ID 수집
    all_ku_ids = set()
    for c in contradicts:
        all_ku_ids.add(c["from_ku_id"])
        all_ku_ids.add(c["to_ku_id"])

    embeddings = _get_embeddings_by_ids(col, list(all_ku_ids))

    # dispute vector 계산
    vectors = []
    valid_edges = []
    for c in contradicts:
        from_emb = embeddings.get(c["from_ku_id"])
        to_emb = embeddings.get(c["to_ku_id"])
        if from_emb is None or to_emb is None:
            continue
        dispute_vec = np.mean([from_emb, to_emb], axis=0)
        vectors.append(dispute_vec)
        valid_edges.append(c)

    if len(valid_edges) < 2:
        if valid_edges:
            return [{"cluster_id": 0, "edges": valid_edges, "centroid_edge_idx": 0}]
        return []

    logger.info(
        "Clustering %d edges (%d skipped due to missing embeddings)",
        len(valid_edges),
        len(contradicts) - len(valid_edges),
    )

    X = np.array(vectors)

    # 정규화 (cosine distance를 위해)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_norm = X / norms

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(X_norm)

    # 클러스터별 그룹화
    cluster_map: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for idx, (label, edge) in enumerate(zip(labels, valid_edges)):
        cluster_map[int(label)].append((idx, edge))

    # 결과 정리 — centroid에 가장 가까운 edge 찾기
    results = []
    for cluster_id, items in sorted(cluster_map.items()):
        edge_indices = [i for i, _ in items]
        edges = [e for _, e in items]

        # 클러스터 centroid 계산
        cluster_vecs = X_norm[edge_indices]
        centroid = np.mean(cluster_vecs, axis=0)
        norm_c = np.linalg.norm(centroid)
        if norm_c > 0:
            centroid = centroid / norm_c

        # centroid에 가장 가까운 edge
        best_idx = 0
        best_sim = -1.0
        for i, vec in enumerate(cluster_vecs):
            sim = float(np.dot(centroid, vec))
            if sim > best_sim:
                best_sim = sim
                best_idx = i

        results.append({
            "cluster_id": cluster_id,
            "edges": edges,
            "centroid_edge_idx": best_idx,
        })

    logger.info(
        "Clustering done: %d clusters (min_size filter: >= %d)",
        len(results),
        MIN_CLUSTER_SIZE,
    )
    return results


def summarize_axis(
    client: OpenAI,
    cluster: dict,
    model: str = "gpt-4.1-mini",
    cache_db_path: str | Path | None = None,
) -> dict:
    """클러스터 내 대표 edge를 LLM에 전달하여 논쟁 축 요약.

    Returns: {axis_name, description, stance_a, stance_b, cluster_id, edge_count}
    """
    edges = cluster["edges"]
    # 대표 edge 최대 8건 선택 (strength 높은 순)
    sorted_edges = sorted(edges, key=lambda e: e["strength"], reverse=True)
    sample = sorted_edges[:8]

    pairs_text = []
    for i, edge in enumerate(sample, 1):
        pairs_text.append(
            f"Pair {i}:\n"
            f"  Claim A [{edge['from_ku_id']}]: {edge['from_claim']}\n"
            f"  Claim B [{edge['to_ku_id']}]: {edge['to_claim']}\n"
            f"  Strength: {edge['strength']:.2f}"
        )

    user_text = (
        f"The following {len(sample)} pairs of knowledge claims contradict each other.\n"
        f"Identify the common dispute axis:\n\n"
        + "\n\n".join(pairs_text)
    )

    response_text = get_or_call(
        client,
        model,
        AXIS_SUMMARY_SYSTEM_PROMPT,
        user_text,
        temperature=0.3,
        max_tokens=500,
        cache_db_path=cache_db_path,
    )

    # JSON 파싱
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse axis summary: %s", text[:100])
        result = {
            "axis_name": f"클러스터 {cluster['cluster_id']}",
            "description": "LLM 응답 파싱 실패",
            "stance_a": "",
            "stance_b": "",
        }

    # 도메인 수집
    domains = set()
    for edge in edges:
        domains.add(edge["from_domain"])
        domains.add(edge["to_domain"])

    return {
        "axis_name": result.get("axis_name", ""),
        "description": result.get("description", ""),
        "stance_a": result.get("stance_a", ""),
        "stance_b": result.get("stance_b", ""),
        "cluster_id": cluster["cluster_id"],
        "edge_count": len(edges),
        "domains": sorted(domains),
        "sample_pairs": [
            {
                "from_ku_id": e["from_ku_id"],
                "to_ku_id": e["to_ku_id"],
                "strength": e["strength"],
            }
            for e in sample[:5]
        ],
    }


def prepare_dispute_axes(
    conn,
    col,
    *,
    distance_threshold: float = 0.5,
) -> dict:
    """load + cluster 단계만 수행. LLM 호출 전에 클러스터 통계를 확인할 수 있도록 분리.

    Returns: {contradicts, main_clusters, small_clusters, total_edges, llm_calls_needed}
    """
    contradicts = load_contradicts(conn)
    if not contradicts:
        return {
            "contradicts": [],
            "main_clusters": [],
            "small_clusters": [],
            "total_edges": 0,
            "llm_calls_needed": 0,
        }

    clusters = cluster_disputes(
        contradicts, col, distance_threshold=distance_threshold
    )

    main_clusters = [c for c in clusters if len(c["edges"]) >= MIN_CLUSTER_SIZE]
    small_clusters = [c for c in clusters if len(c["edges"]) < MIN_CLUSTER_SIZE]

    logger.info(
        "Main clusters: %d, small clusters: %d (edges < %d)",
        len(main_clusters),
        len(small_clusters),
        MIN_CLUSTER_SIZE,
    )

    return {
        "contradicts": contradicts,
        "main_clusters": main_clusters,
        "small_clusters": small_clusters,
        "total_edges": len(contradicts),
        "llm_calls_needed": len(main_clusters),
    }


def summarize_clusters(
    main_clusters: list[dict],
    *,
    model: str = "gpt-4.1-mini",
    cache_db_path: str | Path | None = None,
    max_workers: int = 5,
) -> list[dict]:
    """클러스터 리스트에 대해 LLM 요약 (병렬).

    Returns: 논쟁 축 리스트 (edge_count 내림차순)
    """
    if not main_clusters:
        return []

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    axes: list[dict] = []

    def _summarize_one(cluster):
        return summarize_axis(client, cluster, model, cache_db_path)

    if max_workers > 1 and len(main_clusters) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_summarize_one, c): c["cluster_id"]
                for c in main_clusters
            }
            for future in as_completed(futures):
                cid = futures[future]
                try:
                    axis = future.result()
                    axes.append(axis)
                except Exception as e:
                    logger.error("Summarize error for cluster %d: %s", cid, e)
    else:
        for c in main_clusters:
            try:
                axis = _summarize_one(c)
                axes.append(axis)
            except Exception as e:
                logger.error("Summarize error for cluster %d: %s", c["cluster_id"], e)

    axes.sort(key=lambda a: a["edge_count"], reverse=True)

    small_edge_count = 0  # caller tracks this if needed
    logger.info("Dispute axes summarized: %d axes", len(axes))
    return axes


def build_dispute_axes(
    conn,
    col,
    *,
    model: str = "gpt-4.1-mini",
    cache_db_path: str | Path | None = None,
    max_workers: int = 5,
    distance_threshold: float = 0.5,
) -> list[dict]:
    """메인 파이프라인: load → cluster → summarize (병렬).

    Returns: 논쟁 축 리스트 (edge_count 내림차순)
    """
    prep = prepare_dispute_axes(conn, col, distance_threshold=distance_threshold)
    if not prep["main_clusters"]:
        logger.info("No clusters large enough to summarize")
        return []

    return summarize_clusters(
        prep["main_clusters"],
        model=model,
        cache_db_path=cache_db_path,
        max_workers=max_workers,
    )


def write_report(
    axes: list[dict],
    total_contradicts: int,
    total_clusters: int,
    output_path: Path,
) -> None:
    """논쟁 축 리포트를 마크다운으로 작성."""
    lines = [
        "# Dispute Axes Report",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        f"- Total contradicts edges: {total_contradicts:,}",
        f"- Clusters found: {total_clusters}",
        f"- Axes summarized: {len(axes)}",
        "",
        "## Axes",
        "",
    ]

    for i, axis in enumerate(axes, 1):
        lines.append(f"### {i}. {axis['axis_name']}")
        lines.append(f"- **Edges:** {axis['edge_count']}")
        lines.append(f"- **Domains:** {', '.join(axis['domains'])}")
        lines.append(f"- **Stance A:** {axis['stance_a']}")
        lines.append(f"- **Stance B:** {axis['stance_b']}")
        lines.append(f"- **Description:** {axis['description']}")

        if axis.get("sample_pairs"):
            lines.append("- **Sample pairs:**")
            for pair in axis["sample_pairs"]:
                lines.append(
                    f"  - {pair['from_ku_id']} vs {pair['to_ku_id']} "
                    f"({pair['strength']:.2f})"
                )
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written to %s", output_path)
