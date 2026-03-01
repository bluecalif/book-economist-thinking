"""Stage G.2: KU → Obsidian-compatible markdown renderer.

Renders knowledge_units from DB to vault/domains/{domain}/{ku_id}.md
with YAML frontmatter and structured body sections.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.db.models import get_connection, get_ku, list_kus_by_book, list_books

logger = logging.getLogger(__name__)


def _domain_to_dir(domain: str) -> str:
    """도메인 문자열 → 디렉터리명 (슬래시 → 하이픈)."""
    return domain.replace("/", "-")


def _format_tags_yaml(tags: list[str] | None) -> str:
    """Format tags as YAML inline list."""
    if not tags:
        return "[]"
    escaped = [t.replace('"', '\\"') for t in tags]
    return "[" + ", ".join(f'"{t}"' for t in escaped) + "]"


def render_ku(ku: dict[str, Any], output_dir: Path) -> Path:
    """Render a single KU dict to a markdown file.

    Args:
        ku: KU dict from DB (with parsed tags/source_spans).
        output_dir: Base output directory (e.g. vault/).

    Returns:
        Path to the written markdown file.
    """
    domain = ku.get("domain", "unknown")
    ku_id = ku["id"]

    # Build output path: output_dir/domains/{domain-dir}/{ku_id}.md
    domain_dir = output_dir / "domains" / _domain_to_dir(domain)
    domain_dir.mkdir(parents=True, exist_ok=True)
    filepath = domain_dir / f"{ku_id}.md"

    # YAML frontmatter
    tags = ku.get("tags", [])
    created = ku.get("created_at", datetime.now().isoformat())
    # Truncate to date only if it's a full datetime
    if isinstance(created, str) and len(created) > 10:
        created = created[:10]

    frontmatter_lines = [
        "---",
        f"id: {ku_id}",
        f"book: {ku.get('book_id', '')}",
        f"domain: {domain}",
        f"subdomain: {ku.get('subdomain') or ''}",
        f"confidence: {ku.get('confidence', 0.5)}",
        f"maturity: {ku.get('maturity', 'M0')}",
        f"tags: {_format_tags_yaml(tags)}",
        f"created: {created}",
        "---",
    ]

    # Body sections
    body_lines = [
        "",
        "## Claim",
        "",
        ku.get("claim", ""),
        "",
        "## Evidence",
        "",
    ]

    evidence = ku.get("evidence_summary")
    if evidence:
        body_lines.append(evidence)
    else:
        body_lines.append("(없음)")

    body_lines += [
        "",
        "## Counter",
        "",
    ]

    counter = ku.get("counter_summary")
    if counter:
        body_lines.append(counter)
    else:
        body_lines.append("(없음)")

    body_lines += [
        "",
        "## Connections",
        "",
        "(Phase 3에서 edges 기반 자동 생성)",
        "",
    ]

    content = "\n".join(frontmatter_lines + body_lines)
    filepath.write_text(content, encoding="utf-8")

    return filepath


def render_all_kus(
    db_path: str | Path,
    output_dir: str | Path,
    book_id: str | None = None,
) -> int:
    """Render all KUs from DB to markdown files.

    Args:
        db_path: SQLite DB path.
        output_dir: Base output directory (e.g. vault/).
        book_id: Optional book filter. If None, renders all books.

    Returns:
        Number of KU files rendered.
    """
    output_dir = Path(output_dir)
    conn = get_connection(db_path)
    count = 0

    try:
        if book_id:
            book_ids = [book_id]
        else:
            books = list_books(conn)
            book_ids = [b["id"] for b in books]

        for bid in book_ids:
            kus = list_kus_by_book(conn, bid)
            logger.info("Rendering %d KUs for book '%s'...", len(kus), bid)

            for ku in kus:
                render_ku(ku, output_dir)
                count += 1

    finally:
        conn.close()

    logger.info("Rendered %d KU files to %s", count, output_dir)
    return count
