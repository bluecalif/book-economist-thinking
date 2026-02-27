"""ChromaDB wrapper for KU embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

COLLECTION_NAME = "ku_embeddings"


def init_chroma(persist_dir: str | Path) -> chromadb.Collection:
    """Initialize ChromaDB client and return the KU embeddings collection."""
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def add_embeddings(
    collection: chromadb.Collection,
    *,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]] | None = None,
) -> None:
    """Add KU embeddings to the collection."""
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def query_similar(
    collection: chromadb.Collection,
    query_embedding: list[float],
    n_results: int = 10,
    where: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Query similar KUs by embedding vector."""
    kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def delete_embeddings(
    collection: chromadb.Collection,
    ids: list[str],
) -> None:
    """Delete embeddings by KU IDs."""
    collection.delete(ids=ids)
