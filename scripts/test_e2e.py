"""Stage G.3: E2E 통합 테스트 스크립트.

DB 정합성 + 검색 + 콘텐츠 생성 파이프라인 전체 검증.
API 호출이 포함되므로 수동 실행용.

Usage:
    python scripts/test_e2e.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def log(msg: str, status: str = "INFO") -> None:
    print(f"[{status}] {msg}")


def test_db_integrity() -> dict:
    """Test 1: DB 정합성 검증."""
    log("=== Test 1: DB 정합성 ===")
    results = {"name": "DB 정합성", "checks": [], "pass": True}

    db_path = ROOT / "data" / "knowledge.db"
    assert db_path.exists(), f"DB 파일 없음: {db_path}"
    results["checks"].append("DB 파일 존재")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Table existence
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    for t in ["books", "raw_spans", "knowledge_units", "edges", "generations"]:
        assert t in tables, f"테이블 누락: {t}"
    results["checks"].append(f"테이블 5개 확인: {tables}")

    # Record counts
    books = conn.execute("SELECT COUNT(*) as c FROM books").fetchone()["c"]
    spans = conn.execute("SELECT COUNT(*) as c FROM raw_spans").fetchone()["c"]
    kus = conn.execute("SELECT COUNT(*) as c FROM knowledge_units").fetchone()["c"]
    gens = conn.execute("SELECT COUNT(*) as c FROM generations").fetchone()["c"]

    log(f"  books={books}, spans={spans}, kus={kus}, generations={gens}")
    assert books >= 1, "books 0건"
    assert spans >= 100, f"spans {spans}건 (100건 미만)"
    assert kus >= 100, f"kus {kus}건 (100건 미만)"
    results["checks"].append(f"레코드: books={books}, spans={spans}, kus={kus}, gens={gens}")

    # FK integrity: all KU book_ids exist in books
    orphan_kus = conn.execute(
        "SELECT COUNT(*) as c FROM knowledge_units WHERE book_id NOT IN (SELECT id FROM books)"
    ).fetchone()["c"]
    assert orphan_kus == 0, f"고아 KU {orphan_kus}건"
    results["checks"].append("FK 무결성: KU→books 정상")

    conn.close()
    log("  PASS", "OK")
    return results


def test_chroma_integrity() -> dict:
    """Test 2: ChromaDB 정합성 — DB KU 수 == ChromaDB 임베딩 수."""
    log("=== Test 2: ChromaDB 정합성 ===")
    results = {"name": "ChromaDB 정합성", "checks": [], "pass": True}

    from src.db.vectors import init_chroma

    chroma_dir = ROOT / "data" / "chroma"
    collection = init_chroma(chroma_dir)
    chroma_count = collection.count()

    db_path = ROOT / "data" / "knowledge.db"
    conn = sqlite3.connect(str(db_path))
    ku_count = conn.execute("SELECT COUNT(*) as c FROM knowledge_units").fetchone()["c"]
    conn.close()

    log(f"  DB KUs={ku_count}, ChromaDB={chroma_count}")
    assert chroma_count == ku_count, f"불일치: DB {ku_count} != ChromaDB {chroma_count}"
    results["checks"].append(f"DB KUs ({ku_count}) == ChromaDB ({chroma_count})")

    log("  PASS", "OK")
    return results


def test_search() -> dict:
    """Test 3: 벡터 검색 동작 확인."""
    log("=== Test 3: 벡터 검색 ===")
    results = {"name": "벡터 검색", "checks": [], "pass": True}

    from src.search.vector import search_kus

    queries = ["매몰비용", "인플레이션", "경쟁의 효과"]
    for q in queries:
        hits = search_kus(q, top_k=5)
        log(f"  '{q}' → {len(hits)}건")
        assert len(hits) > 0, f"검색 결과 0건: '{q}'"
        results["checks"].append(f"'{q}' → {len(hits)}건")

    log("  PASS", "OK")
    return results


def test_generate() -> dict:
    """Test 4: 콘텐츠 생성 동작 확인 (summary — 최소 API 비용)."""
    log("=== Test 4: 콘텐츠 생성 ===")
    results = {"name": "콘텐츠 생성", "checks": [], "pass": True}

    from src.generation.content import generate_content

    result = generate_content(
        topic="매몰비용",
        format="summary",
        top_k=3,
        save=False,  # 테스트이므로 DB 저장 안 함
    )

    log(f"  format={result.format}, KU {len(result.ku_ids)}건, 길이={len(result.content)}자")
    assert len(result.content) > 100, f"생성 콘텐츠 너무 짧음: {len(result.content)}자"
    assert len(result.ku_ids) > 0, "참조 KU 없음"
    assert "출처:" in result.content, "출처 KU ID 누락"
    results["checks"].append(f"summary 생성: {len(result.content)}자, KU {len(result.ku_ids)}건")

    log("  PASS", "OK")
    return results


def test_vault_render() -> dict:
    """Test 5: Vault 렌더러 동작 확인."""
    log("=== Test 5: Vault 렌더링 ===")
    results = {"name": "Vault 렌더링", "checks": [], "pass": True}

    from src.vault.renderer import render_all_kus

    db_path = ROOT / "data" / "knowledge.db"
    vault_dir = ROOT / "vault"

    count = render_all_kus(db_path=db_path, output_dir=vault_dir)
    log(f"  렌더링: {count}건")
    assert count > 0, "렌더링 0건"
    results["checks"].append(f"렌더링 {count}건")

    # Verify file existence
    md_files = list((vault_dir / "domains").rglob("*.md"))
    log(f"  마크다운 파일: {len(md_files)}개")
    assert len(md_files) == count, f"파일 수 불일치: {len(md_files)} != {count}"
    results["checks"].append(f"마크다운 파일 {len(md_files)}개 확인")

    # Verify frontmatter
    sample = md_files[0].read_text(encoding="utf-8")
    assert sample.startswith("---"), "YAML frontmatter 누락"
    assert "## Claim" in sample, "Claim 섹션 누락"
    results["checks"].append("frontmatter + 본문 구조 확인")

    log("  PASS", "OK")
    return results


def main() -> None:
    log(f"E2E 통합 테스트 시작: {datetime.now().isoformat()}")
    log(f"프로젝트 루트: {ROOT}\n")

    all_results = []
    failed = []

    tests = [
        test_db_integrity,
        test_chroma_integrity,
        test_search,
        test_generate,
        test_vault_render,
    ]

    for test_fn in tests:
        try:
            result = test_fn()
            all_results.append(result)
        except (AssertionError, Exception) as e:
            log(f"  FAIL: {e}", "FAIL")
            all_results.append({
                "name": test_fn.__doc__ or test_fn.__name__,
                "pass": False,
                "error": str(e),
            })
            failed.append(test_fn.__name__)

    # Summary
    total = len(tests)
    passed = total - len(failed)
    print(f"\n{'='*60}")
    print(f"E2E 결과: {passed}/{total} PASS")
    if failed:
        print(f"FAIL: {', '.join(failed)}")
    print(f"{'='*60}")

    # Save results
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    report_path = logs_dir / "phase2-e2e-test.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "passed": passed,
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)
    print(f"리포트 저장: {report_path}")


if __name__ == "__main__":
    main()
