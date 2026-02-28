"""Phase 1 E2E 테스트: JSON → raw_spans → KU → 임베딩 → ChromaDB 검색.

기존 프로덕션 DB는 건드리지 않고 임시 DB로 소규모 파이프라인을 재현한다.
ChromaDB 유사도 검색 품질도 함께 검증한다.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

BOOK_ID = "econ-thinking-001"
DOMAIN = "경제"
SAMPLE_PAGES = [50, 100, 150]  # 3페이지만 테스트


def header(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    mark = "[O]" if condition else "[X]"
    line = f"  [{status}] {label}"
    if detail:
        line += f" -- {detail}"
    print(f"{mark} {line}")
    return condition


def main() -> None:
    results: list[bool] = []

    # ── Test 1: 기존 프로덕션 DB 무결성 검증 ──
    header("Test 1: 프로덕션 DB 무결성 검증")

    prod_db = PROJECT_ROOT / "data" / "knowledge.db"
    results.append(check("DB 파일 존재", prod_db.exists()))

    conn = sqlite3.connect(str(prod_db))
    conn.row_factory = sqlite3.Row

    # 테이블 존재
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    for t in ["books", "raw_spans", "knowledge_units", "edges", "generations"]:
        results.append(check(f"테이블 '{t}' 존재", t in tables))

    # 건수 검증
    book_cnt = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    span_cnt = conn.execute("SELECT COUNT(*) FROM raw_spans").fetchone()[0]
    ku_cnt = conn.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()[0]
    results.append(check("books 1건", book_cnt == 1, f"actual={book_cnt}"))
    results.append(check("raw_spans 341건", span_cnt == 341, f"actual={span_cnt}"))
    results.append(check("knowledge_units 997건", ku_cnt == 997, f"actual={ku_cnt}"))

    # FK 무결성: 모든 KU의 source_spans가 실제 raw_spans를 참조
    orphan_kus = conn.execute("""
        SELECT k.id, k.source_spans FROM knowledge_units k
        WHERE k.source_spans IS NOT NULL
    """).fetchall()
    orphan_count = 0
    for ku in orphan_kus:
        spans = json.loads(ku["source_spans"])
        for span_id in spans:
            exists = conn.execute(
                "SELECT 1 FROM raw_spans WHERE id = ?", (span_id,)
            ).fetchone()
            if not exists:
                orphan_count += 1
    results.append(check(
        "FK 무결성 (KU→raw_span)", orphan_count == 0,
        f"orphan refs={orphan_count}"
    ))

    # 데이터 품질
    dup_claims = conn.execute(
        "SELECT COUNT(*) FROM (SELECT claim FROM knowledge_units GROUP BY claim HAVING COUNT(*)>1)"
    ).fetchone()[0]
    results.append(check("중복 claim 없음", dup_claims == 0, f"dups={dup_claims}"))

    no_evidence = conn.execute(
        "SELECT COUNT(*) FROM knowledge_units WHERE evidence_summary IS NULL OR LENGTH(TRIM(evidence_summary)) < 5"
    ).fetchone()[0]
    results.append(check("모든 KU에 evidence 존재", no_evidence == 0, f"missing={no_evidence}"))

    conn.close()

    # ── Test 2: ChromaDB 임베딩 검증 ──
    header("Test 2: ChromaDB 임베딩 검증")

    from src.db.vectors import init_chroma

    chroma_dir = PROJECT_ROOT / "data" / "chroma"
    results.append(check("chroma 디렉터리 존재", chroma_dir.exists()))

    collection = init_chroma(chroma_dir)
    chroma_count = collection.count()
    results.append(check("ChromaDB 997건 임베딩", chroma_count == 997, f"actual={chroma_count}"))

    # ── Test 3: ChromaDB 유사도 검색 품질 ──
    header("Test 3: ChromaDB 유사도 검색 품질")

    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  [SKIP] OPENAI_API_KEY not set -- search test skipped")
    else:
        client = OpenAI(api_key=api_key)

        test_queries = [
            ("매몰비용", "경제"),
            ("인플레이션", "경제"),
            ("경쟁의 효과", "경제"),
        ]

        for query_text, expected_domain in test_queries:
            # 쿼리 임베딩
            resp = client.embeddings.create(
                model="text-embedding-3-large", input=[query_text]
            )
            q_emb = resp.data[0].embedding

            from src.db.vectors import query_similar

            result = query_similar(collection, q_emb, n_results=5)
            ids = result["ids"][0] if result["ids"] else []
            distances = result["distances"][0] if result["distances"] else []
            docs = result["documents"][0] if result["documents"] else []

            has_results = len(ids) > 0
            results.append(check(
                f"검색 '{query_text}' 결과 존재",
                has_results,
                f"top-5 ids={ids[:3]}..."
            ))

            if distances:
                top_dist = distances[0]
                # cosine distance < 1.0 means some similarity
                results.append(check(
                    f"검색 '{query_text}' 유사도 합리적",
                    top_dist < 1.5,
                    f"top distance={top_dist:.4f}"
                ))
                print(f"    Top-1: {docs[0][:80]}..." if docs else "    (no docs)")

    # ── Test 4: 파싱 파이프라인 재현 (임시 DB) ──
    header("Test 4: 파싱 파이프라인 재현 (임시 DB, 3페이지)")

    json_path = PROJECT_ROOT / "55bbe4_경제학자의_생각법_text.json"
    results.append(check("text.json 파일 존재", json_path.exists()))

    if json_path.exists():
        from src.ingest.pdf_parser import load_text_json, parse_chapters
        from src.db.models import init_db, count_raw_spans, insert_book, bulk_insert_raw_spans

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_db = Path(tmpdir) / "test.db"
            conn = init_db(tmp_db)

            # books 레코드
            insert_book(conn, id=BOOK_ID, title="경제학자의 생각법", domain=DOMAIN)

            # JSON 파싱
            data = load_text_json(json_path)
            spans = parse_chapters(data, BOOK_ID)

            # 3페이지만 필터
            sample_spans = [s for s in spans if s["page"] in SAMPLE_PAGES]
            results.append(check(
                "샘플 스팬 추출",
                len(sample_spans) == len(SAMPLE_PAGES),
                f"expected={len(SAMPLE_PAGES)}, actual={len(sample_spans)}"
            ))

            # DB 저장
            inserted = bulk_insert_raw_spans(conn, sample_spans)
            db_count = count_raw_spans(conn, BOOK_ID)
            results.append(check(
                "임시 DB 저장",
                db_count == len(sample_spans),
                f"inserted={inserted}, db_count={db_count}"
            ))

            # 저장된 데이터 확인
            for s in sample_spans:
                row = conn.execute(
                    "SELECT * FROM raw_spans WHERE id = ?", (s["id"],)
                ).fetchone()
                results.append(check(
                    f"span {s['id']} 복원",
                    row is not None and row["text"] == s["text"],
                ))

            conn.close()

    # ── 최종 결과 ──
    header("최종 결과")

    passed = sum(results)
    total = len(results)
    all_pass = all(results)

    print(f"\n  {passed}/{total} tests passed")
    if all_pass:
        print("  Phase 1 E2E ALL PASS!")
    else:
        print("  Some tests FAILED -- check logs above")

    # 결과를 JSON으로도 저장
    log_path = PROJECT_ROOT / "logs" / "phase1-e2e-test.json"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "passed": passed,
            "total": total,
            "all_pass": all_pass,
        }, f, indent=2)
    print(f"  결과 저장: {log_path}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
