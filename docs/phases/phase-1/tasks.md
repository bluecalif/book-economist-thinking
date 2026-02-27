# Phase 1: 데이터 파이프라인 — Tasks
> Last Updated: 2026-02-27

## Progress: 0/18 Tasks (0%)

---

### Stage A: 프로젝트 초기화 (S) — 0/5

- [ ] A.1 `pyproject.toml` 생성 (의존성 정의)
- [ ] A.2 `src/` 디렉터리 구조 생성 (`__init__.py` 포함)
  - `src/__init__.py`
  - `src/db/__init__.py`
  - `src/ingest/__init__.py`
  - `src/search/__init__.py`
  - `src/generation/__init__.py`
  - `src/generation/templates/`
  - `src/vault/__init__.py`
- [ ] A.3 `data/`, `vault/` 디렉터리 생성 (`.gitkeep`)
  - `data/raw/`, `data/chroma/`
- [ ] A.4 `config.yaml` 기본 설정 파일
  - API 키 참조 (환경변수), 모델 선택, DB 경로, 청크 크기
- [ ] A.5 의존성 설치 확인 (`pip install -e .`)

---

### Stage B: DB 스키마 (M) — 0/4

- [ ] B.1 SQLite DDL — 5개 테이블 생성
  - books, raw_spans, knowledge_units, edges, generations
  - 인덱스: idx_raw_spans_book, idx_ku_book, idx_ku_domain, idx_edges_*
- [ ] B.2 CRUD 헬퍼 함수 (`src/db/models.py`)
  - `init_db()` — 테이블 생성
  - `insert_book()`, `get_book()`, `list_books()`
  - `insert_raw_span()`, `get_raw_spans_by_book()`, `get_raw_spans_by_chapter()`
  - `insert_ku()`, `get_ku()`, `list_kus_by_book()`, `update_ku()`
- [ ] B.3 ChromaDB 래퍼 (`src/db/vectors.py`)
  - `init_chroma()` — 컬렉션 생성
  - `add_embeddings()` — KU 임베딩 추가
  - `query_similar()` — 유사도 검색
  - `delete_embeddings()` — 삭제
- [ ] B.4 DB 초기화 스크립트
  - `data/knowledge.db` 자동 생성, 테이블 존재 확인

---

### Stage C: JSON 파싱 (M) — 0/4

- [ ] C.1 기존 JSON 구조 분석 + 페이지 단위 확정
  - text.json: chapters[].pages[].{page_number, text}
  - structure.json: chapters[].{order_index, title, start_page, end_page}
  - 텍스트 품질 샘플 검수 (OCR 오류 수준 확인)
  - **확정:** 1페이지 = 1 raw_span (C-1)
  - **빈 페이지 필터:** `len(text.strip()) < 10` → 제외
  - **문단 분리는 D 단계 LLM에 위임** (근거: OCR 줄바꿈이 문단 경계를 보장하지 않음)
- [ ] C.2 JSON → raw_spans 변환 로직 (`src/ingest/pdf_parser.py`)
  - `parse_json_book()` — text.json 로드 → books + raw_spans 생성
  - raw_span ID: `{book_id}-ch{nn}-p{nnn}-s{nnn}`
  - 페이지 단위이므로 s는 항상 001
- [ ] C.3 raw_spans DB 저장 + 검증
  - 건수 확인: 5챕터 × ~354페이지 = 예상 스팬 수
  - 샘플 조회로 텍스트 정합성 확인
- [ ] C.4 PDF 직접 파싱 보조 경로 (PyMuPDF)
  - `parse_pdf_book()` — PDF → 페이지 텍스트 추출
  - 우선순위 낮음: 기존 JSON이 없는 책 대비

---

### Stage D: KU 추출 (L) — 0/5

- [ ] D.1 KU 추출 프롬프트 설계 + 테스트
  - masterplan §5 프롬프트 기반
  - 규칙: 1 KU = 1 claim, evidence 인용, counter 기록
  - 출력: JSON array [{claim, evidence_summary, counter_summary, tags}]
  - 소수 샘플(3-5 페이지)로 반복 테스트
- [ ] D.2 `src/ingest/ku_extractor.py` 구현
  - `extract_kus_from_spans()` — raw_spans 청크 → LLM API → KU 파싱
  - 배치 처리: rate limit 관리, 재시도 로직
  - **3단계 fallback:**
    1. JSON repair (trailing comma, 따옴표 수정)
    2. 동일 프롬프트로 1회 재시도
    3. skip + 로그 기록 → M1에서 수동 처리
- [ ] D.3 KU DB 저장 + source_spans 매핑
  - ku_id 자동 생성: `ku-econ-001-{seq:04d}`
  - source_spans: 사용된 raw_span ID 목록 (JSON array)
  - domain: "경제", book_id: "econ-thinking-001"
- [ ] D.4 임베딩 생성 + ChromaDB 저장
  - 임베딩 텍스트: `claim + " " + evidence_summary`
  - 모델: text-embedding-3-small
  - metadata: ku_id, domain, book_id, subdomain
- [ ] D.5 프롬프트 최적화 (정량 종료 기준 적용)
  - **종료 조건 (모두 충족 시):**
    - 샘플 20페이지 추출 → claim 존재율 > 80%
    - LLM JSON 파싱 성공률 > 95%
    - 최대 2세션 이내 수렴
  - **미달 시:**
    - 현재 프롬프트로 확정, M0으로 전체 실행
    - M1 단계에서 수동 보정
  - 품질 안정 후 전체 실행 (354페이지)
