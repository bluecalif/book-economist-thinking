# Project Tasks
> Last Updated: 2026-02-27

## Overall Progress

| 항목 | 값 |
|------|---|
| 전체 Phase | 4개 (Phase 4는 조건부) |
| 완료 Phase | 0 |
| 현재 Phase | Phase 1 — 1권 MVP |
| 현재 Stage | Stage A (프로젝트 초기화) 대기 |

---

## Phase Progress Summary

| Phase | Status | Progress | Current Step | 비고 |
|-------|--------|----------|--------------|------|
| Phase 1: 1권 MVP | In Progress | 0/7 Stages | Stage A 대기 | dev-docs 생성 완료, 실행 시작 전 |
| Phase 2: 그래프+5권 | Planned | - | - | Phase 1 완료 후 |
| Phase 3: 87권+진화 | Planned | - | - | Phase 2 완료 후 |
| Phase 4: 웹 UI | Conditional | - | - | 가치 검증 통과 시 |

---

## Phase 1 Tasks

### Stage A: 프로젝트 초기화 (S)
- [ ] A.1 `pyproject.toml` 생성 (의존성 정의)
- [ ] A.2 `src/` 디렉터리 구조 생성 (`__init__.py` 포함)
- [ ] A.3 `data/`, `vault/` 디렉터리 생성
- [ ] A.4 `config.yaml` 기본 설정 파일
- [ ] A.5 의존성 설치 확인

### Stage B: DB 스키마 (M)
- [ ] B.1 SQLite DDL — 5개 테이블 생성
- [ ] B.2 CRUD 헬퍼 함수 (`src/db/models.py`)
- [ ] B.3 ChromaDB 래퍼 (`src/db/vectors.py`)
- [ ] B.4 DB 초기화 스크립트

### Stage C: PDF 파싱 (M)
- [ ] C.1 기존 JSON 구조 분석 (structure.json, text.json)
- [ ] C.2 JSON → raw_spans 변환 로직 (`src/ingest/pdf_parser.py`)
- [ ] C.3 raw_spans DB 저장 + 검증
- [ ] C.4 PDF 직접 파싱 보조 경로 (PyMuPDF)

### Stage D: KU 추출 (L)
- [ ] D.1 KU 추출 프롬프트 설계 + 테스트
- [ ] D.2 `src/ingest/ku_extractor.py` 구현
- [ ] D.3 KU DB 저장 + source_spans 매핑
- [ ] D.4 임베딩 생성 + ChromaDB 저장
- [ ] D.5 프롬프트 최적화 (품질 검증 반복)

### Stage E: 의미 검색 (S)
- [ ] E.1 `src/search/vector.py` 구현
- [ ] E.2 검색 결과 포매팅 (claim, domain, confidence 표시)
- [ ] E.3 도메인 필터링

### Stage F: 콘텐츠 생성 (M)
- [ ] F.1 `src/generation/content.py` 파이프라인
- [ ] F.2 프롬프트 템플릿 3종 (blog, summary, thread)
- [ ] F.3 출처 KU ID 첨부 로직
- [ ] F.4 generations 테이블 기록

### Stage G: CLI + 통합 (L)
- [ ] G.1 `src/cli.py` — ingest, search, generate 명령어
- [ ] G.2 `src/vault/renderer.py` — KU 마크다운 렌더링
- [ ] G.3 통합 테스트 (전체 파이프라인)
- [ ] G.4 완료 기준 4항목 검증

---

## Key Decisions

| # | Decision | Phase | Date | Rationale |
|---|----------|-------|------|-----------|
| 1 | Raw SQL + 헬퍼 함수 (ORM 미사용) | Phase 1 | 2026-02-25 | 단순성 우선, 테이블 5개로 ORM 불필요 |
| 2 | 기존 JSON 우선 경로 | Phase 1 | 2026-02-25 | PDF 직접 파싱보다 기존 파싱 데이터 먼저 활용 |
| 3 | edges 테이블 DDL만 Phase 1 | Phase 1 | 2026-02-25 | DDL 생성만, 실제 사용은 Phase 2 |
| 4 | GPT-4o mini 우선 | Phase 1 | 2026-02-25 | KU 추출 비용 절감, 필요시 업그레이드 |
| 5 | Typer CLI 유력 | Phase 1 | 2026-02-25 | 타입 힌트 기반으로 Click보다 간결, Stage G에서 최종 확정 |
| 6 | Hook: PowerShell 제거 | Infra | 2026-02-26 | PS1 5.1 한국어 인코딩 비호환 → npx tsx 직접 호출 |
| 7 | 커맨드 이름 변경 | Infra | 2026-02-27 | design-docs→dev-docs, progress-update→step-update (REF 표준) |
| 8 | project-overall 3파일 분리 | Infra | 2026-02-27 | project-status.md → project-plan/context/tasks 분리 (REF 표준) |
