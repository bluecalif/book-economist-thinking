---
description: claude code에서 프로젝트 시작시 사전 준비(또는 Phase 0) 순서
argument-hint: 프로젝트 사전 준비 (예: "project start", "scratch")
---

## 사전 준비 (또는 Phase 0) 순서

### 0. Github 확인

- Github address 생성 및 CC에 알려주기

### 1. 플랜 review

- 마스터플랜 리뷰: `docs/masterplan-XX.md` 리뷰
- 상세 Context 리뷰: `docs/` 아래 `context-XX.md`, `plan-XX.md`, `detail-XX.md`, `guide-XX.md` 리뷰

### 2. CLAUDE.md 생성 확인

- Reference 확인: `@Projects-2026\archive\REF-CLAUDE.md`
- general instruction: reference의 내용 확인후 필요시 수정
- project-specific instruction: 마스터 플랜을 바탕으로 생성

### 3. commands 생성 확인

- Reference 확인: `@Projects-2026\archive\REF-commands\*`
- reference 파일 복사 -> 프로젝트에 맞게 수정 -> `.claude\commands\` 저장

### 4. hooks 생성 확인

- Reference 확인: `@Projects-2026\archive\REF-hooks\*`
- reference 파일 복사 -> 프로젝트에 맞게 수정 -> `.claude\hooks\` 저장
  
### 5. skills 생성 확인

- Reference 확인: `@Projects-2026\archive\REF-skills\*`
- reference 파일 복사 -> 프로젝트에 맞게 수정 -> `.claude\skills\` 저장

### 6. plan 검토

- plan 모드 대화: plan에 충분히 검토되었는지 확인하고, 없으면 생성하기
- 주요 포인트: plan의 충분한 검토 여부. tiki-taka

### 7. dev-docs 구현

- 전체 project 구현: project-overall에 대한 dev-docs 실시. overall후 phase 1으로 넘어감을 agent에 설명
- **Phase 0**: project-overall은 rough한 상태. 따라서 phase 0에서 실제 구현인 phase 1으로 들어가기전, 모든 계약 사항을 설계, 설정, 확인하는 phase를 명시적으로 생성
- Phase 1 구현: project-overall에 대한 dev-docs 실시

### 8. Phase 1부터 시작

- Initialization: Phase 0에 대한 실행 확인. Phase 1의 실행 가능 여부 확인 (또는 plan 및 context 존재여부 확인)
- Instruction 가이드: 
- Step-Update: 매 step이 완료시 step-update로 git update 및 dev docs update

### 9. Audit

- 각 Phase 완료전, `re-consider this phase original goal in terms of total project context. Are there any missing parts? If not satisfactory, show me the better plan`을 질문할 것
- 이를 통해 부족한 부분에 대한 개선 plan 생성 및 이를 실행 

## 주의 사항

- **Clear**: 매과제가 실시완료(step 완료가 아님) 되면 반드시 **Clear** 실시
- **Compact**: 매과제가 길어지면 반드시 **Compact** 실시. Every 5 mins ?    
- Phase안에서 Phase **자기완결성**을 반드시 확보할 것
- temporary 이력 문서: CC 작업중 rate limit 넘어갈시 마지막 상태 compact한 것 기록. 파일명은 `temp_compact.md`




