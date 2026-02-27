# Phase 1: 데이터 파이프라인 — Design Notes
> Last Updated: 2026-02-27

## Stage C: JSON 파싱

### 청킹 단위 — 페이지 단위(C-1) 확정

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| C-1 | 페이지 전체를 1 raw_span으로 | 단순, JSON 구조 그대로 | 스팬이 큼 (페이지당 수백 자) | **확정** |
| C-2 | 줄바꿈 기반 문단 분리 | 의미 단위 분리 가능 | OCR 줄바꿈이 문단 경계를 보장하지 않음 | 기각 |
| C-3 | 대형 JSON (element 기반) | heading/paragraph 타입 구분 가능 | 2.2M 복잡한 구조, HTML 파싱 필요 | 보조 |

**확정 근거:**
- OCR 텍스트의 줄바꿈이 실제 문단 경계를 나타내지 않음
- 문단 분리는 D 단계 LLM에 위임하는 것이 더 정확
- 1페이지 = 1 raw_span으로 단순하게 시작
- 빈 페이지 필터: `len(text.strip()) < 10` → 제외

---

## Stage D: KU 추출

### 설계 대안 (Alternatives Considered)

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| D-1 | 페이지 1개 = 1 LLM 호출 | 단순, 컨텍스트 관리 쉬움 | 페이지 경계 KU 누락, API 호출 많음 | 기본 |
| D-2 | 2-3 페이지 묶음 | 경계 KU 보존, 호출 수 절반 | 토큰 증가, 비용 미세 증가 | 유력 |
| D-3 | 인접 페이지 오버랩 | 경계 KU 누락 최소화 | 중복 KU 발생 가능, 후처리 필요 | 보조 |

**결정 보류** — D.1에서 소수 샘플 테스트 후 최적 전략 결정.

### KU 추출 프롬프트 (초안)

```
[System] 당신은 책의 내용을 구조화된 지식 단위(Knowledge Unit)로 추출하는 전문가입니다.

[User] 다음 텍스트에서 Knowledge Unit을 추출하세요.

규칙:
1. 각 KU는 하나의 명확한 claim(주장)을 가져야 합니다
2. claim을 뒷받침하는 evidence(근거)를 원문에서 인용하세요
3. 저자가 제시한 한계나 반례가 있으면 counter로 기록하세요
4. claim이 없는 서술(배경 설명, 일화 등)은 KU로 추출하지 마세요
5. 하나의 텍스트에서 여러 KU가 나올 수 있습니다
6. 한국어로 작성하세요

출력 형식: JSON array
[{"claim": "...", "evidence_summary": "...", "counter_summary": "...", "tags": [...]}]

텍스트:
{chunk_text}
```

### D.2 LLM JSON 파싱 실패 — 3단계 fallback

```
파싱 실패 시 순서:
1. JSON repair — trailing comma 제거, 작은따옴표→큰따옴표, 불완전 JSON 수정
2. 동일 프롬프트로 1회 재시도 — LLM의 비결정적 출력 활용
3. skip + 로그 기록 — failed_spans.log에 span_id + 에러 메시지 기록
   → M1 단계에서 수동 검토 및 처리
```

### D.5 프롬프트 최적화 — 정량 종료 기준

```
종료 조건 (모두 충족 시):
  - 샘플 20페이지 추출 → claim 존재율 > 80%
  - LLM JSON 파싱 성공률 > 95%
  - 최대 2세션 이내 수렴

미달 시:
  - 현재 프롬프트로 확정, M0으로 전체 실행
  - M1 단계에서 수동 보정

측정 방법:
  - claim 존재율 = (claim이 있는 페이지 수) / (전체 샘플 페이지 수)
  - JSON 파싱 성공률 = (성공 파싱 수) / (전체 LLM 호출 수)
```

### 열린 질문 (Open Questions)
- [ ] GPT-4o mini의 한국어 claim 추출 정확도는? — D.1 테스트에서 확인
- [ ] 1페이지당 평균 KU 수는? — 예상 0.3-0.6, 실측 필요
- [ ] 중복 KU 감지/제거 전략은? — 임베딩 유사도 기반 후처리 vs 프롬프트에서 방지

---

## 디버깅 이력 (Debug History)

| Bug # | Module | Issue | Fix | File |
|-------|--------|-------|-----|------|
| (Phase 실행 시작 후 기록) | | | | |

---

## 교훈 (Lessons Learned)

(Phase 실행 중 축적)

---

## Modified Files Summary

(Phase 전체 변경 파일 트리 — 실행 시작 후 업데이트)

```
src/
├── __init__.py
├── db/
│   ├── __init__.py
│   ├── models.py
│   └── vectors.py
└── ingest/
    ├── __init__.py
    ├── pdf_parser.py
    └── ku_extractor.py
data/
├── knowledge.db
├── chroma/
└── raw/
config.yaml
pyproject.toml
```
