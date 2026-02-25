---
name: generation-dev
description: L3 생성 파이프라인 가이드. 콘텐츠 생성(blog, thread, newsletter, lecture, summary) 5포맷, 아이디어 생성(business, content, serendipity) 3모드, 토픽→KU검색→컨텍스트→프롬프트→출력 파이프라인, 출처 KU ID 필수 첨부, generations 테이블 기록. 콘텐츠 생성, 아이디어 생성, 생성 파이프라인 작업 시 자동 활성화.
---

# Generation Pipeline Guide

## 목적

L3 생성 레이어(콘텐츠 + 아이디어)의 파이프라인 설계 및 구현 가이드.

## 사용 시점

- 생성 파이프라인 코드 작성/수정
- 프롬프트 템플릿 설계
- 생성 CLI 명령어 구현
- 생성 품질 관리 로직

---

## 생성 파이프라인 (공통)

```
1. 토픽/KU 지정
2. 관련 KU 검색 (Vector Search + Graph 1-hop)
3. KU 컨텍스트 조합 (claim + evidence + 관련 KU)
4. 프롬프트 템플릿 적용
5. LLM 호출 → 초안 생성
6. 출력 저장 (마크다운 + 사용된 KU ID 기록)
```

### 핵심 규칙

- **출처 KU ID 필수**: 생성 결과에 항상 사용된 KU ID 목록 첨부
- **generations 테이블 기록**: 모든 생성을 DB에 기록 (추적 + maturity 승격 입력)
- **ku_ids 필드**: 사용된 KU ID를 JSON array로 저장

---

## 콘텐츠 생성 (Content Generation)

### CLI 사용 예

```bash
ks generate content --topic "매몰비용" --format blog --depth deep
ks generate content --topic "게임이론의 실생활 적용" --format thread
ks generate content --ku ku-econ-001-0042,ku-mgmt-003-0015 --format newsletter
```

### 5가지 포맷

| 포맷 | 설명 | 예상 길이 |
|------|------|----------|
| `blog` | 블로그 포스트 | 1,500-3,000자 |
| `thread` | 소셜미디어 스레드 | 5-10개 항목 |
| `newsletter` | 뉴스레터 섹션 | 500-1,000자 |
| `lecture` | 강의 노트 | 2,000-5,000자 |
| `summary` | 개념 요약 | 300-500자 |

### 포맷별 특성

- **blog**: 서론-본론-결론 구조, 독자 친화적 톤
- **thread**: 번호 매기기, 각 항목 독립적, 훅 문장 시작
- **newsletter**: 핵심 요약 + "더 알아보기" 형태
- **lecture**: 학습 목표 → 설명 → 예시 → 정리
- **summary**: 3-5개 핵심 포인트, 간결하게

---

## 아이디어 생성 (Idea Generation)

### CLI 사용 예

```bash
ks generate idea --mode business --domains 경제,기술
ks generate idea --mode content --ku ku-hist-005-0023 --cross-domain
ks generate idea --mode serendipity  # 랜덤 cross-domain 조합
```

### 3가지 모드

| 모드 | 설명 | 입력 |
|------|------|------|
| `business` | 비즈니스 모델/서비스 아이디어 | 도메인 쌍 또는 KU |
| `content` | 콘텐츠 시리즈/주제 기획 | KU + cross-domain 옵션 |
| `serendipity` | 랜덤 cross-domain 조합에서 발견 | 없음 (랜덤) |

### 아이디어 파이프라인

```
1. 도메인/KU 선택 (또는 랜덤)
2. Cross-domain KU 쌍 탐색 (Graph traversal + analogous_to edges)
3. 교차점 분석 프롬프트 → LLM 호출
4. 아이디어 후보 생성
5. 출력 저장 + 사용된 KU 역참조 기록
```

---

## 프롬프트 템플릿 설계 원칙

1. **KU 컨텍스트 포함**: claim + evidence를 프롬프트에 직접 삽입
2. **포맷 지시**: 원하는 출력 형식을 명확히 지정
3. **출처 표기 지시**: "사용한 지식 단위의 ID를 말미에 기록하세요"
4. **톤 지정**: 포맷에 맞는 톤/문체 지시
5. **길이 제한**: 포맷별 예상 길이 범위 명시

### 템플릿 위치

`src/generation/templates/` 디렉터리에 포맷별 `.txt` 또는 `.jinja2` 파일

---

## 품질 관리

### 생성 결과 저장

```python
# generations 테이블에 항상 기록
{
    "mode": "content",       # content|idea
    "format": "blog",        # 포맷 (content일 때)
    "prompt": "사용된 프롬프트",
    "output": "생성 결과",
    "ku_ids": ["ku-econ-001-0042", "ku-econ-001-0038"],
    "rating": None           # 나중에 사용자 평가
}
```

### Maturity 연동

- 생성에 3회 이상 사용 + 평균 rating >= 2 → M0 → M1 후보 제안
- 이 로직은 `evolution/` 모듈에서 처리

---

## 체크리스트

생성 관련 코드 작성 시:

- [ ] 생성 결과에 KU ID 목록이 첨부되는가?
- [ ] generations 테이블에 기록되는가?
- [ ] ku_ids가 JSON array 형태인가?
- [ ] 포맷이 5종 중 하나인가? (content mode)
- [ ] 모드가 3종 중 하나인가? (idea mode)
- [ ] 프롬프트 템플릿이 templates/ 디렉터리에 있는가?

---

## 관련 파일

- `src/generation/content.py` — 콘텐츠 생성 파이프라인
- `src/generation/idea.py` — 아이디어 생성 파이프라인
- `src/generation/templates/` — 프롬프트 템플릿
- `src/db/models.py` — generations 테이블
- `docs/masterplan-v2.0.md` §7 — L3 상세 설계
