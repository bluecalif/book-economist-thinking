"""H.2: 데이터 마이그레이션 — 87개 JSON을 도메인별 디렉터리로 복사.

소스: C:/Projects-2026/maintenance/books-final-processor/data/output/text/
대상: data/raw/{도메인-하이픈}/
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(
    "C:/Projects-2026/maintenance/books-final-processor/data/output/text/"
)
CATALOG_PATH = PROJECT_ROOT / "books_catalog.yaml"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def _domain_to_dir(domain: str) -> str:
    """도메인 → 디렉터리명 (슬래시 → 하이픈)."""
    return domain.replace("/", "-")


def migrate():
    # 카탈로그 로드
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    books = catalog["books"]
    copied = 0
    skipped = 0
    errors = []

    for book in books:
        domain = book["domain"]
        json_file = book["json_file"]
        domain_dir = RAW_DIR / _domain_to_dir(domain)
        domain_dir.mkdir(parents=True, exist_ok=True)

        src = SOURCE_DIR / json_file
        dst = domain_dir / json_file

        if dst.exists():
            skipped += 1
            continue

        if not src.exists():
            errors.append(f"소스 없음: {json_file}")
            continue

        shutil.copy2(str(src), str(dst))
        copied += 1

    # 검증
    total_files = 0
    parse_errors = []
    for domain_dir in RAW_DIR.iterdir():
        if not domain_dir.is_dir():
            continue
        for jf in domain_dir.glob("*.json"):
            total_files += 1
            try:
                with open(jf, encoding="utf-8") as f:
                    json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                parse_errors.append(f"{jf.name}: {e}")

    print(f"마이그레이션 완료:")
    print(f"  복사: {copied}개")
    print(f"  스킵 (이미 존재): {skipped}개")
    print(f"  오류: {len(errors)}개")
    if errors:
        for e in errors:
            print(f"    - {e}")

    print(f"\n검증:")
    print(f"  data/raw/ 내 JSON 파일: {total_files}개")
    print(f"  JSON 파싱 오류: {len(parse_errors)}개")
    if parse_errors:
        for e in parse_errors:
            print(f"    - {e}")

    # 디렉터리 목록
    dirs = sorted(d.name for d in RAW_DIR.iterdir() if d.is_dir())
    print(f"  디렉터리: {dirs}")


if __name__ == "__main__":
    migrate()
