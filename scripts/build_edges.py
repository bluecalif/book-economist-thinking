"""Stage I.2p: 배치 edge 생성 스크립트.

KU 간 관계를 LLM으로 판별하여 edges 테이블에 저장.

Usage:
    python scripts/build_edges.py --mode within --dry-run
    python scripts/build_edges.py --mode cross-chapter
    python scripts/build_edges.py --mode cross-domain
    python scripts/build_edges.py --mode all --workers 5
    python scripts/build_edges.py --mode all --threshold 0.35
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from src.db.models import count_edges, get_connection, init_db
from src.db.vectors import init_chroma
from src.graph.edge_builder import (
    build_edges,
    find_cross_chapter_candidates,
    find_cross_domain_candidates,
    find_within_chapter_candidates,
)

logger = logging.getLogger(__name__)


def _load_config() -> dict:
    with open(PROJECT_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_pilot_books(cfg: dict) -> list[dict]:
    """status=done 또는 pilot인 책 목록."""
    catalog_path = PROJECT_ROOT / cfg["paths"]["catalog"]
    with open(catalog_path, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)
    return [b for b in catalog["books"] if b.get("status") in ("done", "pilot")]


def main():
    parser = argparse.ArgumentParser(description="KU edge 배치 생성")
    parser.add_argument(
        "--mode",
        choices=["within", "cross-chapter", "cross-domain", "all"],
        default="all",
        help="edge 검색 모드 (default: all)",
    )
    parser.add_argument("--workers", type=int, default=5, help="LLM 병렬 호출 수")
    parser.add_argument("--threshold", type=float, default=0.35, help="유사도 임계값")
    parser.add_argument("--dry-run", action="store_true", help="후보만 확인, edge 미생성")
    parser.add_argument("--book-id", type=str, default=None, help="특정 책만 처리")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = _load_config()
    db_path = PROJECT_ROOT / cfg["paths"]["db"]
    chroma_dir = PROJECT_ROOT / cfg["paths"]["chroma"]
    cache_db_path = PROJECT_ROOT / "data" / "llm_cache.db"
    model = cfg["models"]["ku_extraction"]

    conn = init_db(db_path)
    col = init_chroma(chroma_dir)

    edges_before = count_edges(conn)
    print(f"현재 edges: {edges_before}건")

    # 대상 책 결정
    if args.book_id:
        book_ids = [args.book_id]
    else:
        books = _load_pilot_books(cfg)
        book_ids = [b["id"] for b in books]

    print(f"대상 books: {book_ids}")

    all_candidates: list[tuple[str, str, float]] = []

    # --- Tier 1: Within-chapter ---
    if args.mode in ("within", "all"):
        print("\n=== Tier 1: Within-chapter ===")
        for bid in book_ids:
            candidates = find_within_chapter_candidates(
                col, conn, bid, top_k=5, threshold=args.threshold
            )
            print(f"  {bid}: {len(candidates)} 후보 쌍")
            all_candidates.extend(candidates)

    # --- Tier 2: Cross-chapter ---
    if args.mode in ("cross-chapter", "all"):
        print("\n=== Tier 2: Cross-chapter (centroid) ===")
        for bid in book_ids:
            candidates = find_cross_chapter_candidates(
                col, conn, bid, centroids_per_ch=5, top_k=3, threshold=args.threshold
            )
            print(f"  {bid}: {len(candidates)} 후보 쌍")
            all_candidates.extend(candidates)

    # --- Cross-domain ---
    if args.mode in ("cross-domain", "all"):
        print("\n=== Cross-domain ===")
        candidates = find_cross_domain_candidates(
            col, conn, centroids_per_ch=5, top_k=3, threshold=args.threshold
        )
        print(f"  전체: {len(candidates)} 후보 쌍")
        all_candidates.extend(candidates)

    # 중복 제거
    seen = set()
    unique_candidates = []
    for a, b, s in all_candidates:
        pair = tuple(sorted([a, b]))
        if pair not in seen:
            seen.add(pair)
            unique_candidates.append((a, b, s))

    print(f"\n총 후보 쌍 (중복 제거): {len(unique_candidates)}")

    if args.dry_run:
        print("\n[DRY RUN] edge 생성 생략")
        # 유사도 분포 출력
        if unique_candidates:
            sims = [s for _, _, s in unique_candidates]
            print(f"  유사도 범위: {min(sims):.3f} ~ {max(sims):.3f}")
            print(f"  평균 유사도: {sum(sims)/len(sims):.3f}")
        conn.close()
        return

    # LLM 판정 + edge 생성
    print(f"\nLLM 판정 시작 (workers={args.workers})...")
    start = time.time()

    metrics = build_edges(
        conn,
        col,
        unique_candidates,
        model=model,
        cache_db_path=cache_db_path,
        max_workers=args.workers,
        source="auto",
    )

    elapsed = time.time() - start
    edges_after = count_edges(conn)

    print(f"\n=== 결과 ===")
    print(f"  후보 쌍: {metrics['total_candidates']}")
    print(f"  생성된 edges: {metrics['edges_created']}")
    print(f"  거부된 쌍: {metrics['edges_rejected']}")
    print(f"  DB 총 edges: {edges_after}")
    print(f"  소요 시간: {elapsed:.1f}초")

    conn.close()


if __name__ == "__main__":
    main()
