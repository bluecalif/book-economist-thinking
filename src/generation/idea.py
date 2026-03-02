"""Idea generation pipeline — hybrid search → context → LLM → ideas.

Stage J.2: business / content / serendipity 3모드.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

from src.db.models import get_connection, get_ku, insert_generation
from src.generation.content import _build_ku_context, _append_sources
from src.search.hybrid import hybrid_search

logger = logging.getLogger(__name__)

VALID_MODES = ("business", "content", "serendipity")
TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class IdeaResult:
    content: str          # 생성된 아이디어 (출처 포함)
    ku_ids: list[str]     # 사용된 KU ID 목록
    mode: str             # business | content | serendipity
    prompt: str           # LLM에 보낸 프롬프트
    generation_id: str    # DB 기록용 ID


def _load_config() -> dict[str, Any]:
    cfg_path = Path(__file__).resolve().parents[2] / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_template(mode: str) -> str:
    path = TEMPLATES_DIR / f"idea_{mode}.txt"
    with open(path, encoding="utf-8") as f:
        return f.read()


def _sample_cross_domain_edges(
    db_path: str | Path,
    n: int = 3,
) -> list[dict[str, Any]]:
    """DB에서 cross-domain edge를 랜덤 샘플링.

    Returns:
        [{"from_ku": dict, "to_ku": dict, "relation_type": str, "strength": float}, ...]
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT e.from_ku_id, e.to_ku_id, e.relation_type, e.strength
            FROM edges e
            JOIN knowledge_units ku1 ON e.from_ku_id = ku1.id
            JOIN knowledge_units ku2 ON e.to_ku_id = ku2.id
            WHERE ku1.domain != ku2.domain
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (n,),
        ).fetchall()

        pairs = []
        for row in rows:
            row = dict(row)
            from_ku = get_ku(conn, row["from_ku_id"])
            to_ku = get_ku(conn, row["to_ku_id"])
            if from_ku and to_ku:
                pairs.append({
                    "from_ku": from_ku,
                    "to_ku": to_ku,
                    "relation_type": row["relation_type"],
                    "strength": row["strength"],
                })
        return pairs
    finally:
        conn.close()


def _build_serendipity_context(pairs: list[dict[str, Any]]) -> str:
    """Cross-domain edge 쌍을 컨텍스트 텍스트로 조합."""
    blocks = []
    for i, pair in enumerate(pairs, 1):
        fk = pair["from_ku"]
        tk = pair["to_ku"]
        rel = pair["relation_type"]
        parts = [
            f"### 연결 {i}: {fk['domain']} ↔ {tk['domain']} ({rel})",
            f"",
            f"**A) [{fk['id']}] {fk['claim']}**",
        ]
        if fk.get("evidence_summary"):
            parts.append(f"  근거: {fk['evidence_summary']}")
        parts.append(f"")
        parts.append(f"**B) [{tk['id']}] {tk['claim']}**")
        if tk.get("evidence_summary"):
            parts.append(f"  근거: {tk['evidence_summary']}")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def generate_idea(
    topic: str | None = None,
    mode: str = "business",
    top_k: int = 8,
    save: bool = True,
) -> IdeaResult:
    """아이디어 생성 파이프라인.

    Args:
        topic: 주제 (business/content 모드 필수, serendipity는 무시).
        mode: 생성 모드 — "business", "content", "serendipity".
        top_k: hybrid search 결과 수 (serendipity에서는 edge 샘플 수).
        save: True이면 generations 테이블에 기록.

    Returns:
        IdeaResult with generated ideas and metadata.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of {VALID_MODES}")

    if mode != "serendipity" and not topic:
        raise ValueError(f"'{mode}' 모드에는 --topic이 필요합니다.")

    cfg = _load_config()
    project_root = Path(__file__).resolve().parents[2]
    db_path = project_root / cfg["paths"]["db"]
    model = cfg["models"]["generation"]

    # 1. KU 수집
    used_ku_ids: list[str] = []

    if mode == "serendipity":
        # 랜덤 cross-domain edge 샘플링
        pairs = _sample_cross_domain_edges(db_path, n=min(top_k, 3))
        if not pairs:
            raise ValueError("Cross-domain edge가 없습니다.")
        ku_context = _build_serendipity_context(pairs)
        for pair in pairs:
            used_ku_ids.append(pair["from_ku"]["id"])
            used_ku_ids.append(pair["to_ku"]["id"])
    else:
        # hybrid search
        results = hybrid_search(topic, top_k=top_k, db_path=db_path)
        if not results:
            raise ValueError(f"'{topic}'에 대한 검색 결과가 없습니다.")

        # KU 상세 조회
        kus: list[dict[str, Any]] = []
        conn = get_connection(db_path)
        try:
            for r in results:
                ku = get_ku(conn, r.ku_id)
                if ku:
                    kus.append(ku)
                    used_ku_ids.append(r.ku_id)
        finally:
            conn.close()

        if not kus:
            raise ValueError(f"'{topic}'에 대한 KU를 찾을 수 없습니다.")
        ku_context = _build_ku_context(kus)

    # 2. 템플릿 로드 + 변수 치환
    template = _load_template(mode)
    prompt = template.replace("{ku_context}", ku_context)
    if topic:
        prompt = prompt.replace("{topic}", topic)

    # 3. LLM 호출
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    logger.info(
        "LLM 호출: model=%s, mode='%s', topic='%s', KU %d건",
        model, mode, topic or "(serendipity)", len(used_ku_ids),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    raw_content = response.choices[0].message.content

    # 4. 출처 첨부
    content = _append_sources(raw_content, used_ku_ids)

    # 5. DB 기록
    gen_id = f"gen-{uuid.uuid4().hex[:8]}"

    if save:
        conn = get_connection(db_path)
        try:
            insert_generation(
                conn,
                id=gen_id,
                mode="idea",
                format=mode,
                prompt=prompt,
                output=content,
                ku_ids=used_ku_ids,
            )
            logger.info("DB 기록 완료: %s", gen_id)
        finally:
            conn.close()

    return IdeaResult(
        content=content,
        ku_ids=used_ku_ids,
        mode=mode,
        prompt=prompt,
        generation_id=gen_id,
    )
