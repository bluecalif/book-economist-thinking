# Project Tasks
> Last Updated: 2026-03-02

## Overall Progress

| 항목 | 값 |
|------|---|
| 전체 Phase | 6개 (Phase 6는 조건부) |
| 완료 Phase | 2 (Phase 1, Phase 2) |
| 현재 Phase | Phase 3 — Partially-Full 12권 + 성능 평가 |
| 현재 Stage | H.partial 착수 대기 (파일럿 완료, Quality Gate PASS) |

---

## Phase Progress Summary

| Phase | Status | Progress | Current Step | 비고 |
|-------|--------|----------|--------------|------|
| Phase 1: 데이터 파이프라인 (A~D) | Complete ✅ | 18/18 (100%) | 전체 완료 | `4d33a2a` |
| Phase 2: 서비스 레이어 (E~G) | Complete ✅ | 11/11 (100%) | 전체 완료 | `acc1942` |
| Phase 3: Partially-Full 12권 (H~K) | In Progress | 14/27 (52%) | H.partial 대기 | Pilot ✅ QG ✅ |
| Phase 4: 전체 도서 확장 (M~P) | Planning | 0/11 (0%) | Phase 3 완료 후 | dev-docs 생성됨 |
| Phase 5: 진화 (Evolution) | Planned | - | - | Phase 4 완료 후 |
| Phase 6: 웹 UI | Conditional | - | - | 가치 검증 통과 시 |

---

## Phase 1 Tasks (18/18 ✅)

### Stage A: 프로젝트 초기화 — 5/5 ✅ `4796a61`
### Stage B: DB 스키마 — 4/4 ✅ `07096fa`
### Stage C: JSON 파싱 — 4/4 ✅ `67b21e7`
### Stage D: KU 추출 — 5/5 ✅ `4d33a2a`

**최종 메트릭:** 341 raw_spans, 997 KUs, 997 embeddings, E2E 26/26 PASS

---

## Phase 2 Tasks (11/11 ✅)

### Stage E: 의미 검색 (S) — 3/3 ✅ `dcb8043`
### Stage F: 콘텐츠 생성 (M) — 4/4 ✅ `1f0544e`
### Stage G: CLI + 통합 (L) — 4/4 ✅ `acc1942`

**최종 메트릭:** books=1, spans=341, kus=997, chroma=997, gens=2

---

## Phase 3 Tasks (14/27) — Partially-Full + 평가

→ 상세: `docs/phases/phase-3/tasks.md`

### Stage H.infra: 인프라 준비 ($0) — 6/6 ✅
### Stage H.pilot: 파일럿 인제스트 (~$1) — 3/3 ✅
### Stage I.pilot: 파일럿 그래프 (~$3) — 5/5 ✅
### Quality Gate: 품질 판정 — ✅ PASS
### Stage H.partial: 추가 8권 인제스트 (~$2.2) — 0/2
### Stage I.partial: 12권 edge 생성 (~$5-10) — 0/4
### Stage J: Generation 확장 + Hybrid ($0-1) — 0/3
### Stage K: 성능 평가 + 로직 개선 ($1-3) — 0/4

**현재 메트릭:** books=4, spans=1,724, kus=5,872, chroma=5,872, edges=11,662

---

## Phase 4 Tasks (0/11) — 전체 도서 확장

→ 상세: `docs/phases/phase-4/tasks.md`

### Stage M: 사전 확인 ($0) — 0/2
### Stage N: 75권 인제스트 (~$21) — 0/3
### Stage O: 전체 edge 생성 (~$15-30) — 0/4
### Stage P: 통합 검증 ($0-1) — 0/2

---

## Key Decisions

| # | Decision | Phase | Date | Rationale |
|---|----------|-------|------|-----------|
| 1 | Raw SQL + 헬퍼 함수 (ORM 미사용) | Phase 1 | 2026-02-25 | 단순성 우선, 테이블 5개로 ORM 불필요 |
| 2 | 기존 JSON 우선 경로 | Phase 1 | 2026-02-25 | PDF 직접 파싱보다 기존 파싱 데이터 먼저 활용 |
| 3 | edges 테이블 DDL만 Phase 1 | Phase 1 | 2026-02-25 | DDL 생성만, 실제 사용은 Phase 3 |
| 4 | GPT-4o mini 우선 | Phase 1 | 2026-02-25 | KU 추출 비용 절감, 필요시 업그레이드 |
| 5 | Typer CLI 확정 | Phase 2 | 2026-02-25 | 타입 힌트 기반, Click보다 간결 |
| 6 | Hook: PowerShell 제거 | Infra | 2026-02-26 | PS1 5.1 한국어 인코딩 비호환 |
| 7 | 커맨드 이름 변경 | Infra | 2026-02-27 | design-docs→dev-docs, progress-update→step-update |
| 8 | project-overall 3파일 분리 | Infra | 2026-02-27 | project-status.md → plan/context/tasks 분리 |
| 9 | Phase 1 MVP → Phase 1+2 분리 | Infra | 2026-02-27 | 데이터 파이프라인(A~D)과 서비스 레이어(E~G) 분리 |
| 10 | text-embedding-3-large 확정 | Phase 1 | 2026-02-28 | small → large 전환, 정확도 우선 |
| 11 | similarity threshold 0.6 | Phase 2 | 2026-02-28 | 10쿼리 튜닝 결과, cosine distance 기준 |
| 12 | 4개 카테고리 그대로 사용 | Phase 3 | 2026-03-01 | books-final-processor CSV 분야 컬럼 활용 |
| 13 | text.json 프로젝트 내 복사 (standalone) | Phase 3 | 2026-03-01 | 프로젝트가 모든 지식 소스 자체 포함 |
| 14 | domain_short 매핑: hist/econ/humn/sci | Phase 3 | 2026-03-01 | KU ID 4자리 약어 |
| 15 | 기존 domain "경제"→"경제/경영" 통일 | Phase 3 | 2026-03-01 | 4개 카테고리 체계로 일관성 확보 |
| 16 | Pilot First 전략 채택 | Phase 3 | 2026-03-01 | 비경제 도메인 KU 품질 미검증 |
| 17 | LLM 응답 캐시 도입 | Phase 3 | 2026-03-01 | 재실행 비용 $0 |
| 18 | KU + Graph 함께 파일럿 검증 | Phase 3 | 2026-03-01 | end-to-end 품질 확인 |
| **19** | **Phase 3 범위를 카테고리당 3권(12권)으로 축소** | **Phase 3** | **2026-03-02** | **전체 파이프라인 완성 + 성능 평가 우선, 전체 확장은 Phase 4** |
| **20** | **Phase 4를 전체 도서 확장으로 재정의** | **Phase 4** | **2026-03-02** | **Phase 3 로직 개선 완료 후 나머지 75권 확장** |
| **21** | **Stage K 성능 평가 추가** | **Phase 3** | **2026-03-02** | **로직 개선 기회를 전체 확장 전에 확보** |
