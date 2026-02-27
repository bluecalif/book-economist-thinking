# Phase 1: 1권 MVP
> Last Updated: 2026-02-27
> Status: In Progress

## 1. Summary (개요)

**목적:** 경제학자의 생각법 1권으로 전체 파이프라인(L0 Raw → L1 KU → L3 Generation)을 완성하고, 생성 기능의 실제 가치를 검증한다.

**범위:**
- L0 Raw: 기존 JSON → raw_spans 변환 + DB 저장
- L1 KU: raw_spans → KU 추출 (LLM) + 임베딩 (ChromaDB)
- L3 Generation: 토픽 기반 콘텐츠 생성 (blog, summary, thread)
- CLI: `ks ingest`, `ks search`, `ks generate content`
- Vault: KU 마크다운 렌더링 (Obsidian 호환)

**예상 산출물:**
- 소스 코드 8개 모듈 + 템플릿 3종
- SQLite DB (5테이블 DDL, 3테이블 활성 사용)
- ChromaDB ku_embeddings 컬렉션
- 100-200 KU (경제학자의 생각법)
- Obsidian 호환 마크다운 vault

---

## 2. Current State (현재 상태)

- 프로젝트 git 저장소 초기화 완료
- masterplan v2.0 확정, project-overall 3파일 생성 완료
- 기존 파싱 데이터 3종 확보:
  - `55bbe4_경제학자의_생각법_structure.json` (1.1K) — 5챕터 구조 메타데이터
  - `55bbe4_경제학자의_생각법_text.json` (391K) — 챕터/페이지별 텍스트 (400페이지)
  - `55bbe48ee53666b54ce523d0ba4166b7.json` (2.2M) — PDF 파싱 원본 (1,986 elements)
- 소스 코드: 없음 (Stage A부터 시작)
- DB: 없음

### 기존 JSON 데이터 구조

**text.json (주 경로):**
```
book_id: 199, book_title: "경제학자의 생각법"
metadata: { total_pages: 400, main_start_page: 17, main_end_page: 370, chapter_count: 5 }
text_content.chapters[]: { order_index, chapter_number, title, start_page, end_page, pages[] }
pages[]: { page_number, text }
```

**챕터 구성:**
| # | 제목 | 페이지 | 페이지 수 |
|---|------|--------|----------|
| 0 | 일상 — 피가 되고 살이 되는 경제학 사용법 | 17-90 | 74 |
| 1 | 경쟁 — 피할 수 없다면 이겨라 | 91-216 | 126 |
| 2 | 경제 — 경제는 도대체 언제 좋아지는 걸까 | 217-262 | 46 |
| 3 | 오류 — 우리가 경제학에 대해 오해하고 있는 것들 | 263-304 | 42 |
| 4 | 경제와 정치 — 경제학자의 눈으로 세상을 읽는 법 | 305-370 | 66 |

**structure.json:** 챕터 경계 메타데이터 (text.json과 동일 정보, 경량)

**대형 JSON (2.2M):** PDF 파싱 원본. 1,986 elements (paragraph 905, footer 772, heading1 254, figure 52, table 2, list 1). HTML content + 좌표 정보. 보조 경로로 활용.

---

## 3. Target State (목표 상태)

Phase 1 완료 후:
- `ks ingest book.pdf` → KU 추출 + DB 저장 + 마크다운 생성
- `ks search "매몰비용"` → 관련 KU 반환 (claim, domain, confidence 표시)
- `ks generate content --topic "매몰비용" --format blog` → 블로그 초안 생성
- 생성된 콘텐츠가 실제 사용 가능한 품질 (경미한 편집으로 게시 가능)
- 100-200 KU가 DB + ChromaDB + Vault에 일관되게 저장
- 전체 파이프라인이 1권 단위로 재현 가능

---

## 4. Implementation Stages

### Stage A: 프로젝트 초기화 (S)

**목표:** 실행 가능한 Python 프로젝트 골격 구성

- `pyproject.toml` — 의존성 정의 (pymupdf, chromadb, openai, anthropic, pydantic, typer, pyyaml, rich)
- `src/` 디렉터리 — 전체 모듈 구조 + `__init__.py`
- `data/`, `vault/` 디렉터리 — 데이터 및 출력 경로
- `config.yaml` — API 키 참조, 모델 선택, 경로, 청크 크기 등 설정
- 의존성 설치 확인 (`pip install -e .`)

**의존성:** 없음 (첫 Stage)

### Stage B: DB 스키마 (M)

**목표:** SQLite 5테이블 DDL + CRUD 헬퍼 + ChromaDB 래퍼

- SQLite DDL — books, raw_spans, knowledge_units, edges, generations (edges는 DDL만)
- `src/db/models.py` — 테이블 생성, CRUD 함수 (insert/select/update/delete)
- `src/db/vectors.py` — ChromaDB ku_embeddings 컬렉션 초기화, add/query/delete
- DB 초기화 스크립트 — `data/knowledge.db` 자동 생성

**의존성:** Stage A (디렉터리 구조)

### Stage C: PDF 파싱 (M)

**목표:** 기존 JSON → raw_spans 변환 + DB 저장

- 기존 JSON 구조 분석 — text.json의 chapters[].pages[] 매핑
- `src/ingest/pdf_parser.py` — JSON 로드 → books 레코드 생성 → pages를 raw_spans로 변환
- raw_spans ID 생성: `{book_id}-ch{nn}-p{nnn}-s{nnn}` 패턴
- 페이지 텍스트 → 문단 분할 전략: 줄바꿈 기반 분리 또는 페이지 단위 유지 (design-notes에서 결정)
- DB 저장 + 건수 검증
- PDF 직접 파싱 보조 경로 (PyMuPDF) — 기존 JSON이 없는 책 대비

**의존성:** Stage B (DB 스키마)

### Stage D: KU 추출 (L)

**목표:** raw_spans → KU 추출 + 임베딩 + 품질 검증

- KU 추출 프롬프트 설계 — masterplan §5 프롬프트 기반, 반복 최적화
- `src/ingest/ku_extractor.py` — raw_spans 청크 → LLM API (GPT-4o mini) → KU JSON 파싱
- KU DB 저장 — knowledge_units 테이블, source_spans 매핑
- 임베딩 생성 — claim + evidence_summary → text-embedding-3-small → ChromaDB 저장
- 프롬프트 최적화 — 소수 샘플로 반복 테스트, 품질 안정 후 전체 실행
- 예상 산출: 100-200 KU (354페이지 본문, 페이지당 0.3-0.6 KU)

**의존성:** Stage B (DB), Stage C (raw_spans 데이터)

### Stage E: 의미 검색 (S)

**목표:** ChromaDB 벡터 검색 모듈

- `src/search/vector.py` — 쿼리 임베딩 → ChromaDB 유사도 검색 → KU 반환
- 검색 결과 포매팅 — claim, domain, confidence, similarity score 표시
- 도메인 필터링 — metadata 기반 (Phase 1은 단일 도메인이지만 구조 준비)

**의존성:** Stage D (임베딩 데이터)

### Stage F: 콘텐츠 생성 (M)

**목표:** 토픽 → KU 검색 → 프롬프트 → LLM → 콘텐츠 초안

- `src/generation/content.py` — 생성 파이프라인 (토픽 → 검색 → 컨텍스트 조합 → 생성)
- 프롬프트 템플릿 3종:
  - `blog` — 1,500-3,000자 블로그 포스트
  - `summary` — 300-500자 개념 요약
  - `thread` — 5-10개 항목 소셜미디어 스레드
- 출처 KU ID 필수 첨부 — 생성 결과에 사용된 KU ID 목록 기록
- generations 테이블 기록 — mode, format, prompt, output, ku_ids

**의존성:** Stage E (검색 모듈)

### Stage G: CLI + 통합 (L)

**목표:** CLI 진입점 + Vault 렌더러 + 전체 파이프라인 통합 테스트

- `src/cli.py` — Typer 기반 CLI
  - `ks ingest <path>` — PDF/JSON → raw_spans → KU → 임베딩 → Vault
  - `ks search <query>` — 벡터 검색 + 결과 출력
  - `ks generate content --topic <t> --format <f>` — 콘텐츠 생성
- `src/vault/renderer.py` — KU → Obsidian 호환 마크다운 (YAML frontmatter + claim/evidence/counter/connections)
- 통합 테스트 — 전체 파이프라인 end-to-end
- 완료 기준 4항목 검증 (masterplan §14)

**의존성:** Stage A-F 전체

---

## 5. Task Breakdown

| ID | Task | Stage | Size | 의존성 | 비고 |
|----|------|-------|------|--------|------|
| A.1 | pyproject.toml 생성 | A | S | - | 의존성 정의 |
| A.2 | src/ 디렉터리 구조 생성 | A | S | - | __init__.py 포함 |
| A.3 | data/, vault/ 디렉터리 생성 | A | S | - | .gitkeep |
| A.4 | config.yaml 기본 설정 | A | S | - | API 키 참조, 모델, 경로 |
| A.5 | 의존성 설치 확인 | A | S | A.1 | pip install -e . |
| B.1 | SQLite DDL (5테이블) | B | S | A.2 | edges는 DDL만 |
| B.2 | CRUD 헬퍼 함수 | B | M | B.1 | src/db/models.py |
| B.3 | ChromaDB 래퍼 | B | M | A.2 | src/db/vectors.py |
| B.4 | DB 초기화 스크립트 | B | S | B.1, B.3 | knowledge.db 자동 생성 |
| C.1 | 기존 JSON 구조 분석 | C | S | - | text.json, structure.json |
| C.2 | JSON → raw_spans 변환 | C | M | B.2, C.1 | src/ingest/pdf_parser.py |
| C.3 | raw_spans DB 저장 + 검증 | C | S | C.2 | 건수 확인 |
| C.4 | PDF 직접 파싱 보조 경로 | C | M | B.2 | PyMuPDF, 우선순위 낮음 |
| D.1 | KU 추출 프롬프트 설계 | D | M | - | masterplan §5 기반 |
| D.2 | ku_extractor.py 구현 | D | L | B.2, D.1 | LLM API 호출 |
| D.3 | KU DB 저장 + source_spans | D | S | D.2 | knowledge_units 테이블 |
| D.4 | 임베딩 생성 + ChromaDB | D | M | B.3, D.3 | text-embedding-3-small |
| D.5 | 프롬프트 최적화 | D | L | D.2 | 반복 테스트 |
| E.1 | vector.py 구현 | E | S | B.3 | ChromaDB 검색 |
| E.2 | 검색 결과 포매팅 | E | S | E.1 | claim, domain, confidence |
| E.3 | 도메인 필터링 | E | S | E.1 | metadata 기반 |
| F.1 | content.py 파이프라인 | F | M | E.1 | 토픽→검색→생성 |
| F.2 | 프롬프트 템플릿 3종 | F | M | F.1 | blog, summary, thread |
| F.3 | 출처 KU ID 첨부 | F | S | F.1 | 생성 결과에 KU ID 기록 |
| F.4 | generations 테이블 기록 | F | S | B.2, F.1 | mode, format, output, ku_ids |
| G.1 | cli.py (ingest, search, generate) | G | M | C.2, E.1, F.1 | Typer CLI |
| G.2 | vault/renderer.py | G | M | D.3 | KU → 마크다운 |
| G.3 | 통합 테스트 | G | L | G.1, G.2 | end-to-end |
| G.4 | 완료 기준 검증 | G | S | G.3 | masterplan §14 4항목 |

**합계:** 29개 Task (S: 14, M: 11, L: 4)

---

## 6. Risks & Mitigation

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| KU 추출 프롬프트 품질 저조 | 전체 시스템 품질 하락 | 중 | Stage D에서 소수 샘플 반복 테스트, 품질 안정 후 전체 실행 |
| 기존 JSON 텍스트 품질 (OCR 오류) | raw_spans 노이즈 | 중 | C.1에서 샘플 검수, 심각 시 PDF 직접 파싱(C.4)으로 전환 |
| GPT-4o mini KU 추출 한계 | claim/evidence 분리 부정확 | 중-저 | GPT-4o로 업그레이드 (비용 $2-5 → $10-20) |
| 페이지 단위 청크의 KU 경계 문제 | 페이지 걸침 KU 누락 | 중 | 인접 페이지 오버랩 전략 (design-notes에서 상세) |
| ChromaDB 임베딩 품질 | 검색 정확도 저하 | 저 | text-embedding-3-small → large 전환 가능 |
| API 비용 초과 | 예산 $3-10 초과 | 저 | GPT-4o mini 우선, 배치 크기 조절 |

---

## 7. Dependencies

### 내부 의존성

```
Stage A ──→ Stage B ──→ Stage C ──→ Stage D ──→ Stage E ──→ Stage F ──→ Stage G
                  └──→ Stage C                          └──→ Stage G
                  └──→ Stage D (B.2, B.3)
```

- Stage B → C, D: DB 스키마 필요
- Stage C → D: raw_spans 데이터 필요
- Stage D → E: 임베딩 데이터 필요
- Stage E → F: 검색 모듈 필요
- Stage A-F → G: 전체 모듈 통합

### 외부 의존성

| 의존성 | 용도 | Phase 1 필수 |
|--------|------|-------------|
| OpenAI API (text-embedding-3-small) | 임베딩 | Yes |
| OpenAI API (GPT-4o mini) | KU 추출 | Yes |
| Anthropic API (Claude) | 콘텐츠 생성 | Yes |
| pymupdf | PDF 파싱 보조 경로 | No (C.4) |
| chromadb | 벡터 DB | Yes |
| typer | CLI 프레임워크 | Yes |
| pydantic | 데이터 검증 | Yes |
| pyyaml | config 파싱 | Yes |
| rich | CLI 출력 포매팅 | Optional |
