# Phase 3: 87권 확장 + 그래프 레이어 (Pilot First)
> Last Updated: 2026-03-01
> Status: Planning
> **전제:** Phase 2 완료 (1권 파이프라인 + 검색 + 생성 + CLI + Vault)

## 1. Summary (개요)

**목적:** 1권 파이프라인을 87권으로 확장하고, KU 간 관계 그래프(L2)를 구축하여 cross-domain 지식 연결 및 아이디어 생성을 가능하게 한다.

**전략 변경 (v1→v2):** 87권 전체 인제스트 후 그래프 구축 → **4권 파일럿으로 KU+Graph end-to-end 검증 후 전체 확장.** 비용 리스크를 1/3로 줄이고, 비경제 도메인 KU 품질을 조기 검증.

**범위:**
- H.infra: 인프라 준비 (코드 수정, 카탈로그, 마이그레이션, LLM 캐시)
- H.pilot: 4권 파일럿 인제스트 (도메인당 1권)
- I.pilot: 파일럿 그래프 레이어 (edge 생성 + 탐색)
- Quality Gate: 품질 판정 + 프롬프트 튜닝
- H.full: 나머지 83권 배치 인제스트
- I.full: 전체 그래프 레이어 + Dispute axis
- J: Generation 확장 (아이디어 생성 + 하이브리드 검색)

**예상 산출물:**
- 87권 text.json 데이터 (`data/raw/`)
- 87권 book catalog (`books_catalog.yaml`)
- LLM 응답 캐시 (`src/ingest/llm_cache.py`, `data/llm_cache.db`)
- 배치 처리 스크립트 (`scripts/batch_ingest.py`)
- ~75,000+ KUs + ChromaDB embeddings
- 수천 개 edges (within-book + cross-domain)
- `src/graph/` 모듈 (edge_builder, traversal, dispute)
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
| LLM 캐시 | 없음 (캐시 메커니즘 미구현) |

**사용 가능한 외부 데이터:**
- `C:\Projects-2026\maintenance\books-final-processor\data\output\text\` — 87권 text.json
- `C:\Projects-2026\maintenance\books-final-processor\docs\100권 노션 원본_수정.csv` — 87권 메타데이터

---

## 3. Target State (목표 상태)

Phase 3 완료 후:
- `ks stats` → books=87, spans≥25,000, kus≥75,000, chroma≥75,000
- `ks search "기술 혁신과 노동시장"` → 다수 도메인에서 KU 반환
- `ks explore ku-id --depth 2` → 연결된 KU 탐색
- `ks generate idea --mode business --domains 경제/경영,과학/기술` → 아이디어 후보 생성
- `vault/domains/` 하위 4개 도메인 디렉터리 구조
- Cross-domain 연결에서 실제 유용한 통찰 산출
- LLM 캐시로 재실행 시 비용 절감

---

## 4. Implementation Stages

### 전체 흐름

```
H.infra ($0) → H.pilot (~$1) → I.pilot (추정 $2-5) → Quality Gate
                                                         ├─ PASS → H.full (~$23) → I.full (추정 $10-20) → J ($0)
                                                         └─ FAIL → 프롬프트 튜닝 → 재실행 (캐시 덕분에 비용 최소)
```

### Stage H.infra: 인프라 준비 (API 비용 $0) — 6 Tasks

**목표:** 87권 처리를 위한 코드 파라미터화, 데이터 마이그레이션, LLM 캐시 구축

**주요 변경:**
- `books_catalog.yaml` — 87권 메타데이터 카탈로그 (status: done/pilot/pending)
- `data/raw/{domain_dir}/` — 87개 text.json 복사
- `src/ingest/ku_extractor.py` — domain_short 파라미터화
- `src/vault/renderer.py` — 슬래시 도메인 경로 처리
- `src/ingest/llm_cache.py` — **LLM 응답 캐시 (비용 절감 핵심)**
- 기존 DB 도메인 통일 (`경제` → `경제/경영`)

**의존성:** Phase 2 완료

### Stage H.pilot: 파일럿 인제스트 (~$1) — 3 Tasks

**목표:** 4개 도메인 각 1권(경제는 기존 재사용, 3권 신규) 인제스트 + KU 품질 검증

**파일럿 도서:** 도메인당 1권, 서로 다른 서술 유형(서술형/논증형/에세이형/기술형)
- 경제/경영: 경제학자의 생각법 (기존 재사용, $0)
- 역사/사회, 인문/자기계발, 과학/기술: 각 1권 신규 (~$0.28/권)

> **실측 데이터 (econ-thinking 1권):** input $0.09 (220K tokens) + output $0.19 (110K tokens) = **$0.28/권**

**의존성:** H.infra 완료

### Stage I.pilot: 파일럿 그래프 (추정 $2-5) — 5 Tasks

**목표:** 4-5권 KU로 edge 생성 + 그래프 탐색 end-to-end 검증

- within-book edge + cross-domain edge 생성
- 그래프 탐색 모듈 + CLI `ks explore`
- 품질 리포트 출력

**의존성:** H.pilot 완료

### Quality Gate: 품질 판정

**목표:** 전체 확장 전 KU + Graph 품질 검증

| # | 메트릭 | 목표 |
|---|--------|------|
| 1 | 도메인별 parse 성공률 | ≥ 95% |
| 2 | 도메인별 claim 존재율 | ≥ 80% |
| 3 | cross-domain edge 의미 적합도 | ≥ 60% (수동 10건) |
| 4 | within-book edge 의미 적합도 | ≥ 70% (수동 10건) |

PASS → H.full 진행 / FAIL → 프롬프트 튜닝 후 재실행 (캐시 히트로 비용 최소)

### Stage H.full: 나머지 83권 배치 (~$23) — 2 Tasks

**목표:** 나머지 83권 인제스트 (파일럿/done 자동 skip)

**의존성:** Quality Gate 통과

### Stage I.full: 전체 그래프 + Dispute (추정 $10-20) — 4 Tasks

**목표:** 87권 전체 edge 생성 + Vault connections + Dispute axis

**의존성:** H.full 완료

### Stage J: Generation 확장 + Hybrid Search ($0) — 3 Tasks

**목표:** 아이디어 생성 파이프라인 + Vector+Graph 복합 검색

**의존성:** I.full 완료

---

## 5. Task Breakdown

### Stage H.infra (인프라 준비) — 6 Tasks

| ID | Task | Size | 의존성 |
|----|------|------|--------|
| H.1 | 북 카탈로그 생성 (`build_catalog.py` → `books_catalog.yaml`) | M | - |
| H.2 | 데이터 마이그레이션 (`migrate_data.py`) | S | H.1 |
| H.3 | `ku_extractor.py` domain_short 파라미터화 | S | - |
| H.4 | `renderer.py` 슬래시 도메인 경로 처리 | S | - |
| H.5 | `config.yaml` + 기존 DB 도메인 통일 | S | H.1 |
| H.cache | LLM 응답 캐시 레이어 (`llm_cache.py`) | M | - |

### Stage H.pilot (파일럿 인제스트) — 3 Tasks

| ID | Task | Size | 의존성 |
|----|------|------|--------|
| H.6p | 배치 처리 스크립트 (파일럿 모드 지원) | L | H.1~H.5, H.cache |
| H.7p | 파일럿 3권 인제스트 실행 | M | H.6p |
| H.8p | 파일럿 KU 품질 리포트 생성 | S | H.7p |

### Stage I.pilot (파일럿 그래프) — 5 Tasks

| ID | Task | Size | 의존성 |
|----|------|------|--------|
| I.1p | `edge_builder.py` — edge 생성 모듈 | L | H.7p |
| I.2p | 파일럿 edge 생성 실행 | M | I.1p |
| I.3p | `traversal.py` — 그래프 탐색 | M | I.2p |
| I.4p | CLI `ks explore` 추가 | S | I.3p |
| I.5p | 파일럿 그래프 품질 리포트 | S | I.2p |

### Stage H.full (전체 배치) — 2 Tasks

| ID | Task | Size | 의존성 |
|----|------|------|--------|
| H.9 | 나머지 83권 배치 인제스트 | L | Quality Gate |
| H.10 | 전체 검증 + Vault 재렌더링 | M | H.9 |

### Stage I.full (전체 그래프) — 4 Tasks

| ID | Task | Size | 의존성 |
|----|------|------|--------|
| I.6 | 전체 within-book edge 생성 | L | H.10 |
| I.7 | 전체 cross-domain edge 생성 | L | I.6 |
| I.8 | Vault connections 업데이트 | M | I.7 |
| I.9 | Dispute axis 자동 요약 | M | I.7 |

### Stage J (Generation 확장) — 3 Tasks

| ID | Task | Size | 의존성 |
|----|------|------|--------|
| J.1 | `hybrid.py` — Vector + Graph 복합 검색 | M | I.8 |
| J.2 | `idea.py` — 아이디어 생성 파이프라인 | L | J.1 |
| J.3 | CLI `ks generate idea` + 통합 테스트 | M | J.2 |

**합계:** 23 Tasks (S:6, M:11, L:6)

---

## 6. Risks & Mitigation

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| 비경제 도메인 KU 품질 저조 | 전체 시스템 품질 하락 | 중 | **파일럿으로 조기 검증**, 도메인별 프롬프트 오버라이드 |
| KU 추출 비용 초과 | 예산 초과 | 중 | LLM 캐시로 재실행 비용 $0, 파일럿 분리 |
| 배치 중단 시 데이터 손실 | 재처리 비용 | 중 | **LLM 캐시 + 체크포인트** → 재실행 안전 |
| Cross-domain edge 환각 | 잘못된 연결 | 중 | 파일럿 수동 검토, threshold 조정 |
| OpenAI rate limit | 처리 중단 | 높 | delay + 자동 재시도 + 체크포인트 |
| 75,000+ 파일 Obsidian 성능 | UX 저하 | 중 | 벤치마크 필요, 필요시 도메인별 분리 |

---

## 7. Dependencies

### 내부 의존성

```
Phase 2 (완료) → H.infra → H.pilot → I.pilot → Quality Gate
                                                   ├─ PASS → H.full → I.full → J
                                                   └─ FAIL → 튜닝 → 재실행
```

### 외부 의존성

| 의존성 | 용도 | 비고 |
|--------|------|------|
| OpenAI API (GPT-4.1-mini) | KU 추출, edge 생성 | 파일럿 ~$3-6, 전체 추가 ~$33-43 |
| OpenAI API (text-embedding-3-large) | 임베딩 | $2-3 |
| books-final-processor text.json | 87권 원본 텍스트 | H.2에서 1회 복사 |
| books-final-processor CSV | 도서 메타데이터 | H.1에서 1회 참조 |

---

## 8. 비용 추정

> **실측 기반 (2026-03-01):** econ-thinking 1권 KU 추출 = input $0.09 (220K tokens) + output $0.19 (110K tokens) = **$0.28/권**
> Edge 생성 비용은 아직 실측 데이터 없음 (추정치 사용)

| 단계 | 항목 | 비용 | 근거 |
|------|------|------|------|
| Quality Gate 전 | 파일럿 KU 추출 (3권 신규) | ~$1 | 실측 $0.28/권 × 3 |
| Quality Gate 전 | 파일럿 edge 생성 | 추정 $2-5 | 미검증 |
| Quality Gate 전 소계 | | **~$3-6** | |
| Quality Gate 후 | 나머지 83권 KU 추출 | ~$23 | 실측 $0.28/권 × 83 |
| Quality Gate 후 | 전체 edge 생성 | 추정 $10-20 | 미검증 |
| Quality Gate 후 소계 | | **~$33-43** | |
| **Phase 3 합계** | | **~$36-49** | KU 실측 + edge 추정 |

**vs 기존 추정:** $175-325 → **~$36-49** (KU 추출 비용이 기존 추정의 ~1/60)
**캐시 효과:** 프롬프트 튜닝 후 재실행 시 변경 안 된 span은 캐시 히트 → 추가 비용 ≈ $0
