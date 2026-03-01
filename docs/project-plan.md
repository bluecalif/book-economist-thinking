# Project Plan
> Last Updated: 2026-03-01
> Phase Dev-Docs: `docs/phases/phase-1/` (A~D), `docs/phases/phase-2/` (E~G), `docs/phases/phase-3/` (H~J)

## Roadmap Overview

Knowledge System — 87권 도서를 구조화된 지식 파이프라인으로 변환하여 콘텐츠/아이디어 생성 엔진 구축.
전략: 1권 데이터 파이프라인 → 서비스 레이어 → 5권 확장 → 87권 완성 → 웹 UI (선택).

```
Phase 1 (데이터 파이프라인) ──→ Phase 2 (서비스 레이어) ──→ Phase 3 (87권+그래프) ──→ Phase 4 (진화) ──→ Phase 5 (웹 UI)
  L0+L1 기본                     L1검색+L3생성+CLI           87권확장+L2+L3확장       L4 Evolution        FastAPI+프론트
```

---

## Phase 1: 데이터 파이프라인 (Stage A~D) — Complete ✅

**목표:** 경제학자의 생각법 1권의 원본 텍스트를 KU로 변환하는 데이터 파이프라인 완성
**예상 기간:** Week 1-2
**레이어:** L0 Raw, L1 KU
**dev-docs:** `docs/phases/phase-1/`

### Stages

| Stage | 이름 | 범위 | 크기 |
|-------|------|------|------|
| A | 프로젝트 초기화 | pyproject.toml, 디렉터리, config.yaml | S |
| B | DB 스키마 | SQLite DDL + CRUD, ChromaDB 래퍼 | M |
| C | PDF 파싱 | 기존 JSON → raw_spans 변환 | M |
| D | KU 추출 | raw_spans → KU, 임베딩, 프롬프트 최적화 | L |

### 산출물
- `src/ingest/pdf_parser.py`, `src/ingest/ku_extractor.py`
- `src/db/models.py`, `src/db/vectors.py`
- `config.yaml`, `pyproject.toml`
- SQLite DB (books, raw_spans, knowledge_units 활성) + ChromaDB ku_embeddings

### 완료 기준
- `pyproject.toml` + `src/` 구조 완성
- 기존 JSON → raw_spans 변환 + DB 저장
- raw_spans → KU 추출 (LLM) + 임베딩 저장
- 100-200 KU 확보 (경제학자의 생각법)

---

## Phase 2: 서비스 레이어 (Stage E~G) — Complete ✅

**목표:** 데이터 파이프라인 위에 검색/생성/CLI를 올려 사용 가능한 시스템 완성
**예상 기간:** Week 2-3
**레이어:** L1 검색, L3 Generation (기본)
**전제:** Phase 1 완료
**dev-docs:** `docs/phases/phase-2/`

### Stages

| Stage | 이름 | 범위 | 크기 |
|-------|------|------|------|
| E | 의미 검색 | ChromaDB 벡터 검색 | S |
| F | 콘텐츠 생성 | content.py + 템플릿 3종 (blog, summary, thread) | M |
| G | CLI + 통합 | cli.py, vault/renderer.py, 통합 테스트 | L |

### 산출물
- `src/search/vector.py`
- `src/generation/content.py` + `src/generation/templates/`
- `src/cli.py`, `src/vault/renderer.py`
- Obsidian 호환 마크다운 vault

### 완료 기준 (masterplan §14 — 1권 MVP 전체 완료)
- `ks ingest book.pdf` → KU 추출 + DB 저장 + 마크다운 생성
- `ks search "매몰비용"` → 관련 KU 반환
- `ks generate content --topic "매몰비용" --format blog` → 블로그 초안 생성
- 생성된 콘텐츠가 실제 사용 가능한 품질인지 평가

---

## Phase 3: 87권 확장 + 그래프 레이어 (Stage H~J) — In Progress (Pilot First)

**목표:** 87권 배치 처리 + L2 Graph + L3 아이디어 생성 + Hybrid Search
**전략:** Pilot First — 4권 파일럿 → Quality Gate → 전체 확장
**예상 기간:** 2-4주
**레이어:** L0+L1 확장 (87권), L2 Graph, L3 Generation (확장)
**전제:** Phase 2 완료
**dev-docs:** `docs/phases/phase-3/`

### Stages

| Stage | 이름 | 범위 | 크기 | 비용 |
|-------|------|------|------|------|
| H.infra | 인프라 준비 | 카탈로그, 데이터 마이그레이션, 코드 수정, LLM 캐시 | M | $0 |
| H.pilot | 파일럿 인제스트 | 4권(도메인당 1권) 인제스트 + KU 품질 검증 | L | ~$1 |
| I.pilot | 파일럿 그래프 | edge 생성 + 그래프 탐색 end-to-end 검증 | M | 추정 $2-5 |
| Quality Gate | 품질 판정 | parse ≥95%, claim ≥80%, edge 적합도 ≥60-70% | - | $0 |
| H.full | 전체 배치 | 나머지 83권 배치 인제스트 | L | ~$23 |
| I.full | 전체 그래프 | 전체 edge 생성 + Dispute axis | L | 추정 $10-20 |
| J | Generation 확장 | 아이디어 생성 + Vector+Graph 하이브리드 검색 | M | $0 |

### 전체 흐름

```
H.infra ($0) → H.pilot (~$1) → I.pilot (추정 $2-5) → Quality Gate
                                                         ├─ PASS → H.full (~$23) → I.full (추정 $10-20) → J ($0)
                                                         └─ FAIL → 프롬프트 튜닝 → 재실행 (캐시 $0)
```

### 산출물
- 87권 text.json → `data/raw/` (standalone)
- `books_catalog.yaml` — 87권 메타데이터
- `src/ingest/llm_cache.py` + `data/llm_cache.db` — LLM 응답 캐시
- `scripts/batch_ingest.py` — 배치 처리
- ~75,000+ KU + ChromaDB embeddings
- `src/graph/edge_builder.py`, `src/graph/traversal.py`, `src/graph/dispute.py`
- `src/generation/idea.py`, `src/search/hybrid.py`
- 4개 도메인 Vault 구조

### 완료 기준
- `ks stats` → books=87, spans≥25,000, kus≥75,000, chroma≥75,000
- `ks explore ku-id --depth 2` → 연결된 KU 탐색
- `ks generate idea --mode business --domains 경제/경영,과학/기술` → 아이디어 생성
- 4개 도메인 간 dispute 축 자동 식별

---

## Phase 4: 진화 (Evolution) — Planned

**목표:** 외부 지식 유입 + 마크다운 동기화
**예상 기간:** Month 2-3
**레이어:** L4 Evolution
**전제:** Phase 3 완료

### 산출물
- `src/evolution/crawler.py` — 웹 크롤링 기반 KU 확장
- `src/evolution/sync.py` — 마크다운 ↔ DB 동기화
- Maturity 자동 승격 (M0→M1→M2)

### 완료 기준
- `ks crawl --ku ku-id` → 웹 보강 정보 수집 + KU 업데이트 제안
- `ks sync` → Vault 편집 → DB 반영

---

## Phase 5: 웹 UI — Conditional

**조건:** Phase 1-4 가치 검증 결과 웹 UI 필요 시에만 실행
**레이어:** API + 프론트엔드

### 산출물
- FastAPI 엔드포인트
- 그래프 시각화 + 생성 UI

---

## Phase Dependencies

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
  │                                                ↑
  └─── Phase 1-4 가치 검증 결과에 따라 조건부 실행 ──┘
```

- Phase 2는 Phase 1의 L0+L1 데이터 파이프라인에 의존
- Phase 3는 Phase 2의 검색+생성+CLI 서비스 레이어에 의존
- Phase 4는 Phase 3의 87권 KU + L2 Graph에 의존
- Phase 5는 Phase 1-4 전체 완료 + 가치 검증 통과 시에만 실행

## Timeline

| Phase | 시작 | 종료 | 비용 추정 |
|-------|------|------|----------|
| Phase 1 | 2026-02 | 2026-02-28 ✅ | $1-3 |
| Phase 2 | 2026-02-28 | 2026-03-01 ✅ | $3-10 |
| Phase 3 | 2026-03-01 | +2-4주 | ~$36-49 (파일럿 ~$3-6 + 전체 ~$33-43) — KU 실측 + edge 추정 |
| Phase 4 | Phase 3 완료 후 | +2-4주 | $20-50 |
| Phase 5 | 조건부 | TBD | TBD |
