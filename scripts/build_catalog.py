"""H.1: 북 카탈로그 빌더.

CSV + JSON 파일 매칭 → books_catalog.yaml 생성.
소스 CSV: C:/Projects-2026/maintenance/books-final-processor/docs/100권 노션 원본_수정.csv
소스 JSON: C:/Projects-2026/maintenance/books-final-processor/data/output/text/
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import yaml

# --- 상수 ---

DOMAIN_SHORT_MAP = {
    "경제/경영": "econ",
    "역사/사회": "hist",
    "인문/자기계발": "humn",
    "과학/기술": "sci",
}

CSV_PATH = Path(
    "C:/Projects-2026/maintenance/books-final-processor/docs/100권 노션 원본_수정.csv"
)
JSON_DIR = Path(
    "C:/Projects-2026/maintenance/books-final-processor/data/output/text/"
)
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "books_catalog.yaml"

# 기존 1권 — 이미 처리 완료
DONE_TITLE = "경제학자의 생각법"
DONE_ID = "econ-thinking-001"


def _normalize(s: str) -> str:
    """공백 제거 정규화."""
    return re.sub(r"\s+", "", s)


def _match_json_file(
    title: str, json_files: list[str], used: set[str] | None = None,
) -> str | None:
    """CSV Title ↔ JSON 파일명 매칭 (최장 접두사 우선, 이미 사용된 파일 제외)."""
    title_norm = _normalize(title)
    best_match = None
    best_score = 0

    for jf in json_files:
        if used and jf in used:
            continue
        parts = jf.split("_", 1)
        if len(parts) < 2:
            continue
        fname_title = parts[1].replace("_text.json", "").replace("_", "")
        # 공통 접두사 길이 계산
        common = 0
        for a, b in zip(title_norm, fname_title):
            if a == b:
                common += 1
            else:
                break
        if common >= 2 and common > best_score:
            best_score = common
            best_match = jf

    return best_match


def build_catalog() -> dict:
    """카탈로그 빌드 → dict."""
    # CSV 로드
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # JSON 파일 목록
    json_files = sorted(f for f in os.listdir(JSON_DIR) if f.endswith("_text.json"))

    # 도메인별 시퀀스 카운터
    domain_seq: dict[str, int] = {short: 0 for short in DOMAIN_SHORT_MAP.values()}

    books: list[dict] = []
    unmatched: list[str] = []
    used_files: set[str] = set()

    for row in rows:
        title = row["Title"].strip()
        domain = row["분야"].strip()
        author = row["저자"].strip()
        year_str = row["연도"].strip()
        topic = row["Topic"].strip()

        year = int(year_str) if year_str.isdigit() else 0

        # JSON 매칭
        json_file = _match_json_file(title, json_files, used_files)
        if not json_file:
            unmatched.append(title)
            continue
        used_files.add(json_file)

        # book_id 할당
        domain_short = DOMAIN_SHORT_MAP.get(domain, domain[:4].lower())

        if title == DONE_TITLE:
            book_id = DONE_ID
            status = "done"
        else:
            domain_seq[domain_short] = domain_seq.get(domain_short, 0) + 1
            seq = domain_seq[domain_short]
            book_id = f"{domain_short}-{seq:03d}"
            status = "pending"

        books.append({
            "id": book_id,
            "title": title,
            "author": author,
            "domain": domain,
            "year": year,
            "topic": topic,
            "json_file": json_file,
            "status": status,
        })

    if unmatched:
        print(f"WARNING: {len(unmatched)} unmatched titles:")
        for t in unmatched:
            print(f"  - {t}")

    catalog = {
        "domain_short_map": DOMAIN_SHORT_MAP,
        "books": books,
    }
    return catalog


def main():
    catalog = build_catalog()
    books = catalog["books"]

    # YAML 출력
    # PyYAML 한국어 지원을 위해 allow_unicode=True
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(
            catalog,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    # 통계
    domains = {}
    statuses = {}
    for b in books:
        domains[b["domain"]] = domains.get(b["domain"], 0) + 1
        statuses[b["status"]] = statuses.get(b["status"], 0) + 1

    print(f"카탈로그 생성 완료: {OUTPUT_PATH}")
    print(f"  총 도서: {len(books)}")
    print(f"  도메인: {domains}")
    print(f"  상태: {statuses}")


if __name__ == "__main__":
    main()
