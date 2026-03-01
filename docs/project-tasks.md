# Project Tasks
> Last Updated: 2026-03-01

## Overall Progress

| 항목 | 값 |
|------|---|
| 전체 Phase | 5개 (Phase 5는 조건부) |
| 완료 Phase | 2 (Phase 1, Phase 2) |
| 현재 Phase | Phase 3 — 87권 확장 + 그래프 레이어 |
| 현재 Stage | Stage H (87권 마이그레이션 + 배치) 착수 대기 |

---

## Phase Progress Summary

| Phase | Status | Progress | Current Step | 비고 |
|-------|--------|----------|--------------|------|
| Phase 1: 데이터 파이프라인 (A~D) | Complete ✅ | 18/18 Tasks (100%) | 전체 완료 | `4d33a2a` |
| Phase 2: 서비스 레이어 (E~G) | Complete ✅ | 11/11 Tasks (100%) | 전체 완료 | `acc1942` |
| Phase 3: 87권 확장 + 그래프 (H~J) | Planning | 0/23 Tasks (0%) | Stage H.infra 착수 대기 | dev-docs: `docs/phases/phase-3/` |
| Phase 4: 진화 (Evolution) | Planned | - | - | Phase 3 완료 후 |
| Phase 5: 웹 UI | Conditional | - | - | 가치 검증 통과 시 |

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

## Phase 3 Tasks (0/23) — Pilot First 전략

→ 상세: `docs/phases/phase-3/tasks.md`

### Stage H.infra: 인프라 준비 ($0) — 0/6
### Stage H.pilot: 파일럿 인제스트 (~$45-75) — 0/3
### Stage I.pilot: 파일럿 그래프 (~$10-20) — 0/5
### Quality Gate: 품질 판정
### Stage H.full: 전체 배치 (~$80-150) — 0/2
### Stage I.full: 전체 그래프 + Dispute (~$40-80) — 0/4
### Stage J: Generation 확장 + Hybrid ($0) — 0/3

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
| 12 | 4개 카테고리 그대로 사용 | Phase 3 | 2026-03-01 | books-final-processor CSV 분야 컬럼 활용, 7도메인 세분화 안 함 |
| 13 | text.json 프로젝트 내 복사 (standalone) | Phase 3 | 2026-03-01 | 프로젝트가 모든 지식 소스 자체 포함 |
| 14 | domain_short 매핑: hist/econ/humn/sci | Phase 3 | 2026-03-01 | KU ID 4자리 약어, 기존 econ 호환 |
| 15 | 기존 domain "경제"→"경제/경영" 통일 | Phase 3 | 2026-03-01 | 4개 카테고리 체계로 일관성 확보 |
| 16 | Pilot First 전략 채택 | Phase 3 | 2026-03-01 | 87권 일괄 → 4권 파일럿 → Quality Gate → 전체. 검증 전 리스크 $55-95 (기존의 1/3) |
| 17 | LLM 응답 캐시 도입 | Phase 3 | 2026-03-01 | `llm_cache.py` + `llm_cache.db`. 프롬프트 튜닝 후 재실행 비용 $0 |
| 18 | KU + Graph 함께 파일럿 검증 | Phase 3 | 2026-03-01 | end-to-end 품질 확인, 별도 검증 대비 판단 포인트 축소 |
