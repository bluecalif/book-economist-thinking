# Phase 1: 1권 MVP — Tasks
> Last Updated: 2026-02-27

## Progress: 0/29 Tasks (0%)

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
  - `insert_generation()`, `get_generation()`, `list_generations()`
- [ ] B.3 ChromaDB 래퍼 (`src/db/vectors.py`)
  - `init_chroma()` — 컬렉션 생성
  - `add_embeddings()` — KU 임베딩 추가
  - `query_similar()` — 유사도 검색
  - `delete_embeddings()` — 삭제
- [ ] B.4 DB 초기화 스크립트
  - `data/knowledge.db` 자동 생성, 테이블 존재 확인

---

### Stage C: PDF 파싱 (M) — 0/4

- [ ] C.1 기존 JSON 구조 분석 (structure.json, text.json)
  - text.json: chapters[].pages[].{page_number, text}
  - structure.json: chapters[].{order_index, title, start_page, end_page}
  - 텍스트 품질 샘플 검수 (OCR 오류 수준 확인)
- [ ] C.2 JSON → raw_spans 변환 로직 (`src/ingest/pdf_parser.py`)
  - `parse_json_book()` — text.json 로드 → books + raw_spans 생성
  - 문단 분할 전략 결정 (design-notes 참조)
  - raw_span ID: `{book_id}-ch{nn}-p{nnn}-s{nnn}`
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
  - 에러 핸들링: JSON 파싱 실패, API 오류
- [ ] D.3 KU DB 저장 + source_spans 매핑
  - ku_id 자동 생성: `ku-econ-001-{seq:04d}`
  - source_spans: 사용된 raw_span ID 목록 (JSON array)
  - domain: "경제", book_id: "econ-thinking-001"
- [ ] D.4 임베딩 생성 + ChromaDB 저장
  - 임베딩 텍스트: `claim + " " + evidence_summary`
  - 모델: text-embedding-3-small
  - metadata: ku_id, domain, book_id, subdomain
- [ ] D.5 프롬프트 최적화 (품질 검증 반복)
  - 품질 기준: claim 명확성, evidence 정확성, 중복 KU 비율
  - 반복: 프롬프트 수정 → 샘플 실행 → 평가 → 수정
  - 품질 안정 후 전체 실행 (354페이지)

---

### Stage E: 의미 검색 (S) — 0/3

- [ ] E.1 `src/search/vector.py` 구현
  - `search_kus()` — 쿼리 텍스트 → 임베딩 → ChromaDB 검색 → KU 반환
  - top_k 파라미터 (기본 10)
  - similarity threshold (기본 0.5)
- [ ] E.2 검색 결과 포매팅
  - 출력: claim, domain, confidence, similarity score
  - Rich 포매팅 (테이블 형태)
- [ ] E.3 도메인 필터링
  - ChromaDB metadata where 조건 (domain 필터)
  - Phase 1은 단일 도메인이지만 구조 준비

---

### Stage F: 콘텐츠 생성 (M) — 0/4

- [ ] F.1 `src/generation/content.py` 파이프라인
  - `generate_content()` — 토픽 → KU 검색 → 컨텍스트 조합 → LLM → 출력
  - 입력: topic (str), format (str), ku_ids (optional list)
  - KU 컨텍스트: claim + evidence_summary + counter_summary
- [ ] F.2 프롬프트 템플릿 3종
  - `blog.txt` — 1,500-3,000자 블로그 포스트
  - `summary.txt` — 300-500자 개념 요약
  - `thread.txt` — 5-10개 항목 소셜미디어 스레드
  - 변수: {topic}, {ku_context}, {format_instructions}
- [ ] F.3 출처 KU ID 첨부 로직
  - 생성 결과 끝에 "출처: ku-econ-001-xxxx, ..." 자동 첨부
  - 마크다운 출력 시 KU 링크 포함
- [ ] F.4 generations 테이블 기록
  - mode: "content", format, prompt, output, ku_ids (JSON), rating (NULL)

---

### Stage G: CLI + 통합 (L) — 0/4

- [ ] G.1 `src/cli.py` — ingest, search, generate 명령어
  - `ks ingest <path>` — JSON/PDF 자동 감지 → 전체 파이프라인
  - `ks search <query>` — 벡터 검색 + Rich 출력
  - `ks generate content --topic <t> --format <f>` — 콘텐츠 생성
  - `ks stats` — 기본 통계 (KU 수, 도메인 분포)
- [ ] G.2 `src/vault/renderer.py` — KU 마크다운 렌더링
  - YAML frontmatter: id, book, domain, subdomain, confidence, maturity, tags, created
  - 본문: Claim, Evidence, Counter, Connections
  - 출력 경로: `vault/domains/{domain}/{ku_id}.md`
- [ ] G.3 통합 테스트 (전체 파이프라인)
  - ingest → search → generate end-to-end
  - DB 정합성 확인: raw_spans ↔ knowledge_units ↔ ChromaDB
- [ ] G.4 완료 기준 4항목 검증
  - [ ] `ks ingest` → KU 추출 + DB 저장 + 마크다운 생성
  - [ ] `ks search "매몰비용"` → 관련 KU 반환
  - [ ] `ks generate content --topic "매몰비용" --format blog` → 블로그 초안
  - [ ] 생성 콘텐츠 품질 평가 (경미한 편집으로 게시 가능)
