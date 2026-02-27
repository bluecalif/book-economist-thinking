# Project Plan
> Last Updated: 2026-02-27

## Roadmap Overview

Knowledge System — 87권 도서를 구조화된 지식 파이프라인으로 변환하여 콘텐츠/아이디어 생성 엔진 구축.
전략: 1권 MVP → 5권 확장 → 87권 완성 → 웹 UI (선택).

```
Phase 1 (1권 MVP)  ──→  Phase 2 (그래프+5권)  ──→  Phase 3 (87권+진화)  ──→  Phase 4 (웹 UI)
  L0+L1+L3 기본          L2+L3 확장                 전체 규모+L4              FastAPI+프론트
```

---

## Phase 1: 1권 MVP — In Progress

**목표:** 경제학자의 생각법 1권으로 파이프라인 완성 + 생성 기능 가치 검증
**예상 기간:** Week 1-2
**레이어:** L0 Raw, L1 KU, L3 Generation (기본)

### Stages

| Stage | 이름 | 범위 | 크기 |
|-------|------|------|------|
| A | 프로젝트 초기화 | pyproject.toml, 디렉터리, config.yaml | S |
| B | DB 스키마 | SQLite DDL + CRUD, ChromaDB 래퍼 | M |
| C | PDF 파싱 | 기존 JSON → raw_spans 변환 | M |
| D | KU 추출 | raw_spans → KU, 임베딩, 프롬프트 최적화 | L |
| E | 의미 검색 | ChromaDB 벡터 검색 | S |
| F | 콘텐츠 생성 | content.py + 템플릿 3종 (blog, summary, thread) | M |
| G | CLI + 통합 | cli.py, vault/renderer.py, 통합 테스트 | L |

### 완료 기준 (masterplan §14)
- `ks ingest book.pdf` → KU 추출 + DB 저장 + 마크다운 생성
- `ks search "매몰비용"` → 관련 KU 반환
- `ks generate content --topic "매몰비용" --format blog` → 블로그 초안 생성
- 생성된 콘텐츠가 실제 사용 가능한 품질인지 평가

### 산출물
- `src/ingest/pdf_parser.py`, `src/ingest/ku_extractor.py`
- `src/db/models.py`, `src/db/vectors.py`
- `src/search/vector.py`
- `src/generation/content.py` + `src/generation/templates/`
- `src/cli.py`, `src/vault/renderer.py`
- `config.yaml`, `pyproject.toml`

---

## Phase 2: 그래프 + 아이디어 + 5권 확장 — Planned

**목표:** Cross-domain 연결의 가치 검증
**예상 기간:** Week 3-4
**레이어:** L2 Graph, L3 Generation (확장)
**전제:** Phase 1 완료

### 산출물
- `src/graph/edge_builder.py`, `src/graph/traversal.py`
- `src/generation/idea.py`
- CLI 확장 (explore, generate idea)
- 500-1,000 KU + cross-domain edges

### 완료 기준
- `ks explore ku-id --depth 2` → 연결된 KU 탐색
- `ks generate idea --mode business --domains 경제,기술` → 아이디어 후보 생성
- Cross-domain 연결에서 실제 유용한 통찰 산출

---

## Phase 3: 87권 완료 + 진화 — Planned

**목표:** 전체 규모 달성 + 외부 지식 유입
**예상 기간:** Month 2-3
**레이어:** L4 Evolution, 전체 레이어 안정화
**전제:** Phase 2 완료

### 산출물
- `src/evolution/crawler.py`, `src/evolution/sync.py`
- `src/search/hybrid.py`
- 10,000-15,000 KU, 수천 edges
- Dispute 자동 요약

### 완료 기준
- 87권 전체 처리 완료
- `ks crawl --ku ku-id` → 웹 보강 정보 수집 + KU 업데이트 제안
- 7개 도메인 간 dispute 축 자동 식별

---

## Phase 4: 웹 UI — Conditional

**조건:** Phase 1-3 가치 검증 결과 웹 UI 필요 시에만 실행
**레이어:** API + 프론트엔드

### 산출물
- FastAPI 엔드포인트
- 그래프 시각화 + 생성 UI

---

## Phase Dependencies

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
  │                                    ↑
  └─── Phase 1-3 가치 검증 결과에 따라 조건부 실행
```

- Phase 2는 Phase 1의 L0+L1+L3 파이프라인에 의존
- Phase 3는 Phase 2의 L2 Graph에 의존
- Phase 4는 Phase 1-3 전체 완료 + 가치 검증 통과 시에만 실행

## Timeline

| Phase | 시작 | 종료 | 비용 추정 |
|-------|------|------|----------|
| Phase 1 | 2026-02 | 2026-03 초 | $3-10 |
| Phase 2 | Phase 1 완료 후 | +2주 | $10-30 |
| Phase 3 | Phase 2 완료 후 | +4-6주 | $150-350 |
| Phase 4 | 조건부 | TBD | TBD |
