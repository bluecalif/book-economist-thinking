# Project Plan
> Last Updated: 2026-03-02
> Phase Dev-Docs: `docs/phases/phase-1/` (A~D), `docs/phases/phase-2/` (E~G), `docs/phases/phase-3/` (H~K), `docs/phases/phase-4/` (M~P)

## Roadmap Overview

Knowledge System — 87권 도서를 구조화된 지식 파이프라인으로 변환하여 콘텐츠/아이디어 생성 엔진 구축.
전략: 1권 파이프라인 → 서비스 레이어 → **12권 partially-full + 성능 평가** → 전체 확장 → 진화 → 웹 UI (선택).

```
Phase 1 (데이터 파이프라인) → Phase 2 (서비스 레이어) → Phase 3 (12권+그래프+평가) → Phase 4 (전체 확장) → Phase 5 (진화) → Phase 6 (웹 UI)
  L0+L1 기본                  L1검색+L3생성+CLI          12권+L2+L3+평가+개선       75권 확장              L4 Evolution        FastAPI+프론트
```

---

## Phase 1: 데이터 파이프라인 (Stage A~D) — Complete ✅

**목표:** 경제학자의 생각법 1권의 원본 텍스트를 KU로 변환하는 데이터 파이프라인 완성
**레이어:** L0 Raw, L1 KU
**dev-docs:** `docs/phases/phase-1/`

### Stages

| Stage | 이름 | 크기 |
|-------|------|------|
| A | 프로젝트 초기화 | S |
| B | DB 스키마 | M |
| C | PDF 파싱 | M |
| D | KU 추출 | L |

### 산출물
- 데이터 파이프라인 코드, SQLite + ChromaDB
- 341 raw_spans, 997 KUs, 997 embeddings

---

## Phase 2: 서비스 레이어 (Stage E~G) — Complete ✅

**목표:** 검색/생성/CLI를 올려 사용 가능한 시스템 완성
**레이어:** L1 검색, L3 Generation (기본)
**dev-docs:** `docs/phases/phase-2/`

### Stages

| Stage | 이름 | 크기 |
|-------|------|------|
| E | 의미 검색 | S |
| F | 콘텐츠 생성 | M |
| G | CLI + 통합 | L |

### 산출물
- 검색, 생성, CLI, Vault 마크다운 렌더링

---

## Phase 3: Partially-Full 12권 + 성능 평가 (Stage H~K) — In Progress (52%)

**목표:** 카테고리당 3권(12권)으로 KU + Edge + Generation + Search 완성, 성능 평가 + 로직 개선
**전략:** Pilot First (4권) → Quality Gate → Partially-Full (12권) → J (Generation) → K (평가+개선)
**레이어:** L0+L1 확장 (12권), L2 Graph, L3 Generation (확장)
**dev-docs:** `docs/phases/phase-3/`

### Stages

| Stage | 이름 | 비용 | 상태 |
|-------|------|------|------|
| H.infra | 인프라 준비 | $0 | ✅ |
| H.pilot | 파일럿 인제스트 (4권) | ~$1 | ✅ |
| I.pilot | 파일럿 그래프 | ~$3 | ✅ |
| Quality Gate | 품질 판정 | $0 | ✅ PASS |
| H.partial | 추가 8권 인제스트 | ~$2.2 | 대기 |
| I.partial | 12권 edge 생성 | ~$5-10 | 대기 |
| J | Generation 확장 + Hybrid | $0-1 | 대기 |
| K | 성능 평가 + 로직 개선 | $1-3 | 대기 |

### 산출물
- 12권 ~18,000 KU + edges
- Hybrid Search, 아이디어 생성 파이프라인
- 성능 평가 리포트, 로직 개선 사항

### 완료 기준
- books=12, kus≥18,000, cross-domain edges 생성
- 콘텐츠/아이디어 생성 품질 평가 완료
- 로직 개선 사항 반영 (필요 시)

---

## Phase 4: 전체 도서 확장 (Stage M~P) — Planning

**목표:** 나머지 75권 확장 → 87권 완전 커버리지
**전제:** Phase 3 Stage K 로직 개선 완료 확인
**레이어:** L0+L1+L2 확장 (87권)
**dev-docs:** `docs/phases/phase-4/`

### Stages

| Stage | 이름 | 비용 |
|-------|------|------|
| M | 사전 확인 | $0 |
| N | 75권 인제스트 | ~$21 |
| O | 전체 edge 생성 | ~$15-30 |
| P | 통합 검증 | $0-1 |

### 산출물
- 87권 ~75,000+ KU + 전체 edges
- 전체 Dispute axis, Vault

### 완료 기준
- `ks stats` → books=87, kus≥75,000
- 전체 규모 E2E 검증

---

## Phase 5: 진화 (Evolution) — Planned

**목표:** 외부 지식 유입 + 마크다운 동기화
**레이어:** L4 Evolution
**전제:** Phase 4 완료

### 산출물
- `src/evolution/crawler.py` — 웹 크롤링 기반 KU 확장
- `src/evolution/sync.py` — 마크다운 ↔ DB 동기화
- Maturity 자동 승격 (M0→M1→M2)

---

## Phase 6: 웹 UI — Conditional

**조건:** Phase 1-5 가치 검증 결과 웹 UI 필요 시에만 실행
**레이어:** API + 프론트엔드

---

## Phase Dependencies

```
Phase 1 → Phase 2 → Phase 3 (12권+평가+개선) → Phase 4 (75권 확장)
                                                    ↓
                                              Phase 5 (진화) → Phase 6 (웹 UI, 조건부)
```

- Phase 3 → Phase 4: **로직 개선 완료 확인 게이트** (Stage M.1)
- Phase 4 → Phase 5: 87권 전체 데이터 필요
- Phase 6: Phase 1-5 전체 가치 검증 통과 시에만

## Timeline

| Phase | 시작 | 종료 | 비용 추정 |
|-------|------|------|----------|
| Phase 1 | 2026-02 | 2026-02-28 ✅ | $1-3 |
| Phase 2 | 2026-02-28 | 2026-03-01 ✅ | $3-10 |
| Phase 3 | 2026-03-01 | +2-3주 | ~$12-20 |
| Phase 4 | Phase 3 완료 후 | +1-2주 | ~$36-52 |
| Phase 5 | Phase 4 완료 후 | +2-4주 | $20-50 |
| Phase 6 | 조건부 | TBD | TBD |
