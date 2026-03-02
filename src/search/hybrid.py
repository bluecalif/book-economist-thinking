"""Hybrid search — Vector similarity + Graph traversal 복합 검색.

Stage J.1: vector top-K 시드 → graph BFS 확장 → merge + re-rank.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.db.models import get_connection, get_ku
from src.graph.traversal import traverse
from src.search.vector import search_kus

logger = logging.getLogger(__name__)


@dataclass
class HybridResult:
    """복합 검색 결과."""

    ku_id: str
    claim: str
    domain: str
    book_id: str
    confidence: float
    similarity: float       # vector score (0이면 graph-only)
    path_score: float        # graph score (0이면 vector-only)
    hybrid_score: float      # 통합 점수
    source: str              # "vector" | "graph" | "both"
    relation_chain: list[dict] | None = field(default=None)


def _load_config() -> dict[str, Any]:
    cfg_path = Path(__file__).resolve().parents[2] / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def hybrid_search(
    query: str,
    *,
    top_k: int = 10,
    vector_top_k: int = 20,
    graph_depth: int = 2,
    graph_seeds: int = 5,
    alpha: float = 0.6,
    domain: str | None = None,
    db_path: str | Path | None = None,
) -> list[HybridResult]:
    """Vector + Graph 복합 검색.

    Args:
        query: 자연어 검색 쿼리.
        top_k: 최종 반환 결과 수.
        vector_top_k: 벡터 검색 후보 수.
        graph_depth: BFS 탐색 깊이.
        graph_seeds: 그래프 확장할 상위 시드 KU 수.
        alpha: 벡터/그래프 가중치 (0~1). 높을수록 벡터 우세.
        domain: 도메인 필터 (벡터 검색에만 적용).
        db_path: SQLite DB 경로.

    Returns:
        hybrid_score 내림차순 정렬된 HybridResult 리스트.
    """
    cfg = _load_config()
    project_root = Path(__file__).resolve().parents[2]
    db_path = db_path or project_root / cfg["paths"]["db"]

    # --- 1. Vector Search ---
    vector_results = search_kus(
        query, top_k=vector_top_k, domain=domain, db_path=db_path,
    )
    logger.info("벡터 검색: %d건", len(vector_results))

    # ku_id → {similarity, claim, domain, ...} 매핑
    vector_map: dict[str, dict[str, Any]] = {}
    for vr in vector_results:
        vector_map[vr.ku_id] = {
            "similarity": vr.similarity,
            "claim": vr.claim,
            "domain": vr.domain,
            "confidence": vr.confidence,
        }

    # --- 2. Graph Expand ---
    graph_map: dict[str, dict[str, Any]] = {}  # ku_id → best path info
    seed_ids = [vr.ku_id for vr in vector_results[:graph_seeds]]

    conn = get_connection(db_path)
    try:
        for seed_id in seed_ids:
            paths = traverse(conn, seed_id, depth=graph_depth)
            for p in paths:
                kid = p["ku_id"]
                # 같은 KU에 대해 여러 경로 중 최고 path_score만 유지
                if kid not in graph_map or p["path_score"] > graph_map[kid]["path_score"]:
                    graph_map[kid] = {
                        "path_score": p["path_score"],
                        "relation_chain": p["path"],
                        "ku_data": p["ku_data"],
                    }

        logger.info("그래프 확장: %d건 (시드 %d개)", len(graph_map), len(seed_ids))

        # --- 3. Merge + Re-rank ---
        all_ku_ids = set(vector_map.keys()) | set(graph_map.keys())

        # path_score 정규화 (max normalization)
        max_path = max(
            (g["path_score"] for g in graph_map.values()), default=1.0,
        )
        if max_path <= 0:
            max_path = 1.0

        merged: list[HybridResult] = []
        for kid in all_ku_ids:
            in_vector = kid in vector_map
            in_graph = kid in graph_map

            sim = vector_map[kid]["similarity"] if in_vector else 0.0
            raw_ps = graph_map[kid]["path_score"] if in_graph else 0.0
            norm_ps = raw_ps / max_path

            h_score = alpha * sim + (1 - alpha) * norm_ps

            # source 결정
            if in_vector and in_graph:
                source = "both"
            elif in_vector:
                source = "vector"
            else:
                source = "graph"

            # claim, domain, book_id, confidence 결정
            if in_vector:
                claim = vector_map[kid]["claim"]
                domain_val = vector_map[kid]["domain"]
                confidence = vector_map[kid]["confidence"]
                # book_id는 벡터 결과에 없으므로 DB 조회 또는 graph 데이터 사용
                if in_graph:
                    book_id = graph_map[kid]["ku_data"].get("book_id", "")
                else:
                    ku = get_ku(conn, kid)
                    book_id = ku["book_id"] if ku else ""
            else:
                # graph-only
                ku_data = graph_map[kid]["ku_data"]
                claim = ku_data.get("claim", "")
                domain_val = ku_data.get("domain", "")
                confidence = ku_data.get("confidence", 0.0)
                book_id = ku_data.get("book_id", "")

            relation_chain = graph_map[kid]["relation_chain"] if in_graph else None

            merged.append(HybridResult(
                ku_id=kid,
                claim=claim,
                domain=domain_val,
                book_id=book_id,
                confidence=confidence,
                similarity=round(sim, 4),
                path_score=round(raw_ps, 4),
                hybrid_score=round(h_score, 4),
                source=source,
                relation_chain=relation_chain,
            ))
    finally:
        conn.close()

    # hybrid_score 내림차순 정렬 → top_k
    merged.sort(key=lambda x: x.hybrid_score, reverse=True)
    results = merged[:top_k]

    logger.info(
        "복합 검색 완료: '%s' → %d건 (vector=%d, graph=%d, both=%d)",
        query,
        len(results),
        sum(1 for r in results if r.source == "vector"),
        sum(1 for r in results if r.source == "graph"),
        sum(1 for r in results if r.source == "both"),
    )
    return results


def format_hybrid_results_rich(results: list[HybridResult]) -> None:
    """Rich 테이블로 hybrid 검색 결과 출력."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if not results:
        console.print("[yellow]관련 KU 없음[/yellow]")
        return

    table = Table(title="Hybrid 검색 결과", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Vec", justify="right", width=6, style="blue")
    table.add_column("Graph", justify="right", width=6, style="green")
    table.add_column("Source", width=6)
    table.add_column("도메인", width=8)
    table.add_column("KU ID", style="cyan", width=22)
    table.add_column("Claim", max_width=45)

    source_style = {"vector": "blue", "graph": "green", "both": "bold yellow"}
    for i, r in enumerate(results, 1):
        claim_short = r.claim[:45] + "…" if len(r.claim) > 45 else r.claim
        style = source_style.get(r.source, "")
        table.add_row(
            str(i),
            f"{r.hybrid_score:.3f}",
            f"{r.similarity:.2f}" if r.similarity > 0 else "-",
            f"{r.path_score:.2f}" if r.path_score > 0 else "-",
            f"[{style}]{r.source}[/{style}]",
            r.domain,
            r.ku_id,
            claim_short,
        )

    console.print(table)
    console.print(f"총 {len(results)}건")
