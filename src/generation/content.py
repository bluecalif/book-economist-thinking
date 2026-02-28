"""Content generation pipeline — topic → KU search → context → LLM → output.

Stage F: F.1 pipeline, F.3 source attribution, F.4 DB recording.
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
from src.search.vector import search_kus

logger = logging.getLogger(__name__)

VALID_FORMATS = ("blog", "summary", "thread")
TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class GenerationResult:
    content: str          # 생성된 콘텐츠
    ku_ids: list[str]     # 사용된 KU ID 목록
    format: str           # blog | summary | thread
    prompt: str           # 사용된 프롬프트 전문
    generation_id: str    # DB 기록용 ID


def _load_config() -> dict[str, Any]:
    cfg_path = Path(__file__).resolve().parents[2] / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_template(fmt: str) -> str:
    path = TEMPLATES_DIR / f"{fmt}.txt"
    with open(path, encoding="utf-8") as f:
        return f.read()


def _build_ku_context(kus: list[dict[str, Any]]) -> str:
    """KU 목록을 컨텍스트 텍스트 블록으로 조합."""
    blocks = []
    for ku in kus:
        parts = [f"[{ku['id']}] {ku['claim']}"]
        if ku.get("evidence_summary"):
            parts.append(f"  근거: {ku['evidence_summary']}")
        if ku.get("counter_summary"):
            parts.append(f"  반론: {ku['counter_summary']}")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def _append_sources(content: str, ku_ids: list[str]) -> str:
    """생성 결과 끝에 출처 KU ID 첨부."""
    sources = ", ".join(ku_ids)
    return f"{content}\n\n---\n출처: {sources}"


def generate_content(
    topic: str,
    format: str = "blog",
    ku_ids: list[str] | None = None,
    top_k: int = 5,
    save: bool = True,
) -> GenerationResult:
    """토픽 기반 콘텐츠 생성 파이프라인.

    Args:
        topic: 생성할 콘텐츠의 주제.
        format: 출력 형식 — "blog", "summary", "thread".
        ku_ids: 특정 KU ID 목록 (지정 시 검색 생략).
        top_k: 검색 시 반환할 최대 KU 수.
        save: True이면 generations 테이블에 기록.

    Returns:
        GenerationResult with generated content and metadata.
    """
    if format not in VALID_FORMATS:
        raise ValueError(f"Invalid format '{format}'. Must be one of {VALID_FORMATS}")

    cfg = _load_config()
    project_root = Path(__file__).resolve().parents[2]
    db_path = project_root / cfg["paths"]["db"]
    model = cfg["models"]["generation"]

    # 1. KU 조회: 직접 지정 또는 검색
    kus: list[dict[str, Any]] = []
    used_ku_ids: list[str] = []

    if ku_ids:
        conn = get_connection(db_path)
        try:
            for kid in ku_ids:
                ku = get_ku(conn, kid)
                if ku:
                    kus.append(ku)
                    used_ku_ids.append(kid)
                else:
                    logger.warning("KU not found: %s", kid)
        finally:
            conn.close()
    else:
        results = search_kus(topic, top_k=top_k)
        for r in results:
            conn = get_connection(db_path)
            try:
                ku = get_ku(conn, r.ku_id)
                if ku:
                    kus.append(ku)
                    used_ku_ids.append(r.ku_id)
            finally:
                conn.close()

    if not kus:
        raise ValueError(f"No KUs found for topic '{topic}'")

    # 2. 컨텍스트 조합
    ku_context = _build_ku_context(kus)

    # 3. 템플릿 로드 + 변수 치환
    template = _load_template(format)
    prompt = template.replace("{topic}", topic).replace("{ku_context}", ku_context)

    # 4. OpenAI Chat API 호출
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    logger.info("LLM 호출: model=%s, topic='%s', format='%s', KU %d건", model, topic, format, len(kus))

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    raw_content = response.choices[0].message.content

    # 5. 출처 KU ID 첨부 (F.3)
    content = _append_sources(raw_content, used_ku_ids)

    # 6. DB 기록 (F.4)
    gen_id = f"gen-{uuid.uuid4().hex[:8]}"

    if save:
        conn = get_connection(db_path)
        try:
            insert_generation(
                conn,
                id=gen_id,
                mode="content",
                format=format,
                prompt=prompt,
                output=content,
                ku_ids=used_ku_ids,
            )
            logger.info("DB 기록 완료: %s", gen_id)
        finally:
            conn.close()

    return GenerationResult(
        content=content,
        ku_ids=used_ku_ids,
        format=format,
        prompt=prompt,
        generation_id=gen_id,
    )
