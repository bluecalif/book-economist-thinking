좋습니다.
지금까지의 모든 논의(초기 아키텍처 → 병목 분석 → Progressive Structuring → PR 모델 → Dispute Axis → Hybrid Search → 진화 구조 → 도메인 경계 문제)를 통합하여,

> 📘 **Knowledge Evolution Engine 설계 문서 v1.0**

로 완성 정리합니다.

---

# 📘 Knowledge Evolution Engine 설계 문서 v1.0

(FASTAPI + Next.js 기반 / Self-Correcting Knowledge System)

---

# 1. 프로젝트 목적

본 시스템은 단순 지식 저장소가 아니라 다음을 목표로 한다:

1. 다양한 형태의 콘텐츠 제작을 위한 백본
2. 지식 기반 비즈니스 아이디어 생성 엔진
3. 도메인 간 지식 연결 및 확장
4. 외부 지식 및 사용자 피드백을 반영하는 진화 구조

---

# 2. 핵심 철학

### ❌ 기존 접근

* 책 = 텍스트
* 지식 = 정적 노트
* RAG = 검색 + 요약

### ✅ 본 시스템

* 책 = 지식 마이크로서비스
* 지식 = 근거 기반 논증 단위
* 연결 = 조건부 추론 구조
* 진화 = 데이터 기반 성숙도 상승

---

# 3. 전체 아키텍처

```text
L0 Raw Layer
L1 Knowledge Unit Layer
L2 Graph Layer
L3 Dispute & Reasoning Layer
L4 Evolution Layer
```

---

# 4. L0 – Raw Text Layer (불변 계층)

## 목적

* 원본 오염 방지
* 근거 추적 가능성 확보
* 환각 방지 기반

## 저장 단위

* paragraph / sentence 단위
* 각 텍스트 span은 고유 ID 보유

## 주요 필드

* id
* document_id
* chapter
* text
* embedding
* version

---

# 5. L1 – Knowledge Unit Layer (Progressive Structuring)

## 핵심 개념: Knowledge Unit (KU)

KU는 단순 요약이 아니라 “미니 논증 단위”이다.

---

## KU 구조 v2

```json
{
  "id": "...",
  "claim": "...",
  "evidence_spans": [...],
  "counterevidence_spans": [...],
  "counter_claim_summary": "...",
  "maturity": "M0 | M1 | M2 | M3",
  "confidence": 0.42,
  "semantic_fingerprint": "...",
  "primary_domain": "...",
  "context_domains": [...],
  "domain_confidence": {
    "economics": 0.9,
    "psychology": 0.4
  }
}
```

---

## Progressive Structuring 모델

| 단계 | 설명              |
| -- | --------------- |
| M0 | claim + 근거 스팬   |
| M1 | 정의/반례 구조화       |
| M2 | edge 검증 통과      |
| M3 | 사용자/외부 지식 반영 완료 |

---

## 핵심 규칙

* counterevidence_spans 필수 필드
* 반례 없을 경우 `"checked_and_none_found": true`
* 근거 없는 claim 저장 금지
* confidence는 초기 낮게 설정

---

# 6. L2 – Semantic Graph Layer

## 목적

* 개념 간 관계 모델링
* 추론 경로 생성 기반

---

## Edge 타입 (초기 최소 세트)

* explains
* supports
* contradicts
* extends
* example_of
* applies_to
* overlaps_with

---

## Edge는 후보 → 검증 구조

```json
{
  "from_ku": "...",
  "to_ku": "...",
  "relation_type": "...",
  "source_spans": [...],
  "strength_score": 0.62,
  "status": "proposed | validated | rejected"
}
```

---

## Edge 품질 관리

* 자동 중복 검사
* 순환 검사
* 모순 밀도 계산
* 허브 과도 연결 탐지

---

# 7. L3 – Dispute Axis & Reasoning Layer

단순 충돌 나열이 아니라 조건부 추론 구조.

---

## Dispute Axis 구조

```json
{
  "axis_id": "...",
  "question": "...",
  "side_A": [...],
  "side_B": [...],
  "resolution_conditions": [
    {
      "condition": "...",
      "favor": "SideA"
    }
  ],
  "applicable_domains": [...]
}
```

---

## 기능

* 논쟁 축 관리
* 조건부 결론 생성
* 비즈니스 적용 가능성 분석

---

# 8. Hybrid Search Layer

## 2단계 검색 구조

### 1단계 – Vector Search

* L0 / L1 기반 semantic search

### 2단계 – Graph Traversal

* KU 확장
* Reasoning Path 생성

---

## Reasoning Path 점수 계산

```
PathScore =
HarmonicMean(edge_strengths)
× Mean(KU_confidence)
× (1 - contradiction_density)
```

---

## UI 표시

* 🔵 High Confidence
* 🟡 Moderate
* 🔴 Speculative

---

# 9. L4 – Evolution Layer

지식은 PR 기반으로 진화한다.

---

## Knowledge PR 모델

```json
{
  "pr_type": "edit_KU | add_edge | merge_KU | split_KU",
  "diff": "...",
  "evidence": [...],
  "impact_estimation": {...},
  "status": "open | merged | rejected"
}
```

---

## Usage-Driven Maturation

자동 승격 조건 예:

* 검색 노출 ≥ 20회
* 콘텐츠 사용 ≥ 5회
* PR 제안 ≥ 2회

→ review_queue 이동

---

# 10. 중복 및 Overlap 관리

## 자동 감지 조건

* cosine_similarity > 0.85
* claim 유사도 임계 초과

→ overlaps_with edge 후보 생성

---

## 병합 PR 자동 생성

* 공통점 요약
* 차이점 요약
* 병합 제안 텍스트

---

# 11. 도메인 경계 처리 전략

## 확률적 도메인 소속 모델

* primary_domain
* context_domains
* domain_confidence map

도메인은 고정값이 아니라 확률적 멤버십.

---

# 12. 콘텐츠 생성 레이어

## compose API

입력:

* topic
* depth
* format

출력:

* 블로그
* 강의
* 리포트
* 아이디어

---

## 아이디어 생성 로직

1. Dispute Axis 선택
2. 조건부 해결 구조 추출
3. 적용 도메인 매핑
4. monetization angle 생성

---

# 13. 시스템 흐름 요약

```
Raw Text →
KU-M0 생성 →
Edge 후보 생성 →
Hybrid Search →
Usage 수집 →
PR →
Maturity 상승 →
Graph 정제 →
아이디어/콘텐츠 생성
```

---

# 14. 실행 전략

## Phase 1

* 경제학 1권
* KU-M0/M1
* Edge 후보 생성
* Hybrid Search
* Usage 로그 수집

## Phase 2

* overlaps 자동 감지
* PathScore 적용
* 자동 M0→M1 승격

## Phase 3

* Dispute 자동화
* 다도메인 확장

---

# 15. 성공 조건

* 환각 방지 (근거 기반 구조)
* 중복 오염 방지
* 사용 데이터 기반 진화
* 조건부 추론 가능
* 확장 가능성 유지

---

# 16. 최종 정의

이 시스템은:

* 노트 앱이 아니다
* 단순 RAG가 아니다
* 단순 그래프 DB도 아니다

이것은

> Self-Correcting Knowledge Evolution Engine

이다.

---

# 17. 다음 단계

실행을 위해 필요한 것:

1. Supabase(Postgres) DDL 설계
2. Phase 1 최소 FASTAPI API 명세
3. KU 생성 파이프라인 설계
4. Hybrid Search 쿼리 설계

---

문서는 여기까지가 설계 완성본입니다.

원하시면 다음 단계로
📐 DDL 스키마 + API 명세 + 파이프라인 다이어그램
을 바로 제시하겠습니다.
