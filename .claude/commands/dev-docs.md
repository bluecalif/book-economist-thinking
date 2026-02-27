---
description: Phase dev-docs 생성 + project-overall 동기화
argument-hint: 계획할 내용 (예: "phase1-mvp", "phase2-graph", "phase3-scale")
---

# 개발 문서 생성 (Dev Docs Generator)

**Task:** $ARGUMENTS

## Instructions

### 1. 요청 분석 (Analyze Request)

- 대상 Phase의 범위(scope)와 영향도(impact) 파악
- 관련 레이어 식별: L0 Raw, L1 KU, L2 Graph, L3 Generation, L4 Evolution
- 기존 설계 문서와의 연관성 확인

### 2. 관련 문서 검토 (Review Existing Docs) — 반드시 모두 읽기

**프로젝트 전체 (필수):**
- `docs/masterplan-v2.0.md` — 마스터플랜 (아키텍처, 레이어 구조, CLI, 로드맵)
- `docs/session-compact.md` — 현재 진행 상태
- `docs/project-plan.md` — 전체 Phase 로드맵 및 의존성
- `docs/project-context.md` — 공통 스키마, 스택, 컨벤션
- `docs/project-tasks.md` — 전체 Phase 진행률 및 결정사항

**해당 Phase (존재 시):**
- `docs/phases/[phase-name]/plan.md`
- `docs/phases/[phase-name]/context.md`
- `docs/phases/[phase-name]/tasks.md`

### 3. Phase Dev-Docs 생성 (Generate Phase Files)

**위치:** `docs/phases/[phase-name]/`

| 파일 | 용도 |
|------|------|
| `plan.md` | 종합 계획 (Summary, Current State, Target State, Stages, Tasks, Risks, Dependencies) |
| `context.md` | 핵심 파일, 결정사항, 데이터 스키마, 컨벤션 체크 |
| `tasks.md` | 체크리스트 형식 진행 추적 |
| `design-notes.md` | 설계 노트 및 이슈 (대안, 트레이드오프, 열린 질문, 디버깅 이력) |

**파일 헤더:**
```markdown
# [Phase Name]
> Last Updated: YYYY-MM-DD
> Status: Planning | In Progress | Review | Complete
```

**plan.md 필수 섹션:**
```
1. Summary (개요) — 목적, 범위, 예상 산출물
2. Current State (현재 상태) — 이전 Phase에서 넘어온 것
3. Target State (목표 상태) — 완료 후 기대 상태 (masterplan §14 완료 기준 참조)
4. Implementation Stages — Stage A, B... 순차 단계
5. Task Breakdown — 태스크 테이블 (Size: S/M/L/XL, 의존성)
6. Risks & Mitigation
7. Dependencies — 내부(다른 레이어) + 외부(라이브러리, API)
```

**design-notes.md 필수 섹션:**
```markdown
# [Phase Name] Design Notes
> Last Updated: YYYY-MM-DD

## Step X.Y: [Step Name]

### 설계 대안 (Alternatives Considered)
| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|

### 디버깅 이력 (Debug History)
| Bug # | Module | Issue | Fix | File |
|-------|--------|-------|-----|------|

### X.Y-N: [Bug/Issue Title] (심층 분석 시)
- **증상**: 에러 메시지 또는 관찰된 동작
- **원인**: 근본 원인 분석
- **수정**: 변경 내용 + 파일 경로

### 열린 질문 (Open Questions)
- [ ] 질문 — 배경, 영향 범위

### 교훈 (Lessons Learned)
- 패턴, 설계 원칙, 재사용 가능한 인사이트

## Modified Files Summary
(Phase 전체 변경 파일 트리)
```

**context.md 필수 섹션:**
```
1. 핵심 파일 — 이 Phase에서 참조/수정할 소스 파일 경로
2. 데이터 스키마 — 입력/출력 데이터 구조 (masterplan §4-7 참조)
3. 주요 결정사항 — 설계 선택, 트레이드오프
4. 컨벤션 체크리스트 — 해당 Phase에 적용되는 규칙
```

### 4. project-overall 동기화 (CRITICAL — 반드시 수행)

Phase dev-docs 생성 후, project-overall 3파일을 **반드시** 업데이트 (없으면 새로 생성):

#### 4.1 `docs/project-plan.md`
- 해당 Phase 섹션 추가/갱신
- Phase 간 의존성 반영
- 전체 로드맵 타임라인 업데이트

필수 섹션:
```markdown
# Project Plan
> Last Updated: YYYY-MM-DD

## Roadmap Overview
## Phase 1: [Name] — Status
## Phase 2: [Name] — Status
...
## Phase Dependencies
## Timeline
```

#### 4.2 `docs/project-context.md`
- 공통 스키마/스택/컨벤션 변경 반영
- 새 Phase에서 도입하는 기술 스택 추가

필수 섹션:
```markdown
# Project Context
> Last Updated: YYYY-MM-DD

## Tech Stack
## Data Schema
## Conventions
## Shared Dependencies
```

#### 4.3 `docs/project-tasks.md`
- 전체 진행률 업데이트
- Key Decisions 테이블에 새 결정 추가

필수 섹션:
```markdown
# Project Tasks
> Last Updated: YYYY-MM-DD

## Overall Progress
## Phase Progress Summary
| Phase | Status | Progress | Current Step |
## Key Decisions
| # | Decision | Phase | Date | Rationale |
```

### 5. 정합성 검증 (Consistency Check)

생성 완료 후 아래를 검증:
- [ ] Phase tasks.md 태스크 목록이 plan.md의 Stage 구조와 매칭
- [ ] masterplan-v2.0.md의 해당 레이어/Phase 설명과 plan.md 범위 일치
- [ ] context.md의 데이터 스키마가 masterplan §4-7과 일치
- [ ] session-compact.md의 Remaining/TODO가 최신 상태
- [ ] project-tasks.md 진행률이 Phase tasks.md와 일치
- [ ] project-plan.md Phase 의존성이 실제 구조와 일치
- [ ] project-context.md 스택/스키마가 masterplan과 일치

### 6. 컨벤션 체크 (Convention Checklist)

**아키텍처 (masterplan §3):**
- 레이어 구조: L0 Raw → L1 KU → L2 Graph → L3 Generation → L4 Evolution
- CLI 명령어: ks ingest, search, explore, generate, crawl, sync, stats, export

**지식 구조 (masterplan §5):**
- KU 포맷: claim + evidence_summary + counter_summary
- KU ID 패턴: `ku-{domain}-{book_seq}-{ku_seq}`
- Maturity: M0 (자동추출) → M1 (수동검토) → M2 (외부보강)

**데이터 (masterplan §4-7):**
- 5개 테이블: books, raw_spans, knowledge_units, edges, generations
- ChromaDB: ku_embeddings 컬렉션
- Edge 6타입: explains, supports, contradicts, extends, example_of, analogous_to

**인코딩:**
- utf-8-sig (read), utf-8 (write), PYTHONUTF8=1

### 7. Git 커밋 (Commit Phase Docs)

설계 문서 생성 + project-overall 동기화 완료 후:

1. `git add` — 생성/수정된 파일만 개별 지정
   ```
   docs/phases/[phase-name]/plan.md
   docs/phases/[phase-name]/context.md
   docs/phases/[phase-name]/tasks.md
   docs/phases/[phase-name]/design-notes.md
   docs/project-plan.md    (수정된 경우)
   docs/project-context.md (수정된 경우)
   docs/project-tasks.md   (수정된 경우)
   docs/session-compact.md (수정된 경우)
   ```
2. `git commit` — 메시지 형식:
   ```
   docs: [phase-name] 설계 문서 생성

   - plan.md: N개 Stage, M개 Task
   - context.md: 핵심 파일/스키마/결정사항
   - tasks.md: 체크리스트 초기화
   - design-notes.md: 초기 설계 노트
   ```
3. 커밋 전 `git status`로 의도하지 않은 파일이 포함되지 않았는지 확인
4. push는 하지 않음 (사용자가 명시적으로 요청할 때만)

---

## Output Format

```
생성 완료

Phase dev-docs:
docs/phases/[phase-name]/
├── plan.md          (종합 계획)
├── context.md       (컨텍스트)
├── tasks.md         (태스크 추적)
└── design-notes.md  (설계 노트/이슈)

project-overall 동기화: 완료
- project-plan.md: Phase 섹션/의존성
- project-context.md: 스택/스키마/컨벤션
- project-tasks.md: 진행률/결정사항

Git:
- commit: [hash] "docs: [phase-name] 설계 문서 생성"

요약:
- Stages: N개
- Tasks: N개 (S: n, M: n, L: n, XL: n)
- 정합성 검증: PASS / FAIL (상세)
```
