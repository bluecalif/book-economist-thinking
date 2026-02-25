---
description: Step 완료 → Phase 설계 문서 업데이트 + 정합성 검증
argument-hint: phase-name step-number [--sync-status] (예: "phase1-mvp 1.3" 또는 "phase2-graph 2.1 --sync-status")
---

# 진행 업데이트 (Progress Update)

**Task:** $ARGUMENTS

## Overview

설계/구현 단계(step) 완료 시 실행. Phase 문서를 업데이트하고 정합성을 검증.

> **Note:** `docs/project-status.md` 동기화는 `--sync-status` 플래그가 있거나 사용자가 명시적으로 요청할 때만 수행.

```
Phase docs 업데이트 → 정합성 검증 (+ project-status 동기화는 선택적)
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

`--sync-status` 플래그 있을 때 추가:
```
docs/project-status.md
```

확인 사항:
- [ ] Phase 설계 문서 파일 존재 여부 (없으면 `/design-docs` 먼저 실행 안내)
- [ ] 완료된 step의 실제 산출물 변경 내역

### 3. Phase 설계 문서 업데이트

#### 3.1 `tasks.md`
- 완료된 step 체크: `- [ ]` → `- [x]`
- Progress 카운터 갱신 (예: `3/14 (21%)`)
```markdown
- [x] 1.3 SQLite DDL + ChromaDB 컬렉션 설정 `[M]`
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
- 해당 step에서 발생한 설계 이슈/대안 분석 추가
- 간단한 메모: 테이블 row 추가
- 심층 분석: `### X.Y-N: [Issue Title]` 서브섹션으로 상세 기록
- 설계 이슈 없는 step이면 이 섹션 스킵

#### 3.4 `plan.md`
- Last Updated 날짜 갱신
- Status / Current Step 갱신
- Current State 섹션에 완료 항목 추가

### 4. project-status.md 동기화 (--sync-status 또는 명시 요청 시에만)

> **SKIP** `--sync-status` 플래그가 없고 사용자가 요청하지 않았으면 건너뛴다.

- 해당 Phase 진행률 갱신
- Key Decisions 테이블에 새 결정 추가
- Phase 상태 업데이트 (Planning → In Progress 등)

### 5. Git 커밋 (Commit Progress)

Phase 문서 업데이트 완료 후:

1. `git add` — 수정된 파일만 개별 지정
   ```
   docs/phases/[phase-name]/tasks.md
   docs/phases/[phase-name]/context.md
   docs/phases/[phase-name]/plan.md
   docs/phases/[phase-name]/design-notes.md  (수정된 경우)
   docs/project-status.md                    (--sync-status 시)
   docs/session-compact.md                   (수정된 경우)
   ```
2. `git commit` — 메시지 형식:
   ```
   docs: [phase-name] step X.Y 완료 — [step 이름 요약]

   - tasks.md: N/M (P%)
   - context.md: N개 파일 추가
   [선택] - design-notes.md: 설계 노트 추가
   ```
3. Phase 완료 시 커밋 메시지:
   ```
   docs: [phase-name] 완료 (N/N, 100%)

   masterplan §14 완료 기준 달성 확인
   ```
4. 커밋 전 `git status`로 의도하지 않은 파일이 포함되지 않았는지 확인
5. push는 하지 않음 (사용자가 명시적으로 요청할 때만)

### 6. session-compact.md 업데이트

- Remaining/TODO 해당 항목 진행 상태 반영
- Phase 마지막 step 완료 시: Phase 자체를 `[x]` 완료 처리

### 7. 정합성 검증 (Consistency Check)

업데이트 후 검증:
- [ ] git commit 성공 여부
- [ ] session-compact.md의 TODO가 실제 진행률과 일치
- [ ] tasks.md의 체크 상태가 실제 산출물과 일치

`--sync-status` 시 추가 검증:
- [ ] Phase tasks.md 진행률 == project-status.md 해당 Phase 설명

### 8. Phase 완료 시 추가 작업

Phase 마지막 step 완료 시:
- Phase plan.md Status → `Complete`
- Phase tasks.md Progress → `N/N (100%)`
- project-status.md 해당 Phase Status → `Complete`
- session-compact.md 해당 Phase `[x]` 체크
- masterplan-v2.0.md §14 완료 기준과 대조하여 실제 달성 여부 확인

---

## Output Format

```
Progress Update 완료

Task: [phase-name]
Step: X.Y — [Step Name]

Phase docs 업데이트:
- tasks.md: Step X.Y 완료 체크 (N/M, P%)
- context.md: N개 파일/결정사항 추가
- plan.md: 상태 업데이트
- design-notes.md: N개 설계 노트 추가 (없으면 스킵)

Git:
- commit: [commit hash] "docs: [phase-name] step X.Y 완료 — [요약]"

project-status 동기화: (--sync-status 시에만)
- 진행률 갱신
- 결정사항 반영

정합성 검증: PASS / FAIL (상세)

전체 진행률: Phase X/Y steps (N%)
```

---

## Error Handling

| 상황 | 대응 |
|------|------|
| Phase 설계 문서 없음 | `/design-docs` 먼저 실행 안내 |
| project-status.md 없음 | 경고 후 Phase docs만 업데이트 |
| 업데이트할 변경 없음 | 문서만 업데이트 |
| tasks.md 불일치 | 경고 메시지 출력 + 수동 확인 요청 |
| Phase 완료 감지 | 자동으로 완료 처리 + 다음 Phase 안내 |
