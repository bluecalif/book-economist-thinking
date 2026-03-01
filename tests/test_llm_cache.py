"""H.cache 단위 테스트 — cache miss → API 호출, cache hit → DB 반환."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.ingest.llm_cache import get_cached, get_or_call, put_cached


def test_put_and_get(tmp_path: Path):
    """저장 후 조회 성공."""
    db = tmp_path / "cache.db"
    put_cached(db, "gpt-4", "sys", "user", "response-text", 10, 20)
    result = get_cached(db, "gpt-4", "sys", "user")
    assert result == "response-text"


def test_cache_miss(tmp_path: Path):
    """캐시 없으면 None."""
    db = tmp_path / "cache.db"
    result = get_cached(db, "gpt-4", "sys", "user-miss")
    assert result is None


def test_get_or_call_miss_then_hit(tmp_path: Path):
    """cache miss → API 호출 1회, 이후 hit → API 호출 없음."""
    db = tmp_path / "cache.db"

    # Mock OpenAI client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "LLM response"
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 100
    mock_client.chat.completions.create.return_value = mock_response

    # First call: cache miss → API call
    result1 = get_or_call(
        mock_client, "gpt-4", "system prompt", "user text",
        cache_db_path=db,
    )
    assert result1 == "LLM response"
    assert mock_client.chat.completions.create.call_count == 1

    # Second call: cache hit → no API call
    result2 = get_or_call(
        mock_client, "gpt-4", "system prompt", "user text",
        cache_db_path=db,
    )
    assert result2 == "LLM response"
    assert mock_client.chat.completions.create.call_count == 1  # still 1


def test_different_inputs_different_keys(tmp_path: Path):
    """입력이 다르면 다른 캐시 키."""
    db = tmp_path / "cache.db"
    put_cached(db, "gpt-4", "sys", "text-A", "response-A")
    put_cached(db, "gpt-4", "sys", "text-B", "response-B")

    assert get_cached(db, "gpt-4", "sys", "text-A") == "response-A"
    assert get_cached(db, "gpt-4", "sys", "text-B") == "response-B"
