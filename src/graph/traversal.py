"""Graph traversal — BFS + PathScore.

PathScore = HarmonicMean(edge_strengths) × Mean(KU_confidence)
"""

from __future__ import annotations

import sqlite3
from collections import deque
from typing import Any


def _harmonic_mean(values: list[float]) -> float:
    """조화 평균 계산. 0이 포함되면 0 반환."""
    if not values:
        return 0.0
    for v in values:
        if v <= 0:
            return 0.0
    return len(values) / sum(1.0 / v for v in values)


def traverse(
    conn: sqlite3.Connection,
    seed_ku_id: str,
    depth: int = 2,
) -> list[dict[str, Any]]:
    """BFS 그래프 탐색. seed_ku_id에서 depth hop까지 탐색.

    Returns: PathScore로 정렬된 path 리스트.
    각 path = {
        "ku_id": str,
        "hop": int,
        "path": [(ku_id, relation_type, strength), ...],
        "path_score": float,
        "ku_data": {"claim", "domain", "confidence", ...}
    }
    """
    # seed KU 존재 확인
    seed = conn.execute(
        "SELECT * FROM knowledge_units WHERE id = ?", (seed_ku_id,)
    ).fetchone()
    if not seed:
        return []

    visited: set[str] = {seed_ku_id}
    # queue: (ku_id, hop, path_edges)
    queue: deque[tuple[str, int, list[tuple[str, str, str, float]]]] = deque()
    # path_edges: [(from_ku, to_ku, relation_type, strength), ...]
    queue.append((seed_ku_id, 0, []))

    results: list[dict[str, Any]] = []

    while queue:
        current_id, current_hop, path_edges = queue.popleft()

        if current_hop > 0:
            # KU 데이터 가져오기
            ku_row = conn.execute(
                "SELECT id, claim, domain, confidence, maturity, book_id "
                "FROM knowledge_units WHERE id = ?",
                (current_id,),
            ).fetchone()
            if not ku_row:
                continue

            ku_data = dict(ku_row)

            # PathScore 계산
            edge_strengths = [e[3] for e in path_edges]
            # path 상의 모든 KU confidence 수집
            ku_ids_in_path = [seed_ku_id] + [e[1] for e in path_edges]
            confidences = []
            for kid in ku_ids_in_path:
                row = conn.execute(
                    "SELECT confidence FROM knowledge_units WHERE id = ?", (kid,)
                ).fetchone()
                if row:
                    confidences.append(row["confidence"])

            h_mean = _harmonic_mean(edge_strengths)
            c_mean = sum(confidences) / len(confidences) if confidences else 0.0
            path_score = h_mean * c_mean

            results.append({
                "ku_id": current_id,
                "hop": current_hop,
                "path": [
                    {
                        "from": e[0],
                        "to": e[1],
                        "relation_type": e[2],
                        "strength": e[3],
                    }
                    for e in path_edges
                ],
                "path_score": path_score,
                "ku_data": ku_data,
            })

        if current_hop >= depth:
            continue

        # 인접 edge 검색
        edges = conn.execute(
            "SELECT * FROM edges WHERE from_ku_id = ? OR to_ku_id = ? "
            "ORDER BY strength DESC",
            (current_id, current_id),
        ).fetchall()

        for edge in edges:
            edge = dict(edge)
            # 반대편 KU 결정
            neighbor_id = (
                edge["to_ku_id"]
                if edge["from_ku_id"] == current_id
                else edge["from_ku_id"]
            )

            if neighbor_id in visited:
                continue
            visited.add(neighbor_id)

            new_path = path_edges + [
                (current_id, neighbor_id, edge["relation_type"], edge["strength"])
            ]
            queue.append((neighbor_id, current_hop + 1, new_path))

    # PathScore 내림차순 정렬
    results.sort(key=lambda x: x["path_score"], reverse=True)
    return results
