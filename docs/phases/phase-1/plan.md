# Phase 1: 데이터 파이프라인 (Stage A~D)
> Last Updated: 2026-02-27
> Status: In Progress

## 1. Summary (개요)

**목적:** 경제학자의 생각법 1권의 원본 텍스트를 구조화된 Knowledge Unit(KU)으로 변환하는 데이터 파이프라인을 완성한다.

**범위:**
- L0 Raw: 기존 JSON → raw_spans 변환 + DB 저장
- L1 KU: raw_spans → KU 추출 (LLM) + 임베딩 (ChromaDB)
- 프로젝트 기반 구조: pyproject.toml, src/, config.yaml

**예상 산출물:**
- 소스 코드 5개 모듈 (db/models, db/vectors, ingest/pdf_parser, ingest/ku_extractor, config)
- SQLite DB (5테이블 DDL, 3테이블 활성 사용: books, raw_spans, knowledge_units)
- ChromaDB ku_embeddings 컬렉션
- 100-200 KU (경제학자의 생각법)

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

---

## 3. Target State (목표 상태)

Phase 1 완료 후:
- raw_spans 전건 DB 저장 (건수 검증)
- KU 100+ 추출, ChromaDB 임베딩 완료
- D.5 정량 기준 통과:
  - claim 존재율 > 80% (샘플 20페이지)
  - LLM JSON 파싱 성공률 > 95%
  - 최대 2세션 이내 수렴

---

## 4. Implementation Stages

### Stage A: 프로젝트 초기화 (S) — 5 Task

**목표:** 실행 가능한 Python 프로젝트 골격 구성

- `pyproject.toml` — 의존성 정의 (pymupdf, chromadb, openai, anthropic, pydantic, typer, pyyaml, rich)
- `src/` 디렉터리 — 전체 모듈 구조 + `__init__.py`
- `data/`, `vault/` 디렉터리 — 데이터 및 출력 경로
- `config.yaml` — API 키 참조, 모델 선택, 경로, 청크 크기 등 설정
- 의존성 설치 확인 (`pip install -e .`)

**의존성:** 없음 (첫 Stage)

### Stage B: DB 스키마 (M) — 4 Task

**목표:** SQLite 5테이블 DDL + CRUD 헬퍼 + ChromaDB 래퍼

- SQLite DDL — books, raw_spans, knowledge_units, edges, generations (edges는 DDL만)
- `src/db/models.py` — 테이블 생성, CRUD 함수 (insert/select/update/delete)
- `src/db/vectors.py` — ChromaDB ku_embeddings 컬렉션 초기화, add/query/delete
- DB 초기화 스크립트 — `data/knowledge.db` 자동 생성

**의존성:** Stage A (디렉터리 구조)

### Stage C: JSON 파싱 (M) — 4 Task

**목표:** 기존 JSON → raw_spans 변환 + DB 저장

- 기존 JSON 구조 분석 — text.json의 chapters[].pages[] 매핑
- `src/ingest/pdf_parser.py` — JSON 로드 → books 레코드 생성 → pages를 raw_spans로 변환
- raw_spans ID 생성: `{book_id}-ch{nn}-p{nnn}-s{nnn}` 패턴
- 페이지 단위 청킹 확정 (C-1): 1페이지 = 1 raw_span, 빈 페이지 필터 (len(text.strip()) < 10 → 제외)
- DB 저장 + 건수 검증
- PDF 직접 파싱 보조 경로 (PyMuPDF) — 기존 JSON이 없는 책 대비

**의존성:** Stage B (DB 스키마)

### Stage D: KU 추출 (L) — 5 Task

**목표:** raw_spans → KU 추출 + 임베딩 + 품질 검증

- KU 추출 프롬프트 설계 — masterplan §5 프롬프트 기반, 반복 최적화
- `src/ingest/ku_extractor.py` — raw_spans 청크 → LLM API (GPT-4o mini) → KU JSON 파싱
  - D.2 fallback: (1) JSON repair → (2) 1회 재시도 → (3) skip + 로그 기록
- KU DB 저장 — knowledge_units 테이블, source_spans 매핑
- 임베딩 생성 — claim + evidence_summary → text-embedding-3-small → ChromaDB 저장
- 프롬프트 최적화 — 정량 종료 기준:
  - 샘플 20페이지 → claim 존재율 > 80%
  - JSON 파싱 성공률 > 95%
  - 최대 2세션 이내 수렴
  - 미달 시: 현재 프롬프트 확정, M0으로 전체 실행 → M1에서 수동 보정
- 예상 산출: 100-200 KU (354페이지 본문, 페이지당 0.3-0.6 KU)

**의존성:** Stage B (DB), Stage C (raw_spans 데이터)

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
| C.1 | 기존 JSON 구조 분석 + 페이지 단위 확정 | C | S | - | 빈 페이지 필터: len < 10 |
| C.2 | JSON → raw_spans 변환 | C | M | B.2, C.1 | src/ingest/pdf_parser.py |
| C.3 | raw_spans DB 저장 + 검증 | C | S | C.2 | 건수 확인 |
| C.4 | PDF 직접 파싱 보조 경로 | C | M | B.2 | PyMuPDF, 우선순위 낮음 |
| D.1 | KU 추출 프롬프트 설계 | D | M | - | masterplan §5 기반 |
| D.2 | ku_extractor.py 구현 | D | L | B.2, D.1 | 3단계 fallback 포함 |
| D.3 | KU DB 저장 + source_spans | D | S | D.2 | knowledge_units 테이블 |
| D.4 | 임베딩 생성 + ChromaDB | D | M | B.3, D.3 | text-embedding-3-small |
| D.5 | 프롬프트 최적화 | D | L | D.2 | 정량 종료 기준 적용 |

**합계:** 18개 Task (S: 8, M: 7, L: 3)

---

## 6. Risks & Mitigation

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| KU 추출 프롬프트 품질 저조 | 전체 시스템 품질 하락 | 중 | D.5 정량 기준으로 수렴 판단, 미달 시 M0 확정 후 M1 보정 |
| 기존 JSON 텍스트 품질 (OCR 오류) | raw_spans 노이즈 | 중 | C.1에서 샘플 검수, 심각 시 PDF 직접 파싱(C.4)으로 전환 |
| GPT-4o mini KU 추출 한계 | claim/evidence 분리 부정확 | 중-저 | GPT-4o로 업그레이드 (비용 $2-5 → $10-20) |
| LLM JSON 파싱 실패 | 추출 실패 누적 | 중 | D.2 3단계 fallback (repair → 재시도 → skip+로그) |
| ChromaDB 임베딩 품질 | 검색 정확도 저하 | 저 | text-embedding-3-small → large 전환 가능 |
| API 비용 초과 | 예산 $3-10 초과 | 저 | GPT-4o mini 우선, 배치 크기 조절 |

---

## 7. Dependencies

### 내부 의존성

```
Stage A ──→ Stage B ──→ Stage C ──→ Stage D
                └──→ Stage D (B.2, B.3)
```

- Stage B → C, D: DB 스키마 필요
- Stage C → D: raw_spans 데이터 필요

### 외부 의존성

| 의존성 | 용도 | Phase 1 필수 |
|--------|------|-------------|
| OpenAI API (text-embedding-3-small) | 임베딩 | Yes |
| OpenAI API (GPT-4o mini) | KU 추출 | Yes |
| pymupdf | PDF 파싱 보조 경로 | No (C.4) |
| chromadb | 벡터 DB | Yes |
| pydantic | 데이터 검증 | Yes |
| pyyaml | config 파싱 | Yes |

### Phase 2 연결

Phase 1 산출물 → Phase 2 입력:
- `data/knowledge.db` (books, raw_spans, knowledge_units)
- `data/chroma/` (ku_embeddings)
- `src/db/`, `src/ingest/` 모듈
