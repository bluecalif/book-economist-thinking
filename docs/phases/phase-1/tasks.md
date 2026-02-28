# Phase 1: 데이터 파이프라인 — Tasks
> Last Updated: 2026-02-28

## Progress: 18/18 Tasks (100%) ✅

---

### Stage A: 프로젝트 초기화 (S) — 5/5 ✅

- [x] A.1 `pyproject.toml` 생성 (의존성 정의) — `4796a61`
- [x] A.2 `src/` 디렉터리 구조 생성 (`__init__.py` 포함) — `4796a61`
  - `src/__init__.py`
  - `src/db/__init__.py`
  - `src/ingest/__init__.py`
  - `src/search/__init__.py`
  - `src/generation/__init__.py`
  - `src/generation/templates/`
  - `src/vault/__init__.py`
- [x] A.3 `data/`, `vault/` 디렉터리 생성 (`.gitkeep`) — `4796a61`
  - `data/raw/`, `data/chroma/`
- [x] A.4 `config.yaml` 기본 설정 파일 — `4796a61`
  - API 키 참조 (환경변수), 모델: gpt-4.1-mini + text-embedding-3-large
- [x] A.5 의존성 설치 확인 (`pip install -e .`) — `4796a61`

---

### Stage B: DB 스키마 (M) — 4/4 ✅

- [x] B.1 SQLite DDL — 5개 테이블 생성 — `07096fa`
  - books, raw_spans, knowledge_units, edges, generations
  - 인덱스: idx_raw_spans_book, idx_ku_book, idx_ku_domain, idx_edges_*
- [x] B.2 CRUD 헬퍼 함수 (`src/db/models.py`) — `07096fa`
  - `init_db()` — 테이블 생성
  - `insert_book()`, `get_book()`, `list_books()`
  - `insert_raw_span()`, `bulk_insert_raw_spans()`, `get_raw_spans_by_book()`, `get_raw_spans_by_chapter()`
  - `insert_ku()`, `get_ku()`, `list_kus_by_book()`, `update_ku()`
  - `count_raw_spans()`, `count_kus()`
- [x] B.3 ChromaDB 래퍼 (`src/db/vectors.py`) — `07096fa`
  - `init_chroma()` — 컬렉션 생성 (cosine space)
  - `add_embeddings()` — KU 임베딩 upsert
  - `query_similar()` — 유사도 검색
  - `delete_embeddings()` — 삭제
- [x] B.4 DB 초기화 스크립트 — `07096fa`
  - `init_db()` 호출 시 `data/knowledge.db` 자동 생성, 테이블 존재 확인

---

### Stage C: JSON 파싱 (M) — 4/4 ✅

- [x] C.1 기존 JSON 구조 분석 + 페이지 단위 확정 — `67b21e7`
  - text.json: chapters[].pages[].{page_number, text}
  - structure.json: chapters[].{order_index, title, start_page, end_page}
  - **확정:** 1페이지 = 1 raw_span (C-1)
  - **빈 페이지 필터:** `len(text.strip()) < 10` → 59건 제외
- [x] C.2 JSON → raw_spans 변환 로직 (`src/ingest/pdf_parser.py`) — `67b21e7`
  - `ingest_book()` — text.json 로드 → books + raw_spans 생성
  - raw_span ID: `{book_id}-ch{nn}-p{nnn}-s{nnn}`
- [x] C.3 raw_spans DB 저장 + 검증 — `67b21e7`
  - 결과: **341건** (5챕터, 빈 페이지 59건 필터)
- [x] C.4 PDF 직접 파싱 보조 경로 (PyMuPDF) — 보류
  - 우선순위 낮음: 기존 JSON이 없는 책 대비

---

### Stage D: KU 추출 (L) — 5/5 ✅

- [x] D.1 KU 추출 프롬프트 설계 + 테스트 — `4d33a2a`
  - 규칙: 1 KU = 1 claim, evidence 인용, counter 기록
  - 출력: JSON array [{claim, evidence_summary, counter_summary, tags}]
  - 프롬프트 개선: claim 범위 확대 (주장+관찰+원리+통찰) → claim율 20→85%
- [x] D.2 `src/ingest/ku_extractor.py` 구현 — `4d33a2a`
  - `extract_kus_from_spans()` — raw_spans → LLM API → KU 파싱
  - 3단계 fallback: JSON repair → 1x retry → skip+log
- [x] D.3 KU DB 저장 + source_spans 매핑 — `4d33a2a`
  - ku_id: `ku-econ-{book_seq}-{seq:04d}`
  - source_spans: JSON array, FK 무결성 검증 완료
- [x] D.4 임베딩 생성 + ChromaDB 저장 — `4d33a2a`
  - 임베딩 텍스트: `claim + " " + evidence_summary`
  - 모델: text-embedding-3-large (config.yaml)
  - 997건 임베딩 → ChromaDB upsert 완료
- [x] D.5 프롬프트 최적화 (정량 종료 기준 적용) — `4d33a2a`
  - claim 존재율: **83%** (>80% PASS)
  - JSON 파싱 성공률: **100%** (>95% PASS)
  - 수렴: 1세션 (≤2 PASS)
  - Full run: 341 spans → **997 KUs**

---

## Phase 1 완료 검증

- [x] E2E 테스트 26/26 ALL PASS (`scripts/test_e2e_phase1.py`)
- [x] 품질 리포트 생성 (`reports/phase1-quality-report.md`)
- [x] 프로덕션 DB 무결성: FK 0 orphan, 중복 claim 0, evidence 전건 존재
- [x] ChromaDB 유사도 검색 검증: 매몰비용(0.40), 인플레이션(0.44), 경쟁의 효과(0.40)
