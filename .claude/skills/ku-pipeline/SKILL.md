---
name: ku-pipeline
description: KU(Knowledge Unit) 추출 파이프라인 가드레일. claim + evidence_summary + counter_summary 구조, source_spans 추적, M0/M1/M2 maturity 모델, KU ID 패턴(ku-{domain}-{book_seq}-{ku_seq}), raw_spans → KU 변환 규칙, 추출 프롬프트 전략. KU 추출, 지식 단위, knowledge unit 작업 시 자동 활성화.
---

# KU Pipeline Guardrail

## 목적

Knowledge Unit 추출 및 관리 시 프로젝트 규칙 준수를 강제한다.

## 사용 시점

- KU 추출 코드 작성/수정
- `ku_extractor.py` 관련 작업
- KU 구조 변경 논의
- LLM 프롬프트에서 KU 추출 로직 설계

---

## KU 구조 (필수)

모든 KU는 다음 필드를 가져야 한다:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | TEXT | O | `ku-{domain}-{book_seq}-{ku_seq}` 예: `ku-econ-001-0042` |
| `book_id` | TEXT FK | O | `books.id` 참조. 예: `econ-thinking-001` |
| `claim` | TEXT | O | 핵심 주장 (1-2문장). **claim 없는 서술은 KU가 아님** |
| `evidence_summary` | TEXT | - | 근거 요약. 원문 인용 기반 |
| `counter_summary` | TEXT | - | 반례/한계 요약 (저자 제시 시) |
| `domain` | TEXT | O | 1차 도메인: 인문\|사회\|역사\|경제\|과학\|기술\|경영 |
| `subdomain` | TEXT | - | 세부 분야 (예: 행동경제학) |
| `tags` | TEXT(JSON) | - | 키워드 태그 배열 |
| `confidence` | REAL | - | 0.0-1.0, 기본 0.5 |
| `maturity` | TEXT | - | M0\|M1\|M2, 기본 M0 |
| `source_spans` | TEXT(JSON) | - | raw_span ID 배열 → 근거 추적 |

### ID 규칙

- **Book ID**: `{domain_short}-{book_name_short}-{seq}` 예: `econ-thinking-001`
- **KU ID**: `ku-{domain_short}-{book_seq}-{ku_seq}` 예: `ku-econ-001-0042`
- KU seq는 4자리 zero-padded

---

## Maturity 모델

| 단계 | 조건 | 설명 |
|------|------|------|
| **M0** | LLM 자동 추출 | claim + evidence 존재, 미검증 |
| **M1** | 수동 검토 완료 | claim 정확성, evidence 매핑 확인 |
| **M2** | 외부 지식 보강 | 웹 크롤링 또는 다른 책 KU와 교차 검증 완료 |

- 신규 추출 KU는 항상 **M0**으로 시작
- M3는 사용하지 않음 (1인 환경)

---

## 추출 규칙 (CRITICAL)

1. **claim 필수**: claim이 없는 서술(배경 설명, 일화, 목차 등)은 KU로 추출 금지
2. **1 KU = 1 claim**: 하나의 KU에 여러 주장을 넣지 않음
3. **evidence 원문 기반**: evidence_summary는 원문 인용/참조 기반
4. **source_spans 필수**: 추출 시 원본 raw_span ID를 반드시 기록
5. **counter는 저자 기준**: 사용자 의견이 아닌 저자가 제시한 한계/반례만

### 추출 프롬프트 템플릿

```
[System] 당신은 책의 내용을 구조화된 지식 단위로 추출하는 전문가입니다.

[User] 다음 텍스트에서 Knowledge Unit을 추출하세요.

규칙:
1. 각 KU는 하나의 명확한 claim(주장)을 가져야 합니다
2. claim을 뒷받침하는 evidence(근거)를 원문에서 인용하세요
3. 저자가 제시한 한계나 반례가 있으면 counter로 기록하세요
4. claim이 없는 서술(배경 설명, 일화 등)은 KU로 추출하지 마세요
5. 하나의 텍스트에서 여러 KU가 나올 수 있습니다

출력 형식: JSON array
[{"claim": "...", "evidence_summary": "...", "counter_summary": "...", "tags": [...]}]

텍스트:
{chunk_text}
```

---

## 품질 체크리스트

KU 추출 코드 작성/수정 시 확인:

- [ ] claim이 1-2문장의 명확한 주장인가?
- [ ] evidence_summary가 원문 기반인가?
- [ ] source_spans에 raw_span ID가 기록되는가?
- [ ] KU ID 패턴이 `ku-{domain}-{book_seq}-{ku_seq}`인가?
- [ ] 신규 KU의 maturity가 M0인가?
- [ ] confidence 기본값이 0.5인가?
- [ ] domain이 7개 도메인 중 하나인가?

---

## 관련 파일

- `src/ingest/ku_extractor.py` — KU 추출 로직
- `src/ingest/pdf_parser.py` — PDF → raw_spans
- `src/db/models.py` — DB 스키마
- `docs/masterplan-v2.0.md` §5 — L1 상세 설계
