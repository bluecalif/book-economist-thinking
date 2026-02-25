---
name: skill-developer
description: Claude Code 스킬 생성 및 관리 가이드. 새 스킬 추가, skill-rules.json 수정, 트리거 패턴 설계, hook 메커니즘 이해, 스킬 활성화 디버깅 시 사용. 키워드 트리거, intent 패턴, enforcement 레벨(block, suggest, warn), UserPromptSubmit hook, 500라인 규칙.
---

# Skill Developer Guide

## 목적

이 프로젝트의 스킬 시스템을 생성하고 관리하기 위한 가이드.

## 사용 시점

- 새 스킬 생성/추가
- skill-rules.json 수정
- 트리거 패턴 설계/디버깅
- hook 시스템 문제 해결

---

## 아키텍처

```
.claude/
├── hooks/
│   ├── skill-activation-prompt.ps1   # PowerShell wrapper
│   └── skill-activation-prompt.ts    # 메인 로직
└── skills/
    ├── skill-rules.json              # 스킬 정의 (마스터 설정)
    └── {skill-name}/
        └── SKILL.md                  # 스킬 콘텐츠
```

### Hook 동작 흐름

```
User Prompt → PowerShell Wrapper → TypeScript Hook
                                        ↓
                              skill-rules.json 로드
                                        ↓
                              키워드/패턴 매칭
                                        ↓
                              매칭된 스킬 출력 (stdout → Claude)
```

### 현재 스킬 (4개)

| 스킬 | 타입 | 적용 | 우선순위 |
|------|------|------|----------|
| ku-pipeline | guardrail | warn | critical |
| db-schema | guardrail | warn | critical |
| generation-dev | domain | suggest | high |
| skill-developer | domain | suggest | medium |

---

## 새 스킬 생성 (Quick Start)

### Step 1: SKILL.md 생성

**위치:** `.claude/skills/{skill-name}/SKILL.md`

```markdown
---
name: my-skill-name
description: 설명. 트리거 키워드 포함. 최대 1024자.
---

# 스킬 이름

## 목적 / ## 사용 시점 / ## 핵심 정보
```

**규칙:**
- 이름: 소문자, 하이픈 구분
- 설명: 모든 트리거 키워드 포함 (한글+영문)
- 내용: **500라인 미만**
- 예시: 실제 코드 예시 포함

### Step 2: skill-rules.json에 추가

```json
{
  "my-skill-name": {
    "type": "domain",
    "enforcement": "suggest",
    "priority": "medium",
    "promptTriggers": {
      "keywords": ["키워드1", "keyword2"],
      "intentPatterns": ["(생성|추가).*무엇"]
    }
  }
}
```

### Step 3: 테스트

```bash
echo '{"session_id":"test","prompt":"테스트 키워드1"}' | \
  npx tsx .claude/hooks/skill-activation-prompt.ts
```

---

## 스킬 타입

| 타입 | 목적 | enforcement | priority |
|------|------|-------------|----------|
| guardrail | 핵심 규칙 강제 | warn/block | critical/high |
| domain | 영역 가이드 제공 | suggest | high/medium |

## Enforcement 레벨

- **block**: Edit/Write 차단. exit code 2. 치명적 실수 방지
- **suggest**: 리마인더 주입. 권장사항 (가장 일반적)
- **warn**: 낮은 우선순위 제안

## 트리거 타입

- **keywords**: 명시적 매칭 (대소문자 무시). 한글+영문 모두 포함
- **intentPatterns**: 정규식 패턴. `.*`로 유연하게 매칭

---

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| 스킬 트리거 안됨 | JSON 문법 오류 | `jq . skill-rules.json`으로 검증 |
| 스킬 트리거 안됨 | 키워드 누락 | 프롬프트에 키워드 포함 여부 확인 |
| Hook 실행 안됨 | settings.local.json 미등록 | hooks 섹션 확인 |
| Hook 실행 안됨 | npx tsx 미설치 | `npx tsx --version` 확인 |
| False positive | 키워드 너무 일반적 | 더 구체적 키워드로 변경 |

---

## 관련 파일

- `.claude/skills/skill-rules.json` — 마스터 설정
- `.claude/hooks/skill-activation-prompt.ts` — 메인 로직
- `.claude/hooks/skill-activation-prompt.ps1` — Windows wrapper
- `.claude/settings.local.json` — Hook 등록
