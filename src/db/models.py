"""SQLite schema and CRUD helpers for the Knowledge System.

Tables: books, raw_spans, knowledge_units, edges, generations
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DDL = """
CREATE TABLE IF NOT EXISTS books (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    author      TEXT,
    domain      TEXT NOT NULL,
    filepath    TEXT,
    total_pages INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_spans (
    id          TEXT PRIMARY KEY,
    book_id     TEXT NOT NULL REFERENCES books(id),
    chapter     TEXT,
    page        INTEGER,
    seq         INTEGER,
    text        TEXT NOT NULL,
    span_type   TEXT DEFAULT 'paragraph',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_units (
    id                  TEXT PRIMARY KEY,
    book_id             TEXT NOT NULL REFERENCES books(id),
    claim               TEXT NOT NULL,
    evidence_summary    TEXT,
    counter_summary     TEXT,
    domain              TEXT NOT NULL,
    subdomain           TEXT,
    tags                TEXT,
    confidence          REAL DEFAULT 0.5,
    maturity            TEXT DEFAULT 'M0',
    source_spans        TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS edges (
    id              TEXT PRIMARY KEY,
    from_ku_id      TEXT NOT NULL REFERENCES knowledge_units(id),
    to_ku_id        TEXT NOT NULL REFERENCES knowledge_units(id),
    relation_type   TEXT NOT NULL,
    strength        REAL DEFAULT 0.5,
    source          TEXT DEFAULT 'auto',
    description     TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generations (
    id          TEXT PRIMARY KEY,
    mode        TEXT NOT NULL,
    format      TEXT,
    prompt      TEXT,
    output      TEXT NOT NULL,
    ku_ids      TEXT NOT NULL,
    rating      INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_raw_spans_book ON raw_spans(book_id);
CREATE INDEX IF NOT EXISTS idx_ku_book ON knowledge_units(book_id);
CREATE INDEX IF NOT EXISTS idx_ku_domain ON knowledge_units(domain);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_ku_id);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_ku_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(relation_type);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Create a connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """Create tables if they don't exist and return the connection."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    conn.executescript(DDL)
    return conn


# --- books ---

def insert_book(
    conn: sqlite3.Connection,
    *,
    id: str,
    title: str,
    domain: str,
    author: str | None = None,
    filepath: str | None = None,
    total_pages: int | None = None,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO books (id, title, author, domain, filepath, total_pages) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (id, title, author, domain, filepath, total_pages),
    )
    conn.commit()


def get_book(conn: sqlite3.Connection, book_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return dict(row) if row else None


def list_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM books").fetchall()]


# --- raw_spans ---

def insert_raw_span(
    conn: sqlite3.Connection,
    *,
    id: str,
    book_id: str,
    chapter: str | None = None,
    page: int | None = None,
    seq: int = 1,
    text: str,
    span_type: str = "paragraph",
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO raw_spans (id, book_id, chapter, page, seq, text, span_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (id, book_id, chapter, page, seq, text, span_type),
    )


def bulk_insert_raw_spans(
    conn: sqlite3.Connection,
    spans: list[dict[str, Any]],
) -> int:
    """Insert multiple raw_spans in a single transaction. Returns count inserted."""
    cursor = conn.executemany(
        "INSERT OR IGNORE INTO raw_spans (id, book_id, chapter, page, seq, text, span_type) "
        "VALUES (:id, :book_id, :chapter, :page, :seq, :text, :span_type)",
        spans,
    )
    conn.commit()
    return cursor.rowcount


def get_raw_spans_by_book(conn: sqlite3.Connection, book_id: str) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM raw_spans WHERE book_id = ? ORDER BY page, seq",
            (book_id,),
        ).fetchall()
    ]


def get_raw_spans_by_chapter(
    conn: sqlite3.Connection, book_id: str, chapter: str
) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM raw_spans WHERE book_id = ? AND chapter = ? ORDER BY page, seq",
            (book_id, chapter),
        ).fetchall()
    ]


# --- knowledge_units ---

def insert_ku(
    conn: sqlite3.Connection,
    *,
    id: str,
    book_id: str,
    claim: str,
    domain: str,
    evidence_summary: str | None = None,
    counter_summary: str | None = None,
    subdomain: str | None = None,
    tags: list[str] | None = None,
    confidence: float = 0.5,
    maturity: str = "M0",
    source_spans: list[str] | None = None,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO knowledge_units "
        "(id, book_id, claim, evidence_summary, counter_summary, domain, subdomain, "
        "tags, confidence, maturity, source_spans) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            id, book_id, claim, evidence_summary, counter_summary,
            domain, subdomain,
            json.dumps(tags, ensure_ascii=False) if tags else None,
            confidence, maturity,
            json.dumps(source_spans) if source_spans else None,
        ),
    )
    conn.commit()


def get_ku(conn: sqlite3.Connection, ku_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM knowledge_units WHERE id = ?", (ku_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d["tags"] else []
    d["source_spans"] = json.loads(d["source_spans"]) if d["source_spans"] else []
    return d


def list_kus_by_book(conn: sqlite3.Connection, book_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM knowledge_units WHERE book_id = ? ORDER BY id", (book_id,)
    ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        d["source_spans"] = json.loads(d["source_spans"]) if d["source_spans"] else []
        results.append(d)
    return results


def update_ku(
    conn: sqlite3.Connection,
    ku_id: str,
    **fields: Any,
) -> bool:
    """Update specified fields of a KU. Returns True if row was updated."""
    if not fields:
        return False
    # Serialize JSON fields
    if "tags" in fields and isinstance(fields["tags"], list):
        fields["tags"] = json.dumps(fields["tags"], ensure_ascii=False)
    if "source_spans" in fields and isinstance(fields["source_spans"], list):
        fields["source_spans"] = json.dumps(fields["source_spans"])
    fields["updated_at"] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [ku_id]
    cursor = conn.execute(
        f"UPDATE knowledge_units SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    return cursor.rowcount > 0


# --- count helpers ---

def count_raw_spans(conn: sqlite3.Connection, book_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM raw_spans WHERE book_id = ?", (book_id,)
    ).fetchone()
    return row["cnt"]


def count_kus(conn: sqlite3.Connection, book_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM knowledge_units WHERE book_id = ?", (book_id,)
    ).fetchone()
    return row["cnt"]
