---
description: Step 완료 → Phase docs 업데이트 → Git commit (project-overall은 명시 요청 시만)
argument-hint: phase-name step-number [--sync-status] (예: "phase1-mvp 1.3" 또는 "phase2-graph 2.1 --sync-status")
---

# 단계 업데이트 (Step Update)

**Task:** $ARGUMENTS

## Overview

개발 단계(step) 완료 시 실행. Phase 문서를 업데이트한 뒤 커밋.

> **Note:** project-overall 3파일(`project-plan.md`, `project-context.md`, `project-tasks.md`) 동기화는 `--sync-status` 플래그가 있거나 사용자가 명시적으로 요청할 때만 수행.

```
Phase docs 업데이트 → Git Commit (+ project-overall 동기화는 선택적)
```

---

## Instructions

### 1. 인자 파싱 (Parse Arguments)

입력 형식: `[phase-name] [step-id] [--sync-status]`

예시:
- `phase1-mvp 1.3` → Phase 1, Step 3
- `phase2-graph 2.1 --sync-status` → Phase 2, Step 1 + project-status 동기화

### 2. 현재 상태 확인 (Check Current State)

읽어야 할 파일:
```
docs/phases/[phase-name]/tasks.md
docs/phases/[phase-name]/context.md
docs/phases/[phase-name]/plan.md
docs/phases/[phase-name]/design-notes.md
docs/session-compact.md
```

`--sync-status` 플래그 있을 때 추가로 읽기:
```
docs/project-plan.md
docs/project-context.md
docs/project-tasks.md
```

확인 사항:
- [ ] Phase dev-docs 파일 존재 여부 (없으면 `/dev-docs` 먼저 실행 안내)
- [ ] 현재 브랜치, 커밋되지 않은 변경사항
- [ ] 완료된 step의 실제 코드 변경 내역 (`git diff --stat`)

### 3. Phase Dev-Docs 업데이트

#### 3.1 `tasks.md`
- 완료된 step 체크: `- [ ]` → `- [x]` + commit hash
- Progress 카운터 갱신 (예: `3/14 (21%)`)
```markdown
- [x] 1.3 SQLite DDL + ChromaDB 컬렉션 설정 `[M]` — `abc1234`
```

#### 3.2 `context.md`
- 변경/생성된 파일 목록 추가
- 새 결정사항 추가 (있을 경우)
```markdown
## Changed Files (Step 1.3)
- `src/db/models.py` — SQLite 스키마 + CRUD 구현
- `src/db/vectors.py` — ChromaDB 래퍼 구현
```

#### 3.3 `design-notes.md`
- 해당 step에서 발생한 설계 이슈/디버깅 이력 추가
- 간단한 메모: 테이블 row 추가
- 심층 분석: `### X.Y-N: [Issue Title]` 서브섹션으로 증상/원인/수정 상세 기록
- Modified Files Summary 섹션 갱신 (변경 파일 트리)
- Lessons Learned 섹션에 재사용 가능한 교훈 추가
- 설계 이슈/디버깅 없는 step이면 이 섹션 스킵

#### 3.4 `plan.md`
- Last Updated 날짜 갱신
- Status / Current Step 갱신
- Current State 섹션에 완료 항목 추가

### 4. project-overall 동기화 (--sync-status 플래그 또는 명시 요청 시에만)

> **SKIP** 이 섹션은 `--sync-status` 플래그가 없고 사용자가 요청하지 않았으면 건너뛴다.

#### 4.1 `docs/project-tasks.md` (항상 업데이트)
- 해당 Phase 진행률 갱신
- Key Decisions 테이블에 새 결정 추가

#### 4.2 `docs/project-context.md` (새 결정사항 있을 때만)
- 공통 스키마/스택/컨벤션 변경 반영

#### 4.3 `docs/project-plan.md` (Phase 상태 변경 시만)
- Phase 상태 업데이트 (Planning → In Progress 등)
- Phase 간 의존성 변경 반영

### 5. session-compact.md 업데이트

- Remaining/TODO 해당 항목 진행 상태 반영
- Phase 마지막 step 완료 시: Phase 자체를 `[x]` 완료 처리

### 6. 정합성 검증 (Consistency Check)

업데이트 후 아래를 검증:
- [ ] session-compact.md의 TODO가 실제 진행률과 일치
- [ ] tasks.md의 체크 상태가 실제 산출물과 일치

`--sync-status` 시 추가 검증:
- [ ] Phase tasks.md 진행률 == project-tasks.md 해당 Phase 설명

### 7. Git Commit

#### 7.1 Staging
```bash
# 코드 변경 + 문서 변경 포함
git add src/                            # 해당 Phase 코드 (변경된 파일)
git add docs/phases/[phase-name]/       # Phase dev-docs
git add docs/session-compact.md         # session-compact (변경 시)
# --sync-status 시에만:
# git add docs/project-plan.md
# git add docs/project-context.md
# git add docs/project-tasks.md
```

#### 7.2 Commit Message 형식
```
[phase-name] Step X.Y: 간단한 설명

- 주요 변경 1
- 주요 변경 2

Refs: docs/phases/[phase-name]/tasks.md
```

#### 7.3 Phase 완료 시 추가 작업
Phase 마지막 step 완료 시:
- Phase plan.md Status → `Complete`
- Phase tasks.md Progress → `N/N (100%)`
- project-plan.md 해당 Phase Status → `Complete`
- project-tasks.md 해당 Phase Progress → `Complete`
- session-compact.md 해당 Phase `[x]` 체크
- masterplan-v2.0.md §14 완료 기준과 대조하여 실제 달성 여부 확인

### 8. Git Push & Remote 정합성 확인 (CRITICAL — 반드시 수행)

#### 8.1 Push
```bash
git push origin [branch-name]
```
- Push 실패 시: 에러 메시지 출력 후 원인 분석 (remote 변경, 인증 등)
- `rejected` 에러 시: `git pull --rebase` 후 재시도 (force push 절대 금지)

#### 8.2 Local ↔ Remote 정합성 확인
Push 완료 후 반드시 확인:
```bash
git fetch origin
git log --oneline HEAD..origin/[branch-name]   # remote에만 있는 커밋 (0이어야 함)
git log --oneline origin/[branch-name]..HEAD   # local에만 있는 커밋 (0이어야 함)
```

검증 기준:
- [ ] 두 명령 모두 **빈 결과**여야 정합 (local == remote)
- [ ] 차이가 있으면 경고 출력 + 수동 확인 요청

#### 8.3 Push 결과 요약
```
Push: origin/[branch-name] ← [commit-hash]
Remote 정합: ✅ local == remote (동일)
```

---

## Output Format

```
Step Update 완료

Task: [phase-name]
Step: X.Y — [Step Name]

Phase docs 업데이트:
- tasks.md: Step X.Y 완료 체크 (N/M, P%)
- context.md: N개 파일/결정사항 추가
- plan.md: 상태 업데이트
- design-notes.md: N개 설계 노트/디버깅 이력 추가 (없으면 스킵)

project-overall 동기화: (--sync-status 시에만)
- project-tasks.md: 진행률 갱신, 결정사항 반영
- project-context.md: 스택/컨벤션 변경 (해당 시)
- project-plan.md: Phase 상태 변경 (해당 시)

Git:
- Commit: [hash] [message]
- Push: origin/[branch] ← [hash]
- Remote 정합: ✅ local == remote

전체 진행률: Phase X/Y steps (N%)
```

---

## Error Handling

| 상황 | 대응 |
|------|------|
| Phase dev-docs 없음 | `/dev-docs` 먼저 실행 안내 |
| project-overall 파일 없음 | 경고 후 Phase docs만 업데이트 |
| 커밋할 변경 없음 | 문서만 업데이트 후 커밋 스킵 |
| tasks.md 불일치 | 경고 메시지 출력 + 수동 확인 요청 |
| Phase 완료 감지 | 자동으로 완료 처리 + 다음 Phase 안내 |
