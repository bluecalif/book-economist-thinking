"""Stage G.1: Typer CLI — ks ingest / search / generate content / stats.

Usage:
    python -m src.cli ingest <json_path>
    python -m src.cli search <query>
    python -m src.cli generate content --topic <T> --format <F>
    python -m src.cli stats
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load .env before any API calls
load_dotenv()

console = Console()
app = typer.Typer(
    name="ks",
    help="Knowledge System CLI — 지식 추출·검색·생성 파이프라인",
    no_args_is_help=True,
)
generate_app = typer.Typer(help="콘텐츠 생성 명령어")
app.add_typer(generate_app, name="generate")

# --- Config helpers ---

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_config(config_path: Path | None = None) -> dict:
    """Load config.yaml."""
    path = config_path or (PROJECT_ROOT / "config.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_catalog(cfg: dict) -> list[dict]:
    """Load books_catalog.yaml → books list."""
    catalog_path = PROJECT_ROOT / cfg["paths"]["catalog"]
    with open(catalog_path, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)
    return catalog["books"]


def _find_book(books: list[dict], book_id: str) -> dict | None:
    """카탈로그에서 book_id로 책 찾기."""
    for b in books:
        if b["id"] == book_id:
            return b
    return None


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# --- Global options ---

config_option = typer.Option(None, "--config", "-c", help="config.yaml 경로")
verbose_option = typer.Option(False, "--verbose", "-v", help="상세 로그 출력")


# --- ingest ---

@app.command()
def ingest(
    json_path: str = typer.Argument(..., help="입력 JSON 파일 경로"),
    book_id: Optional[str] = typer.Option(None, "--book-id", help="책 ID (기본: config.yaml 첫 번째 책)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="DB 저장 없이 미리보기"),
    config: Optional[Path] = config_option,
    verbose: bool = verbose_option,
) -> None:
    """JSON 파싱 → KU 추출 → 임베딩 → Vault 마크다운 생성."""
    _setup_logging(verbose)
    cfg = _load_config(config)

    json_file = Path(json_path)
    if not json_file.exists():
        console.print(f"[red]파일을 찾을 수 없습니다: {json_path}[/red]")
        raise typer.Exit(1)

    db_path = PROJECT_ROOT / cfg["paths"]["db"]
    chroma_dir = PROJECT_ROOT / cfg["paths"]["chroma"]
    vault_dir = PROJECT_ROOT / "vault"

    # Resolve book config from catalog
    catalog_books = _load_catalog(cfg)
    bid = book_id or catalog_books[0]["id"]
    book_cfg = _find_book(catalog_books, bid)
    if not book_cfg:
        console.print(f"[red]카탈로그에서 책을 찾을 수 없습니다: {bid}[/red]")
        raise typer.Exit(1)
    title = book_cfg["title"]
    domain = book_cfg.get("domain", "경제/경영")

    if dry_run:
        console.print("[yellow]--- DRY RUN 모드 ---[/yellow]")
        from src.ingest.pdf_parser import load_text_json, parse_chapters

        data = load_text_json(json_file)
        spans = parse_chapters(data, bid)
        console.print(f"총 페이지: {data['metadata']['total_pages']}")
        console.print(f"파싱될 spans: {len(spans)}")
        console.print(f"건너뛸 빈 페이지: {data['metadata']['total_pages'] - len(spans)}")

        # Show first 5 spans as preview
        table = Table(title="미리보기 (처음 5건)")
        table.add_column("ID", style="cyan")
        table.add_column("Page", justify="right")
        table.add_column("Text (100자)", max_width=100)
        for s in spans[:5]:
            table.add_row(s["id"], str(s["page"]), s["text"][:100] + "…")
        console.print(table)
        return

    # Step 1: JSON → raw_spans
    console.print("[bold]Step 1/3:[/bold] JSON 파싱 → raw_spans")
    from src.ingest.pdf_parser import ingest_book

    result = ingest_book(
        db_path=db_path,
        json_path=json_file,
        book_id=bid,
        title=title,
        domain=domain,
    )
    console.print(f"  spans 삽입: {result['spans_inserted']}건 (DB 총 {result['spans_in_db']}건)")

    # Step 2: KU 추출 + 임베딩
    console.print("[bold]Step 2/3:[/bold] KU 추출 + 임베딩 (API 호출, 시간 소요)")
    from src.ingest.ku_extractor import extract_kus_from_spans

    metrics = extract_kus_from_spans(
        db_path=db_path,
        chroma_dir=chroma_dir,
        book_id=bid,
        domain=domain,
        model=cfg["models"]["ku_extraction"],
        embedding_model=cfg["models"]["embedding"],
    )
    console.print(f"  추출 KUs: {metrics['total_kus_extracted']}건")
    console.print(f"  파싱 성공률: {metrics['parse_success_rate'] * 100:.1f}%")

    # Step 3: Vault 마크다운 렌더링
    console.print("[bold]Step 3/3:[/bold] Vault 마크다운 생성")
    from src.vault.renderer import render_all_kus

    rendered = render_all_kus(db_path=db_path, output_dir=vault_dir, book_id=bid)
    console.print(f"  렌더링: {rendered}건 → {vault_dir}/domains/")

    console.print("\n[green]✓ Ingest 완료[/green]")


# --- search ---

@app.command()
def search(
    query: str = typer.Argument(..., help="검색 쿼리 (자연어)"),
    top_k: int = typer.Option(10, "--top-k", "-k", help="최대 결과 수"),
    threshold: float = typer.Option(0.6, "--threshold", "-t", help="유사도 임계값 (cosine distance)"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="도메인 필터"),
    config: Optional[Path] = config_option,
    verbose: bool = verbose_option,
) -> None:
    """벡터 검색 — 쿼리와 유사한 KU를 검색합니다."""
    _setup_logging(verbose)

    from src.search.vector import format_results_rich, search_kus

    results = search_kus(
        query,
        top_k=top_k,
        threshold=threshold,
        domain=domain,
    )
    format_results_rich(results)


# --- generate content ---

@generate_app.command("content")
def generate_content(
    topic: str = typer.Option(..., "--topic", help="생성할 콘텐츠 주제"),
    format: str = typer.Option("blog", "--format", "-f", help="출력 형식: blog, summary, thread"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="참조할 KU 수"),
    no_save: bool = typer.Option(False, "--no-save", help="DB에 저장하지 않음"),
    config: Optional[Path] = config_option,
    verbose: bool = verbose_option,
) -> None:
    """토픽 기반 콘텐츠 생성 (blog, summary, thread)."""
    _setup_logging(verbose)

    from src.generation.content import generate_content as gen

    try:
        result = gen(
            topic=topic,
            format=format,
            top_k=top_k,
            save=not no_save,
        )
    except ValueError as e:
        console.print(f"[red]오류: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]── {format.upper()}: {topic} ──[/bold cyan]\n")
    console.print(result.content)
    console.print(f"\n[dim]생성 ID: {result.generation_id} | KU {len(result.ku_ids)}건 참조[/dim]")


# --- stats ---

@app.command()
def stats(
    config: Optional[Path] = config_option,
    verbose: bool = verbose_option,
) -> None:
    """DB 통계 — books, spans, KUs, generations, 도메인 분포."""
    _setup_logging(verbose)
    cfg = _load_config(config)

    import sqlite3

    db_path = PROJECT_ROOT / cfg["paths"]["db"]

    if not db_path.exists():
        console.print(f"[red]DB 파일 없음: {db_path}[/red]")
        raise typer.Exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Basic counts
    books = conn.execute("SELECT COUNT(*) as cnt FROM books").fetchone()["cnt"]
    spans = conn.execute("SELECT COUNT(*) as cnt FROM raw_spans").fetchone()["cnt"]
    kus = conn.execute("SELECT COUNT(*) as cnt FROM knowledge_units").fetchone()["cnt"]
    edges = conn.execute("SELECT COUNT(*) as cnt FROM edges").fetchone()["cnt"]
    gens = conn.execute("SELECT COUNT(*) as cnt FROM generations").fetchone()["cnt"]

    table = Table(title="Knowledge System 통계")
    table.add_column("항목", style="bold")
    table.add_column("건수", justify="right", style="cyan")
    table.add_row("Books", str(books))
    table.add_row("Raw Spans", str(spans))
    table.add_row("Knowledge Units", str(kus))
    table.add_row("Edges", str(edges))
    table.add_row("Generations", str(gens))
    console.print(table)

    # Domain distribution
    rows = conn.execute(
        "SELECT domain, COUNT(*) as cnt FROM knowledge_units GROUP BY domain ORDER BY cnt DESC"
    ).fetchall()

    if rows:
        dtable = Table(title="도메인 분포")
        dtable.add_column("도메인", style="bold")
        dtable.add_column("KU 수", justify="right", style="cyan")
        for r in rows:
            dtable.add_row(r["domain"], str(r["cnt"]))
        console.print(dtable)

    # ChromaDB count
    chroma_dir = PROJECT_ROOT / cfg["paths"]["chroma"]
    if chroma_dir.exists():
        try:
            from src.db.vectors import init_chroma

            collection = init_chroma(chroma_dir)
            chroma_count = collection.count()
            console.print(f"\nChromaDB 임베딩: [cyan]{chroma_count}[/cyan]건")
        except Exception as e:
            console.print(f"\n[yellow]ChromaDB 접근 오류: {e}[/yellow]")

    conn.close()


# --- Entry point ---

if __name__ == "__main__":
    app()
