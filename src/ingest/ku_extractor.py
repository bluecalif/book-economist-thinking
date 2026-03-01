"""Stage D: KU(Knowledge Unit) 추출 + 임베딩 파이프라인.

raw_spans → LLM 추출 → knowledge_units DB 저장 → ChromaDB 임베딩.
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.db.models import (
    count_kus,
    count_raw_spans,
    get_connection,
    get_raw_spans_by_book,
    init_db,
    insert_ku,
    list_kus_by_book,
)
from src.db.vectors import add_embeddings, init_chroma

logger = logging.getLogger(__name__)

# --- Domain Mapping ---

DOMAIN_SHORT_MAP = {
    "경제/경영": "econ",
    "역사/사회": "hist",
    "인문/자기계발": "humn",
    "과학/기술": "sci",
    "경제": "econ",  # 레거시 호환
}

# --- Prompt ---

SYSTEM_PROMPT = """\
당신은 책의 내용을 구조화된 지식 단위(Knowledge Unit)로 추출하는 전문가입니다.
반드시 JSON array만 출력하세요. 다른 텍스트는 포함하지 마세요."""

USER_PROMPT_TEMPLATE = """\
다음 텍스트에서 Knowledge Unit을 추출하세요.

규칙:
1. 각 KU는 하나의 명확한 claim(주장, 관찰, 원리, 통찰)을 가져야 합니다
2. claim 예시: "X는 Y를 유발한다", "X의 원리는 Y이다", "X 현상은 Y 때문에 발생한다"
3. 일화나 사례 속에 담긴 경제학적 원리나 교훈도 claim으로 추출하세요
4. claim을 뒷받침하는 evidence(근거)를 원문에서 인용하세요
5. 저자가 제시한 한계나 반례가 있으면 counter로 기록하세요
6. 순수한 배경 묘사만 있고 어떤 주장/원리/통찰도 없는 경우에만 빈 배열을 반환하세요
7. 하나의 텍스트에서 여러 KU가 나올 수 있습니다
8. 한국어로 작성하세요

출력 형식 (JSON array만, 마크다운 코드블록 금지):
[{{"claim": "...", "evidence_summary": "...", "counter_summary": "...", "tags": ["...", "..."]}}]

claim이 정말 없으면 빈 배열: []

텍스트:
{chunk_text}"""


# --- JSON Repair ---

def repair_json(text: str) -> str | None:
    """LLM 응답에서 JSON array를 추출하고 보수."""
    # 마크다운 코드블록 제거
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()

    # JSON array 부분만 추출
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return None
    text = text[start : end + 1]

    # trailing comma 제거
    text = re.sub(r",\s*]", "]", text)
    text = re.sub(r",\s*}", "}", text)

    return text


def parse_kus_json(raw_response: str) -> list[dict[str, Any]] | None:
    """LLM 응답 → KU dict list. 실패 시 None."""
    repaired = repair_json(raw_response)
    if not repaired:
        return None
    try:
        result = json.loads(repaired)
        if isinstance(result, list):
            return result
        return None
    except json.JSONDecodeError:
        return None


# --- LLM Call ---

def call_llm(
    client: OpenAI,
    chunk_text: str,
    model: str = "gpt-4.1-mini",
    cache_db_path: str | Path | None = None,
) -> str:
    """OpenAI API 호출 → 응답 텍스트 반환 (캐시 사용)."""
    from src.ingest.llm_cache import get_or_call

    user_text = USER_PROMPT_TEMPLATE.format(chunk_text=chunk_text)
    return get_or_call(
        client,
        model,
        SYSTEM_PROMPT,
        user_text,
        temperature=0.3,
        max_tokens=2000,
        cache_db_path=cache_db_path,
    )


# --- Span-level LLM Processing ---


def _process_span_llm(
    client: OpenAI,
    span: dict[str, Any],
    model: str,
    cache_db_path: str | Path | None,
    span_index: int,
    total_spans: int,
) -> dict[str, Any]:
    """단일 span에 대해 LLM 호출 + JSON 파싱 수행 (DB 접근 없음).

    Returns:
        dict with keys: span_id, page, kus, error, span_index
    """
    span_id = span["id"]
    page = span["page"]
    text = span["text"]

    logger.info("[%d/%d] Processing span %s (page %d)...", span_index + 1, total_spans, span_id, page)

    # 1차 시도
    raw_response = ""
    kus = None
    try:
        raw_response = call_llm(client, text, model=model, cache_db_path=cache_db_path)
        kus = parse_kus_json(raw_response)
    except Exception as e:
        logger.warning("LLM call failed for %s: %s", span_id, e)

    # 1x 재시도
    if kus is None:
        logger.info("Retry for %s...", span_id)
        time.sleep(1)
        try:
            raw_response = call_llm(client, text, model=model, cache_db_path=cache_db_path)
            kus = parse_kus_json(raw_response)
        except Exception as e:
            logger.warning("Retry failed for %s: %s", span_id, e)

    if kus is None:
        return {
            "span_id": span_id,
            "page": page,
            "kus": None,
            "error": "JSON parse failed after retry",
            "response_preview": raw_response[:500],
            "span_index": span_index,
        }

    return {
        "span_id": span_id,
        "page": page,
        "kus": kus,
        "error": None,
        "span_index": span_index,
    }


# --- Extraction Pipeline ---

def extract_kus_from_spans(
    db_path: str | Path,
    chroma_dir: str | Path,
    *,
    book_id: str,
    domain: str,
    model: str = "gpt-4.1-mini",
    embedding_model: str = "text-embedding-3-large",
    sample_pages: list[int] | None = None,
    delay: float = 0.5,
    cache_db_path: str | Path | None = None,
    max_workers: int = 1,
) -> dict[str, Any]:
    """전체 KU 추출 파이프라인.

    Args:
        sample_pages: 특정 페이지만 처리 (D.1 테스트용). None이면 전체.
        delay: API 호출 간 대기 (초). max_workers>1일 때는 무시됨.
        max_workers: LLM 병렬 호출 수. 1이면 순차, >1이면 ThreadPoolExecutor 사용.

    Returns:
        metrics dict (D.5 검증용).
    """
    conn = init_db(db_path)
    spans = get_raw_spans_by_book(conn, book_id)

    if sample_pages:
        spans = [s for s in spans if s["page"] in sample_pages]
        logger.info("Sample mode: %d spans selected", len(spans))

    # .env 로드
    import os
    from dotenv import load_dotenv
    load_dotenv()

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # book_seq from book_id (econ-thinking-001 → 001)
    book_seq = book_id.split("-")[-1]
    domain_short = DOMAIN_SHORT_MAP.get(domain, domain[:4].lower())

    # Metrics
    total_spans = len(spans)
    successful_parses = 0
    failed_spans: list[dict] = []
    pages_with_claims = 0
    total_kus_extracted = 0
    ku_seq = count_kus(conn, book_id)  # 기존 KU 수부터 이어서 번호 매김

    all_kus: list[dict[str, Any]] = []

    # --- LLM 호출: 병렬 또는 순차 ---
    if max_workers > 1:
        logger.info("Parallel mode: max_workers=%d for %d spans", max_workers, total_spans)
        llm_results: list[dict[str, Any]] = [{}] * total_spans  # placeholder

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(
                    _process_span_llm, client, span, model, cache_db_path, i, total_spans
                ): i
                for i, span in enumerate(spans)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    llm_results[idx] = future.result()
                except Exception as e:
                    span = spans[idx]
                    logger.error("Unexpected error for span %s: %s", span["id"], e)
                    llm_results[idx] = {
                        "span_id": span["id"],
                        "page": span["page"],
                        "kus": None,
                        "error": str(e),
                        "response_preview": "",
                        "span_index": idx,
                    }
    else:
        # 순차 처리 (기존 방식)
        llm_results = []
        for i, span in enumerate(spans):
            result = _process_span_llm(client, span, model, cache_db_path, i, total_spans)
            llm_results.append(result)
            if delay > 0 and i < total_spans - 1:
                time.sleep(delay)

    # --- 결과를 span 순서대로 순차 DB 저장 ---
    for result in llm_results:
        span_id = result["span_id"]
        page = result["page"]
        kus = result.get("kus")

        if kus is None:
            failed_spans.append({
                "span_id": span_id,
                "page": page,
                "error": result.get("error", "unknown"),
                "response_preview": result.get("response_preview", ""),
            })
            logger.warning("SKIP %s: %s", span_id, result.get("error"))
            continue

        successful_parses += 1

        if len(kus) > 0:
            pages_with_claims += 1

        # D.3: KU DB 저장 (순차)
        for ku_data in kus:
            ku_seq += 1
            ku_id = f"ku-{domain_short}-{book_seq}-{ku_seq:04d}"

            claim = ku_data.get("claim", "").strip()
            if not claim:
                continue

            evidence = ku_data.get("evidence_summary", "")
            counter = ku_data.get("counter_summary", "")
            tags = ku_data.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            insert_ku(
                conn,
                id=ku_id,
                book_id=book_id,
                claim=claim,
                domain=domain,
                evidence_summary=evidence or None,
                counter_summary=counter or None,
                tags=tags or None,
                confidence=0.5,
                maturity="M0",
                source_spans=[span_id],
            )

            all_kus.append({
                "ku_id": ku_id,
                "claim": claim,
                "evidence_summary": evidence,
                "source_span": span_id,
            })
            total_kus_extracted += 1

    # D.4: 임베딩 생성 + ChromaDB 저장
    if all_kus:
        logger.info("Generating embeddings for %d KUs...", len(all_kus))
        _generate_and_store_embeddings(
            client=client,
            chroma_dir=chroma_dir,
            kus=all_kus,
            book_id=book_id,
            domain=domain,
            embedding_model=embedding_model,
        )

    conn.close()

    # D.5: 메트릭스
    claim_rate = pages_with_claims / total_spans if total_spans > 0 else 0
    parse_rate = successful_parses / total_spans if total_spans > 0 else 0

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "book_id": book_id,
        "model": model,
        "total_spans": total_spans,
        "successful_parses": successful_parses,
        "parse_success_rate": round(parse_rate, 4),
        "pages_with_claims": pages_with_claims,
        "claim_existence_rate": round(claim_rate, 4),
        "total_kus_extracted": total_kus_extracted,
        "failed_spans": failed_spans,
        "sample_pages": sample_pages,
    }

    logger.info(
        "Done. KUs=%d, parse_rate=%.1f%%, claim_rate=%.1f%%",
        total_kus_extracted,
        parse_rate * 100,
        claim_rate * 100,
    )
    return metrics


def _generate_and_store_embeddings(
    client: OpenAI,
    chroma_dir: str | Path,
    kus: list[dict[str, Any]],
    book_id: str,
    domain: str,
    embedding_model: str,
    batch_size: int = 50,
) -> int:
    """KU claim+evidence 임베딩 생성 → ChromaDB 저장."""
    collection = init_chroma(chroma_dir)

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for ku in kus:
        ku_id = ku["ku_id"]
        doc_text = ku["claim"]
        if ku.get("evidence_summary"):
            doc_text += " " + ku["evidence_summary"]

        ids.append(ku_id)
        texts.append(doc_text)
        metadatas.append({
            "ku_id": ku_id,
            "book_id": book_id,
            "domain": domain,
        })

    # 배치 임베딩
    all_embeddings: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.embeddings.create(model=embedding_model, input=batch)
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
        logger.info("Embedded batch %d-%d", start, start + len(batch))

    # ChromaDB 저장
    add_embeddings(
        collection,
        ids=ids,
        embeddings=all_embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    logger.info("Stored %d embeddings in ChromaDB", len(ids))
    return len(ids)


# --- CLI ---

if __name__ == "__main__":
    import sys

    import yaml

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config_path = Path(__file__).resolve().parents[2] / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db_path = Path(__file__).resolve().parents[2] / cfg["paths"]["db"]
    chroma_dir = Path(__file__).resolve().parents[2] / cfg["paths"]["chroma"]

    # 카탈로그에서 첫 번째 done 책 로드
    catalog_path = Path(__file__).resolve().parents[2] / cfg["paths"]["catalog"]
    with open(catalog_path, encoding="utf-8") as cf:
        catalog = yaml.safe_load(cf)
    book_cfg = catalog["books"][0]
    for b in catalog["books"]:
        if b.get("status") == "done":
            book_cfg = b
            break

    # CLI args: --sample 50,150,250 또는 --full
    sample_pages = None
    if "--sample" in sys.argv:
        idx = sys.argv.index("--sample")
        pages_str = sys.argv[idx + 1]
        sample_pages = [int(p) for p in pages_str.split(",")]
        print(f"Sample mode: pages {sample_pages}")
    elif "--full" not in sys.argv:
        # 기본: D.1 테스트용 5페이지 샘플
        sample_pages = [50, 100, 150, 250, 350]
        print(f"Default sample mode: pages {sample_pages}")

    metrics = extract_kus_from_spans(
        db_path=db_path,
        chroma_dir=chroma_dir,
        book_id=book_cfg["id"],
        domain=book_cfg.get("domain", "경제/경영"),
        model=cfg["models"]["ku_extraction"],
        embedding_model=cfg["models"]["embedding"],
        sample_pages=sample_pages,
    )

    # 메트릭스 저장
    logs_dir = Path(__file__).resolve().parents[2] / "logs"
    logs_dir.mkdir(exist_ok=True)
    metrics_path = logs_dir / "phase1-d5-metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"\n=== Stage D 결과 ===")
    print(f"  처리 spans: {metrics['total_spans']}")
    print(f"  JSON 파싱 성공률: {metrics['parse_success_rate'] * 100:.1f}%")
    print(f"  claim 존재율: {metrics['claim_existence_rate'] * 100:.1f}%")
    print(f"  추출된 KUs: {metrics['total_kus_extracted']}")
    print(f"  실패 spans: {len(metrics['failed_spans'])}")
    print(f"  메트릭스 저장: {metrics_path}")

    # D.5 판정
    pass_parse = metrics["parse_success_rate"] >= 0.95
    pass_claim = metrics["claim_existence_rate"] >= 0.80
    if pass_parse and pass_claim:
        print(f"\n  [PASS] D.5 PASS -- full run ready (--full)")
    else:
        if not pass_parse:
            print(f"\n  [FAIL] JSON parse rate: {metrics['parse_success_rate']*100:.1f}% < 95%")
        if not pass_claim:
            print(f"\n  [FAIL] claim rate: {metrics['claim_existence_rate']*100:.1f}% < 80%")
