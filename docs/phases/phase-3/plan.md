# Phase 3: 87권 확장 + 그래프 레이어 (Stage H~J)
> Last Updated: 2026-03-01
> Status: Planning
> **전제:** Phase 2 완료 ✅ (1권 파이프라인 + 검색 + 생성 + CLI + Vault)

## 1. Summary (개요)

**목적:** 1권 파이프라인을 87권으로 확장하고, KU 간 관계 그래프(L2)를 구축하여 cross-domain 지식 연결 및 아이디어 생성을 가능하게 한다.

**범위:**
- Stage H: 87권 데이터 마이그레이션 + 배치 인제스트 + KU 추출
- Stage I: L2 Graph Layer — edge 자동 생성 + 그래프 탐색
- Stage J: L3 Generation 확장 — 아이디어 생성 + 하이브리드 검색

**예상 산출물:**
- 87권 text.json 데이터 (`data/raw/`)
- 87권 book catalog (`books_catalog.yaml`)
- 배치 처리 스크립트 (`scripts/batch_ingest.py`)
- ~10,000-15,000 KUs + ChromaDB embeddings
- 수천 개 edges (within-book + cross-domain)
- `src/graph/` 모듈 (edge_builder, traversal)
- `src/generation/idea.py` + `src/search/hybrid.py`
- 4개 도메인 Vault 구조

---

## 2. Current State (Phase 2 산출물)

| 항목 | 값 |
|------|---|
| Books | 1 (경제학자의 생각법) |
| Raw Spans | 341 |
| Knowledge Units | 997 |
| ChromaDB Embeddings | 997 |
| Generations | 2 |
| Vault Files | 997 (`vault/domains/경제/`) |
| Edges | 0 (테이블만 존재) |

**사용 가능한 외부 데이터:**
- `C:\Projects-2026\maintenance\books-final-processor\data\output\text\` — 87권 text.json (현재 프로젝트 ingest 형식과 100% 호환)
- `C:\Projects-2026\maintenance\books-final-processor\docs\100권 노션 원본_수정.csv` — 87권 메타데이터 (제목, 저자, 분야, Topic, 요약)

---

## 3. Target State (목표 상태)

Phase 3 완료 후:
- `ks stats` → books=87, spans≥25,000, kus≥75,000, chroma≥75,000
- `ks search "기술 혁신과 노동시장"` → 다수 도메인에서 KU 반환
- `ks explore ku-id --depth 2` → 연결된 KU 탐색
- `ks generate idea --mode business --domains 경제/경영,과학/기술` → 아이디어 후보 생성
- `vault/domains/` 하위 4개 도메인 디렉터리 구조
- Cross-domain 연결에서 실제 유용한 통찰 산출

---

## 4. Implementation Stages

### Stage H: 87권 데이터 마이그레이션 + 배치 인제스트 (L) — 7 Tasks

**목표:** 87권 text.json을 프로젝트 내부로 마이그레이션하고, 전체 KU 추출 파이프라인을 배치 실행

**주요 변경:**
- `books_catalog.yaml` — 87권 메타데이터 카탈로그 (CSV + JSON 매칭)
- `data/raw/{domain_dir}/` — 87개 text.json 복사 (standalone)
- `src/ingest/ku_extractor.py` — `domain_short` 하드코딩 제거, 4개 도메인 매핑
- `src/vault/renderer.py` — 슬래시 도메인명 경로 안전 처리
- `scripts/batch_ingest.py` — 87권 배치 처리 + 진행 추적
- 기존 DB 도메인 통일 (`경제` → `경제/경영`)

**4개 도메인 (books-final-processor 카테고리 그대로):**

| 카테고리 | domain_short | 권수 |
|---------|-------------|-----|
| 역사/사회 | hist | 18 |
| 경제/경영 | econ | 28 |
| 인문/자기계발 | humn | 18 |
| 과학/기술 | sci | 23 |

**의존성:** Phase 2 완료

### Stage I: Graph Layer (M) — 예정

**목표:** KU 간 관계(edges) 자동 생성 + 그래프 탐색 모듈

- `src/graph/edge_builder.py` — within-book + cross-domain edge 생성
- `src/graph/traversal.py` — 그래프 탐색 (depth N hop)
- CLI: `ks explore ku-id --depth 2`
- Edge 6타입: explains, supports, contradicts, extends, example_of, analogous_to
- Dispute axis: contradicts edge 클러스터 자동 요약

**의존성:** Stage H (87권 KU 데이터)

### Stage J: Generation 확장 + Hybrid Search (M) — 예정

**목표:** 아이디어 생성 파이프라인 + Vector+Graph 복합 검색

- `src/generation/idea.py` — 아이디어 생성 (business, content, serendipity 3모드)
- `src/search/hybrid.py` — Vector Search + Graph 1-hop 확장
- CLI: `ks generate idea --mode business --domains 경제/경영,과학/기술`

**의존성:** Stage I (Graph 데이터 + 탐색 모듈)

---

## 5. Task Breakdown

### Stage H Tasks (87권 마이그레이션 + 배치)

| ID | Task | Size | 의존성 | 비고 |
|----|------|------|--------|------|
| H.1 | 북 카탈로그 생성 (`scripts/build_catalog.py` → `books_catalog.yaml`) | M | - | CSV+JSON 매칭, 87권 book_id 할당 |
| H.2 | 데이터 마이그레이션 (`scripts/migrate_data.py`) | S | H.1 | 87개 text.json → `data/raw/{domain}/` 복사 |
| H.3 | `ku_extractor.py` domain_short 파라미터화 | S | - | line 154 하드코딩 제거, DOMAIN_SHORT_MAP 추가 |
| H.4 | `renderer.py` 슬래시 도메인 경로 처리 | S | - | `_domain_to_dir()` 헬퍼 추가 |
| H.5 | `config.yaml` + 기존 DB 도메인 통일 | S | H.1 | books 섹션 → catalog 참조, 경제→경제/경영 UPDATE |
| H.6 | 배치 처리 스크립트 (`scripts/batch_ingest.py`) | L | H.1~H.5 | 87권 순차 처리, 진행 추적, 에러 격리 |
| H.7 | 전체 검증 + Vault 재렌더링 | M | H.6 | stats 확인, 4개 도메인 Vault 구조 |

### Stage I Tasks (Graph Layer) — 추후 상세화

| ID | Task | Size | 의존성 | 비고 |
|----|------|------|--------|------|
| I.1 | `src/graph/edge_builder.py` — within-book edge 생성 | L | H.7 | LLM 기반 관계 판정 |
| I.2 | cross-domain edge 생성 | L | I.1 | 임베딩 유사도 후보 → LLM 관계 타입 |
| I.3 | `src/graph/traversal.py` — 그래프 탐색 | M | I.1 | depth N hop, 경로 스코어링 |
| I.4 | CLI `ks explore` + Vault connections 업데이트 | M | I.3 | |
| I.5 | Dispute axis 자동 요약 | M | I.2 | contradicts edge 클러스터 분석 |

### Stage J Tasks (Generation 확장) — 추후 상세화

| ID | Task | Size | 의존성 | 비고 |
|----|------|------|--------|------|
| J.1 | `src/search/hybrid.py` — Vector + Graph 복합 검색 | M | I.3 | PathScore 적용 |
| J.2 | `src/generation/idea.py` — 아이디어 생성 파이프라인 | L | J.1 | 3모드 (business, content, serendipity) |
| J.3 | CLI `ks generate idea` + 통합 테스트 | M | J.2 | |

**합계:** Stage H: 7개 (S:3, M:2, L:2) / Stage I: 5개 / Stage J: 3개

---

## 6. Risks & Mitigation

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| OpenAI rate limit (87권 배치) | 처리 중단 | 높 | delay_between_books=2.0, 자동 재시도, 체크포인트 재시작 |
| KU 추출 비용 ($100-200) | 예산 초과 | 중 | GPT-4.1-mini 유지, 도메인별 분할 실행, dry-run 검증 |
| 1권 처리 실패 (JSON 파싱 오류) | 배치 블록 | 중 | try/except + failed 마킹 후 계속 진행 |
| 도메인 슬래시 → 경로 오류 | Vault/파일 생성 실패 | 중 | `_domain_to_dir()` 헬퍼 (역사/사회→역사-사회) |
| Cross-domain edge 환각 | 잘못된 연결 → 잘못된 아이디어 | 중 | strength<0.7 edge는 proposed 상태, 수동 확인 |
| 긴 처리 시간 (4-6시간) | 중단 후 데이터 손실 | 중 | 북 단위 체크포인트 + DB 멱등성 (INSERT OR IGNORE) |

---

## 7. Dependencies

### 내부 의존성

```
Phase 2 (완료) ──→ Stage H ──→ Stage I ──→ Stage J
                    (87권)      (Graph)     (Idea+Hybrid)
```

### 외부 의존성

| 의존성 | 용도 | 비고 |
|--------|------|------|
| OpenAI API (GPT-4.1-mini) | KU 추출, edge 생성 | $100-200 (87권 배치) |
| OpenAI API (text-embedding-3-large) | 임베딩 | $2-3 |
| books-final-processor text.json | 87권 원본 텍스트 | H.2에서 프로젝트 내 복사 (standalone) |
| books-final-processor CSV | 도서 메타데이터 | H.1에서 catalog 생성 시 1회 참조 |

### Phase 4 연결

Phase 3 산출물 → Phase 4 입력:
- 87권 KU 데이터 (10,000-15,000 KUs)
- Graph edges (수천 개)
- Hybrid search 모듈
- 아이디어 생성 파이프라인

---

## 8. 비용 추정

| 항목 | 추정 비용 |
|------|----------|
| KU 추출 (GPT-4.1-mini, 87권) | $100-200 |
| 임베딩 (text-embedding-3-large) | $2-3 |
| Edge 생성 (within-book + cross-domain) | $50-100 |
| **Phase 3 합계** | **$150-300** |
