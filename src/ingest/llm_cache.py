"""LLM 응답 캐시 — SQLite 기반.

동일한 (model, system_prompt, user_text) 조합은 한 번만 API 호출하고
이후에는 캐시에서 반환.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key   TEXT PRIMARY KEY,
    model       TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    response    TEXT NOT NULL,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "llm_cache.db"


def _get_conn(db_path: str | Path | None = None) -> sqlite3.Connection:
    """캐시 DB 연결 + 테이블 생성."""
    path = Path(db_path) if db_path else _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL)
    return conn


def _make_key(model: str, system_prompt: str, user_text: str) -> str:
    """캐시 키 생성 (SHA-256)."""
    raw = f"{model}|{system_prompt}|{user_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached(
    db_path: str | Path | None,
    model: str,
    system_prompt: str,
    user_text: str,
) -> str | None:
    """캐시에서 응답 조회. 없으면 None."""
    conn = _get_conn(db_path)
    key = _make_key(model, system_prompt, user_text)
    row = conn.execute(
        "SELECT response FROM llm_cache WHERE cache_key = ?", (key,)
    ).fetchone()
    conn.close()
    if row:
        logger.debug("Cache HIT: %s", key[:12])
        return row["response"]
    return None


def put_cached(
    db_path: str | Path | None,
    model: str,
    system_prompt: str,
    user_text: str,
    response: str,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> None:
    """캐시에 응답 저장."""
    conn = _get_conn(db_path)
    key = _make_key(model, system_prompt, user_text)
    prompt_hash = hashlib.sha256(
        f"{system_prompt}|{user_text}".encode("utf-8")
    ).hexdigest()
    conn.execute(
        """INSERT OR REPLACE INTO llm_cache
           (cache_key, model, prompt_hash, response, tokens_in, tokens_out)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (key, model, prompt_hash, response, tokens_in, tokens_out),
    )
    conn.commit()
    conn.close()
    logger.debug("Cache PUT: %s", key[:12])


def get_or_call(
    client: Any,
    model: str,
    system_prompt: str,
    user_text: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    cache_db_path: str | Path | None = None,
) -> str:
    """캐시 조회 → miss 시 API 호출 → 저장 → 반환."""
    # Cache lookup
    cached = get_cached(cache_db_path, model, system_prompt, user_text)
    if cached is not None:
        return cached

    # API call
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    response_text = response.choices[0].message.content or ""
    tokens_in = getattr(response.usage, "prompt_tokens", None)
    tokens_out = getattr(response.usage, "completion_tokens", None)

    # Cache store
    put_cached(
        cache_db_path,
        model,
        system_prompt,
        user_text,
        response_text,
        tokens_in,
        tokens_out,
    )

    return response_text
