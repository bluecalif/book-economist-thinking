"""Stage C: JSON → raw_spans 변환 및 DB 저장.

text.json (기존 파싱 데이터)을 읽어 raw_spans 테이블에 적재한다.
청킹 단위: 1 page = 1 raw_span (설계 결정 C-1).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.db.models import (
    bulk_insert_raw_spans,
    count_raw_spans,
    get_connection,
    init_db,
    insert_book,
)

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 10  # config.yaml chunking.min_text_length


def load_text_json(json_path: str | Path) -> dict[str, Any]:
    """text.json 파일을 UTF-8로 로드."""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"text.json not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_chapters(
    data: dict[str, Any],
    book_id: str,
    min_text_len: int = MIN_TEXT_LENGTH,
) -> list[dict[str, Any]]:
    """text.json → raw_span dict 리스트 변환.

    Returns:
        list of dicts with keys: id, book_id, chapter, page, seq, text, span_type
    """
    chapters = data["text_content"]["chapters"]
    spans: list[dict[str, Any]] = []
    skipped = 0

    for ch in chapters:
        ch_num = ch["order_index"] + 1  # 0-indexed → 1-indexed
        chapter_label = f"ch{ch_num:02d}"

        for page in ch["pages"]:
            page_num = page["page_number"]
            text = page["text"]

            # 빈 페이지 필터
            if len(text.strip()) < min_text_len:
                skipped += 1
                logger.debug(
                    "Skipped page %d (len=%d)", page_num, len(text.strip())
                )
                continue

            span_id = f"{book_id}-{chapter_label}-p{page_num:03d}-s001"
            spans.append(
                {
                    "id": span_id,
                    "book_id": book_id,
                    "chapter": chapter_label,
                    "page": page_num,
                    "seq": 1,
                    "text": text,
                    "span_type": "paragraph",
                }
            )

    logger.info(
        "Parsed %d spans from %d chapters (skipped %d empty pages)",
        len(spans),
        len(chapters),
        skipped,
    )
    return spans


def ingest_book(
    db_path: str | Path,
    json_path: str | Path,
    book_id: str,
    title: str,
    domain: str,
    author: str | None = None,
) -> dict[str, int]:
    """전체 파이프라인: JSON 로드 → books 레코드 → raw_spans 적재 → 검증.

    Returns:
        {"total_pages": int, "spans_inserted": int, "skipped": int}
    """
    # 1. JSON 로드
    data = load_text_json(json_path)
    total_pages = data["metadata"]["total_pages"]

    # 2. DB 초기화 + books 레코드
    conn = init_db(db_path)
    insert_book(
        conn,
        id=book_id,
        title=title,
        domain=domain,
        author=author,
        filepath=str(json_path),
        total_pages=total_pages,
    )

    # 3. raw_spans 변환
    spans = parse_chapters(data, book_id)

    # 4. DB 적재
    inserted = bulk_insert_raw_spans(conn, spans)
    final_count = count_raw_spans(conn, book_id)

    conn.close()

    result = {
        "total_pages": total_pages,
        "spans_parsed": len(spans),
        "spans_inserted": inserted,
        "spans_in_db": final_count,
        "skipped": total_pages - len(spans),
    }
    logger.info("Ingest result: %s", result)
    return result


if __name__ == "__main__":
    import yaml

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # config.yaml 로드
    config_path = Path(__file__).resolve().parents[2] / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db_path = Path(__file__).resolve().parents[2] / cfg["paths"]["db"]
    book_cfg = cfg["books"][0]
    json_path = Path(__file__).resolve().parents[2] / book_cfg["json_path"]

    result = ingest_book(
        db_path=db_path,
        json_path=json_path,
        book_id=book_cfg["id"],
        title=book_cfg["title"],
        domain=book_cfg["domain"],
        author="이완배",
    )

    print(f"\n=== Stage C 완료 ===")
    print(f"  총 페이지: {result['total_pages']}")
    print(f"  파싱된 spans: {result['spans_parsed']}")
    print(f"  DB 삽입: {result['spans_inserted']}")
    print(f"  DB 최종 건수: {result['spans_in_db']}")
    print(f"  스킵 (빈 페이지): {result['skipped']}")
