# Phase 1: 1권 MVP — Design Notes
> Last Updated: 2026-02-27

## Stage C: PDF 파싱

### 설계 대안 (Alternatives Considered)

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| C-1 | 페이지 전체를 1 raw_span으로 | 단순, JSON 구조 그대로 | 스팬이 너무 큼 (페이지당 수백 자) | 후보 |
| C-2 | 줄바꿈 기반 문단 분리 | 의미 단위 분리 가능 | JSON 텍스트의 줄바꿈 패턴 불확실 | 유력 |
| C-3 | 대형 JSON (element 기반) | heading/paragraph 타입 구분 가능 | 2.2M 복잡한 구조, HTML 파싱 필요 | 보조 |

**결정 보류** — Stage C.1에서 text.json 샘플 검수 후 C-1 vs C-2 최종 결정. 페이지 텍스트의 줄바꿈 패턴에 따라 달라짐.

### 열린 질문 (Open Questions)
- [ ] text.json 페이지 텍스트의 줄바꿈이 문단 경계를 나타내는가? — C.1에서 확인
- [ ] 챕터 제목이 text.json 페이지 텍스트에 포함되어 있는가? — heading 별도 처리 필요 여부
- [ ] OCR 오류 수준은? — 심각 시 대형 JSON 또는 PDF 직접 파싱 전환

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

### 열린 질문 (Open Questions)
- [ ] GPT-4o mini의 한국어 claim 추출 정확도는? — D.1 테스트에서 확인
- [ ] 1페이지당 평균 KU 수는? — 예상 0.3-0.6, 실측 필요
- [ ] 중복 KU 감지/제거 전략은? — 임베딩 유사도 기반 후처리 vs 프롬프트에서 방지

---

## Stage F: 콘텐츠 생성

### 설계 대안 (Alternatives Considered)

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| F-1 | Claude (Anthropic) | 한국어 품질 우수, 긴 출력 | 비용 다소 높음 | 유력 |
| F-2 | GPT-4o | 범용 품질 우수 | 한국어 미세 열위 | 대안 |
| F-3 | GPT-4o mini | 비용 최저 | 생성 품질 불확실 | KU 추출용 |

**결정 보류** — Stage F에서 Claude vs GPT-4o 비교 테스트 후 결정.

### 열린 질문 (Open Questions)
- [ ] 검색된 KU를 프롬프트에 넣을 때 최적 개수는? — 3-5개 vs 5-10개
- [ ] 생성 결과의 품질 평가 기준은? — 정확성, 읽기 쉬움, 출처 추적 가능성

---

## Stage G: CLI + Vault

### 열린 질문 (Open Questions)
- [ ] Typer vs Click 최종 확정 — Stage G.1 시작 시 결정 (Typer 유력)
- [ ] vault/ 디렉터리 구조: `vault/domains/{domain}/` vs `vault/{book}/` — masterplan §11 기준 domains 구조
- [ ] KU 마크다운에 connections 섹션을 Phase 1에서 포함할지 — edges 없이 빈 섹션 or 생략

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
├── cli.py
├── db/
│   ├── __init__.py
│   ├── models.py
│   └── vectors.py
├── ingest/
│   ├── __init__.py
│   ├── pdf_parser.py
│   └── ku_extractor.py
├── search/
│   ├── __init__.py
│   └── vector.py
├── generation/
│   ├── __init__.py
│   ├── content.py
│   └── templates/
│       ├── blog.txt
│       ├── summary.txt
│       └── thread.txt
└── vault/
    ├── __init__.py
    └── renderer.py
data/
├── knowledge.db
├── chroma/
└── raw/
vault/
├── domains/
│   └── 경제/
config.yaml
pyproject.toml
```
