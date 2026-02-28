"""Vector search module — query text → embedding → ChromaDB → KU results.

Stage E: E.1 search_kus, E.2 result formatting, E.3 domain filtering.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

from src.db.models import get_connection, get_ku
from src.db.vectors import init_chroma, query_similar

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 10
DEFAULT_THRESHOLD = 0.6  # cosine distance; lower = more similar


@dataclass
class SearchResult:
    """Single KU search result with metadata."""

    ku_id: str
    claim: str
    evidence_summary: str | None
    counter_summary: str | None
    domain: str
    subdomain: str | None
    confidence: float
    similarity: float  # 1 - cosine_distance


def _load_config() -> dict[str, Any]:
    """Load config.yaml from project root."""
    cfg_path = Path(__file__).resolve().parents[2] / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_openai_client() -> OpenAI:
    """Create OpenAI client from environment."""
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _embed_query(client: OpenAI, text: str, model: str) -> list[float]:
    """Generate embedding for a query string."""
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


def search_kus(
    query: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    threshold: float = DEFAULT_THRESHOLD,
    domain: str | None = None,
    db_path: str | Path | None = None,
    chroma_dir: str | Path | None = None,
    embedding_model: str | None = None,
) -> list[SearchResult]:
    """Search KUs by semantic similarity.

    Args:
        query: Natural language search query.
        top_k: Max results to return.
        threshold: Cosine distance threshold (0~2). Results with distance > threshold are excluded.
        domain: Optional domain filter (e.g. "경제").
        db_path: SQLite DB path. Defaults to config.yaml paths.db.
        chroma_dir: ChromaDB directory. Defaults to config.yaml paths.chroma.
        embedding_model: Embedding model name. Defaults to config.yaml models.embedding.

    Returns:
        List of SearchResult sorted by similarity (highest first).
    """
    cfg = _load_config()
    project_root = Path(__file__).resolve().parents[2]

    db_path = db_path or project_root / cfg["paths"]["db"]
    chroma_dir = chroma_dir or project_root / cfg["paths"]["chroma"]
    embedding_model = embedding_model or cfg["models"]["embedding"]

    # 1. Embed query
    client = _get_openai_client()
    query_emb = _embed_query(client, query, embedding_model)

    # 2. ChromaDB query (with optional domain filter)
    collection = init_chroma(chroma_dir)
    where = {"domain": domain} if domain else None
    raw = query_similar(collection, query_emb, n_results=top_k, where=where)

    # 3. Parse results + threshold filter + enrich from SQLite
    results: list[SearchResult] = []
    if not raw["ids"] or not raw["ids"][0]:
        logger.info("검색 결과 없음: '%s'", query)
        return results

    conn = get_connection(db_path)
    try:
        for ku_id, distance in zip(raw["ids"][0], raw["distances"][0]):
            if distance > threshold:
                continue

            ku = get_ku(conn, ku_id)
            if not ku:
                logger.warning("KU not found in DB: %s", ku_id)
                continue

            similarity = 1.0 - distance  # cosine distance → similarity
            results.append(
                SearchResult(
                    ku_id=ku_id,
                    claim=ku["claim"],
                    evidence_summary=ku.get("evidence_summary"),
                    counter_summary=ku.get("counter_summary"),
                    domain=ku["domain"],
                    subdomain=ku.get("subdomain"),
                    confidence=ku["confidence"],
                    similarity=round(similarity, 4),
                )
            )
    finally:
        conn.close()

    logger.info("검색 완료: '%s' → %d건 (threshold=%.2f)", query, len(results), threshold)
    return results


def format_results(results: list[SearchResult]) -> str:
    """Format search results as a readable text table.

    Returns:
        Formatted string. Returns "관련 KU 없음" if results is empty.
    """
    if not results:
        return "관련 KU 없음"

    lines: list[str] = []
    header = f"{'#':<3} {'유사도':>6} {'신뢰도':>6} {'도메인':<8} {'Claim'}"
    sep = "-" * 80
    lines.append(sep)
    lines.append(header)
    lines.append(sep)

    for i, r in enumerate(results, 1):
        claim_short = r.claim[:50] + "…" if len(r.claim) > 50 else r.claim
        lines.append(
            f"{i:<3} {r.similarity:>6.2%} {r.confidence:>6.1f} {r.domain:<8} {claim_short}"
        )

    lines.append(sep)
    lines.append(f"총 {len(results)}건")
    return "\n".join(lines)


def format_results_rich(results: list[SearchResult]) -> None:
    """Print search results using Rich table to stdout."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if not results:
        console.print("[yellow]관련 KU 없음[/yellow]")
        return

    table = Table(title="검색 결과", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("유사도", justify="right", width=7)
    table.add_column("신뢰도", justify="right", width=7)
    table.add_column("도메인", width=8)
    table.add_column("KU ID", style="cyan", width=22)
    table.add_column("Claim")

    for i, r in enumerate(results, 1):
        claim_short = r.claim[:60] + "…" if len(r.claim) > 60 else r.claim
        table.add_row(
            str(i),
            f"{r.similarity:.2%}",
            f"{r.confidence:.1f}",
            r.domain,
            r.ku_id,
            claim_short,
        )

    console.print(table)
    console.print(f"총 {len(results)}건")
