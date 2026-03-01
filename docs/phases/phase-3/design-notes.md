# Phase 3: 87권 확장 + 그래프 레이어 — Design Notes
> Last Updated: 2026-03-01

## Stage H: 87권 마이그레이션 + 배치

### 설계 대안 (Alternatives Considered)

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| 1 | 7개 도메인 세분화 (인문,사회,역사,경제,과학,기술,경영) | masterplan 원안과 일치 | CSV Topic 기반 자동 분류 부정확, 수동 매핑 비용 | **4개 카테고리 그대로 사용** |
| 2 | 원본 경로 직접 참조 (복사 안 함) | 디스크 절약 | standalone 불가, 외부 프로젝트 의존 | **프로젝트 내부로 복사** |
| 3 | DB에서 직접 text 읽기 (books-final-processor DB) | 추가 가공 불필요 | DB 스키마 다름, 의존성 증가 | **text.json 파일 복사** |

### books-final-processor → 현재 프로젝트 데이터 흐름

```
books-final-processor (소스)
├── docs/100권 노션 원본_수정.csv      ──→  build_catalog.py  ──→  books_catalog.yaml
└── data/output/text/*_text.json       ──→  migrate_data.py   ──→  data/raw/{domain}/

현재 프로젝트 (대상)
├── books_catalog.yaml                 ──→  batch_ingest.py   ──→  knowledge.db + chroma/
└── data/raw/{domain}/*_text.json      ──→  ingest_book()     ──→  raw_spans → KUs
```

### text.json 파일명 패턴

books-final-processor의 text.json 파일명:
```
{6자리_hash}_{제목_공백제거}_text.json
```

CSV 제목과 파일명 매칭 시 공백 정규화 필요:
- CSV: "경제학자의 생각법" → 파일: "경제학자의_생각법"
- 87/87 전부 매칭 확인됨 (공백 정규화 포함)

### domain_short 하드코딩 문제

**현재 코드** (`ku_extractor.py:154`):
```python
domain_short = "econ"  # 경제 → econ
```

**문제:** 다른 도메인 책을 처리하면 모든 KU ID가 `ku-econ-*`으로 생성됨.

**수정:**
```python
DOMAIN_SHORT_MAP = {
    "역사/사회": "hist",
    "경제/경영": "econ",
    "인문/자기계발": "humn",
    "과학/기술": "sci",
    "경제": "econ",   # 레거시
}
domain_short = DOMAIN_SHORT_MAP.get(domain, domain[:4].lower())
```

### 기존 데이터 도메인 마이그레이션

기존 DB에 `domain="경제"`로 저장된 데이터 → `"경제/경영"`으로 통일:

```sql
UPDATE books SET domain='경제/경영' WHERE id='econ-thinking-001';
UPDATE knowledge_units SET domain='경제/경영' WHERE book_id='econ-thinking-001';
```

기존 `vault/domains/경제/` → 삭제 후 `vault/domains/경제-경영/`으로 재렌더링.

### 배치 처리 안전장치

1. **멱등성**: `INSERT OR IGNORE` → 같은 책 재실행 안전
2. **체크포인트**: `logs/batch_progress.json` → 북 단위 상태 추적
3. **에러 격리**: `try/except` → 1권 실패 시 다음 권 계속
4. **재시작**: `--from-book` 옵션 → 중간부터 재시작
5. **Rate limit**: `delay_between_spans=0.5`, `delay_between_books=2.0`

---

## 디버깅 이력 (Debug History)

| Bug # | Module | Issue | Fix | File |
|-------|--------|-------|-----|------|
| - | - | Phase 3 시작 전 | - | - |

---

## 열린 질문 (Open Questions)

- [ ] Stage I edge 생성 시 within-book edge를 먼저 만들 것인가, cross-domain부터 만들 것인가? — within-book 우선 (같은 책 내 관계가 더 신뢰도 높음)
- [ ] 87권 배치 실행 시간 추정 — 1권당 ~3-5분 × 86권 ≈ 4-7시간
- [ ] ChromaDB 75,000+ embedding 성능 — 벤치마크 필요 (Phase 1에서 997건은 즉시 응답)
- [ ] Vault 75,000+ 파일 시 Obsidian 성능 — 대규모 vault 테스트 필요

---

## 교훈 (Lessons Learned)

- books-final-processor의 text.json 형식이 현재 파이프라인과 100% 호환 → PDF 재파싱 불필요
- CSV-JSON 매칭 시 공백 정규화가 핵심 (87/87 전부 매칭 가능)
- 기존 DB의 INSERT OR IGNORE 패턴 덕분에 배치 재실행이 안전

---

## Modified Files Summary

```
수정:
├── src/ingest/ku_extractor.py    — DOMAIN_SHORT_MAP 추가, domain_short 파라미터화
├── src/vault/renderer.py         — _domain_to_dir() 헬퍼, 도메인 경로 수정
└── config.yaml                   — books 제거, catalog/batch 섹션 추가

신규:
├── books_catalog.yaml            — 87권 메타데이터 카탈로그
├── scripts/build_catalog.py      — 카탈로그 생성 스크립트
├── scripts/migrate_data.py       — 데이터 마이그레이션 스크립트
├── scripts/batch_ingest.py       — 배치 처리 스크립트
├── src/graph/edge_builder.py     — edge 생성 (Stage I)
├── src/graph/traversal.py        — 그래프 탐색 (Stage I)
├── src/generation/idea.py        — 아이디어 생성 (Stage J)
└── src/search/hybrid.py          — 복합 검색 (Stage J)
```
