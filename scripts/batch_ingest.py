"""Stage H.6p: 배치 인제스트 스크립트.

카탈로그 기반으로 여러 책을 순차 인제스트한다.
진행 추적(checkpoint), 에러 격리, rate limit 적용.

Usage:
    python scripts/batch_ingest.py --pilot          # status=pilot 도서만
    python scripts/batch_ingest.py --books hist-016,sci-023
    python scripts/batch_ingest.py --domain 역사/사회
    python scripts/batch_ingest.py --all             # done 제외 전부
    python scripts/batch_ingest.py --dry-run --pilot  # 실제 실행 없이 미리보기
    python scripts/batch_ingest.py --status           # 진행 현황 출력
    python scripts/batch_ingest.py --retry-failed     # 실패 도서 재시도
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

PROGRESS_FILE = PROJECT_ROOT / "logs" / "batch_progress.json"


# --- Progress Tracking ---


def _load_progress() -> dict[str, Any]:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"books": {}, "last_updated": None}


def _save_progress(progress: dict[str, Any]) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def _book_status(progress: dict, book_id: str) -> str | None:
    """Return book progress status: 'done', 'failed', or None."""
    return progress.get("books", {}).get(book_id, {}).get("status")


# --- Catalog ---


def _load_config() -> dict:
    with open(PROJECT_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_catalog(cfg: dict) -> list[dict]:
    catalog_path = PROJECT_ROOT / cfg["paths"]["catalog"]
    with open(catalog_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["books"]


def _resolve_json_path(cfg: dict, book: dict) -> Path:
    """Resolve raw JSON path for a book using domain directory structure."""
    domain_dir = book["domain"].replace("/", "-")
    return PROJECT_ROOT / cfg["paths"]["raw"] / domain_dir / book["json_file"]


# --- Filter ---


def _filter_books(
    books: list[dict],
    *,
    pilot: bool = False,
    book_ids: list[str] | None = None,
    domain: str | None = None,
    all_books: bool = False,
    retry_failed: bool = False,
    progress: dict | None = None,
) -> list[dict]:
    """Filter catalog books by criteria."""
    if retry_failed:
        if not progress:
            return []
        failed_ids = {
            bid for bid, info in progress.get("books", {}).items()
            if info.get("status") == "failed"
        }
        return [b for b in books if b["id"] in failed_ids]

    if book_ids:
        id_set = set(book_ids)
        return [b for b in books if b["id"] in id_set]

    if pilot:
        return [b for b in books if b.get("status") == "pilot"]

    if domain:
        return [b for b in books if b["domain"] == domain and b.get("status") != "done"]

    if all_books:
        return [b for b in books if b.get("status") != "done"]

    return []


# --- Single Book Ingest ---


def _ingest_one_book(
    cfg: dict,
    book: dict,
    *,
    dry_run: bool = False,
    delay_spans: float = 0.5,
    delay_books: float = 2.0,
    max_workers: int = 1,
) -> dict[str, Any]:
    """Ingest a single book through the full pipeline.

    Returns:
        Result dict with status, metrics, error info.
    """
    book_id = book["id"]
    title = book["title"]
    domain = book["domain"]
    json_path = _resolve_json_path(cfg, book)

    result: dict[str, Any] = {
        "book_id": book_id,
        "title": title,
        "domain": domain,
        "started_at": datetime.now().isoformat(),
    }

    if not json_path.exists():
        result["status"] = "failed"
        result["error"] = f"JSON not found: {json_path}"
        return result

    db_path = PROJECT_ROOT / cfg["paths"]["db"]
    chroma_dir = PROJECT_ROOT / cfg["paths"]["chroma"]
    vault_dir = PROJECT_ROOT / "vault"

    if dry_run:
        from src.ingest.pdf_parser import load_text_json, parse_chapters

        data = load_text_json(json_path)
        spans = parse_chapters(data, book_id)
        result["status"] = "dry_run"
        result["total_pages"] = data["metadata"]["total_pages"]
        result["spans_count"] = len(spans)
        return result

    # Step 1: JSON → raw_spans
    logger.info("[%s] Step 1/3: JSON → raw_spans", book_id)
    from src.ingest.pdf_parser import ingest_book

    parse_result = ingest_book(
        db_path=db_path,
        json_path=json_path,
        book_id=book_id,
        title=title,
        domain=domain,
        author=book.get("author"),
    )
    result["spans_inserted"] = parse_result["spans_inserted"]
    result["spans_in_db"] = parse_result["spans_in_db"]

    # Step 2: KU extraction + embedding
    logger.info("[%s] Step 2/3: KU extraction + embedding", book_id)
    from src.ingest.ku_extractor import extract_kus_from_spans

    cache_db_path = PROJECT_ROOT / "data" / "llm_cache.db"
    metrics = extract_kus_from_spans(
        db_path=db_path,
        chroma_dir=chroma_dir,
        book_id=book_id,
        domain=domain,
        model=cfg["models"]["ku_extraction"],
        embedding_model=cfg["models"]["embedding"],
        delay=delay_spans,
        cache_db_path=cache_db_path,
        max_workers=max_workers,
    )
    result["kus_extracted"] = metrics["total_kus_extracted"]
    result["parse_success_rate"] = metrics["parse_success_rate"]
    result["claim_existence_rate"] = metrics["claim_existence_rate"]
    result["failed_spans"] = len(metrics["failed_spans"])

    # Step 3: Vault rendering
    logger.info("[%s] Step 3/3: Vault rendering", book_id)
    from src.vault.renderer import render_all_kus

    rendered = render_all_kus(db_path=db_path, output_dir=vault_dir, book_id=book_id)
    result["vault_rendered"] = rendered

    result["status"] = "done"
    result["finished_at"] = datetime.now().isoformat()
    return result


# --- Batch Runner ---


def run_batch(
    books: list[dict],
    cfg: dict,
    *,
    dry_run: bool = False,
    progress: dict | None = None,
    max_workers: int = 1,
) -> list[dict[str, Any]]:
    """Run ingest for a list of books with error isolation."""
    if progress is None:
        progress = _load_progress()

    delay_spans = cfg.get("batch", {}).get("delay_between_spans", 0.5)
    delay_books = cfg.get("batch", {}).get("delay_between_books", 2.0)

    results: list[dict[str, Any]] = []

    for i, book in enumerate(books):
        book_id = book["id"]

        # Skip already done in progress
        if not dry_run and _book_status(progress, book_id) == "done":
            logger.info("[%d/%d] SKIP %s (already done)", i + 1, len(books), book_id)
            continue

        logger.info(
            "[%d/%d] START %s: %s (%s)",
            i + 1, len(books), book_id, book["title"], book["domain"],
        )

        try:
            result = _ingest_one_book(
                cfg, book,
                dry_run=dry_run,
                delay_spans=delay_spans,
                delay_books=delay_books,
                max_workers=max_workers,
            )
            results.append(result)

            # Update progress
            if not dry_run:
                progress["books"][book_id] = {
                    "status": result["status"],
                    "finished_at": result.get("finished_at"),
                    "kus_extracted": result.get("kus_extracted", 0),
                    "parse_success_rate": result.get("parse_success_rate", 0),
                }
                _save_progress(progress)

            status_icon = "✓" if result["status"] == "done" else "⚠" if result["status"] == "dry_run" else "✗"
            logger.info(
                "[%d/%d] %s %s: kus=%s, parse=%.0f%%",
                i + 1, len(books), status_icon, book_id,
                result.get("kus_extracted", "N/A"),
                result.get("parse_success_rate", 0) * 100,
            )

        except Exception as e:
            logger.error("[%d/%d] FAIL %s: %s", i + 1, len(books), book_id, e)
            result = {
                "book_id": book_id,
                "title": book["title"],
                "status": "failed",
                "error": str(e),
            }
            results.append(result)

            if not dry_run:
                progress["books"][book_id] = {
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.now().isoformat(),
                }
                _save_progress(progress)

        # Inter-book delay
        if not dry_run and i < len(books) - 1:
            logger.info("Waiting %.1fs before next book...", delay_books)
            time.sleep(delay_books)

    return results


# --- Status Display ---


def _print_status(progress: dict, catalog_books: list[dict]) -> None:
    """Print batch progress status."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # Summary
    book_progress = progress.get("books", {})
    done_count = sum(1 for v in book_progress.values() if v.get("status") == "done")
    failed_count = sum(1 for v in book_progress.values() if v.get("status") == "failed")
    total_kus = sum(v.get("kus_extracted", 0) for v in book_progress.values())

    console.print(f"\n[bold]Batch Progress[/bold] (updated: {progress.get('last_updated', 'N/A')})")
    console.print(f"  Done: [green]{done_count}[/green] | Failed: [red]{failed_count}[/red] | Total KUs: [cyan]{total_kus}[/cyan]")

    # Catalog status
    status_counts: dict[str, int] = {}
    for b in catalog_books:
        s = b.get("status", "pending")
        status_counts[s] = status_counts.get(s, 0) + 1
    console.print(f"  Catalog: {status_counts}")

    # Detail table
    if book_progress:
        table = Table(title="Book Progress")
        table.add_column("Book ID", style="cyan")
        table.add_column("Status")
        table.add_column("KUs", justify="right")
        table.add_column("Parse %", justify="right")

        for bid, info in sorted(book_progress.items()):
            status = info.get("status", "?")
            style = "green" if status == "done" else "red"
            kus = str(info.get("kus_extracted", ""))
            parse_pct = f"{info.get('parse_success_rate', 0) * 100:.0f}%" if info.get("parse_success_rate") else ""
            table.add_row(bid, f"[{style}]{status}[/{style}]", kus, parse_pct)

        console.print(table)


# --- CLI ---


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Batch ingest from catalog")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pilot", action="store_true", help="status=pilot 도서만")
    group.add_argument("--books", type=str, help="쉼표 구분 book_id 목록")
    group.add_argument("--domain", type=str, help="도메인 필터")
    group.add_argument("--all", action="store_true", help="done 제외 전체")
    group.add_argument("--status", action="store_true", help="진행 현황 출력")
    group.add_argument("--retry-failed", action="store_true", help="실패 도서 재시도")

    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 미리보기")
    parser.add_argument("--workers", type=int, default=None, help="LLM 병렬 호출 수 (기본: config.yaml batch.max_workers)")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그")

    args = parser.parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = _load_config()
    catalog_books = _load_catalog(cfg)
    progress = _load_progress()

    # Status mode
    if args.status:
        _print_status(progress, catalog_books)
        return

    # Filter
    book_ids = args.books.split(",") if args.books else None
    books = _filter_books(
        catalog_books,
        pilot=args.pilot,
        book_ids=book_ids,
        domain=args.domain,
        all_books=args.all,
        retry_failed=args.retry_failed,
        progress=progress,
    )

    if not books:
        print("대상 도서가 없습니다. --pilot, --books, --domain, --all 중 하나를 지정하세요.")
        return

    # Resolve max_workers: CLI > config > default(1)
    max_workers = args.workers or cfg.get("batch", {}).get("max_workers", 1)

    # Print plan
    print(f"\n{'=' * 60}")
    print(f"Batch Ingest: {len(books)}권 {'(DRY RUN)' if args.dry_run else ''} [workers={max_workers}]")
    print(f"{'=' * 60}")
    for b in books:
        print(f"  {b['id']}: {b['title']} ({b['domain']})")
    print()

    # Run
    results = run_batch(books, cfg, dry_run=args.dry_run, progress=progress, max_workers=max_workers)

    # Summary
    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"{'=' * 60}")
    for r in results:
        icon = "✓" if r["status"] == "done" else "⚠" if r["status"] == "dry_run" else "✗"
        kus = r.get("kus_extracted", r.get("spans_count", "N/A"))
        print(f"  {icon} {r['book_id']}: {r['title']} — kus={kus}, status={r['status']}")
        if r.get("error"):
            print(f"    ERROR: {r['error']}")

    done_count = sum(1 for r in results if r["status"] == "done")
    fail_count = sum(1 for r in results if r["status"] == "failed")
    total_kus = sum(r.get("kus_extracted", 0) for r in results)
    print(f"\nDone: {done_count} | Failed: {fail_count} | Total KUs: {total_kus}")


if __name__ == "__main__":
    main()
