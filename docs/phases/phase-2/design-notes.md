# Phase 2: 서비스 레이어 — Design Notes
> Last Updated: 2026-02-28

## Stage E: 의미 검색

### E.2 similarity threshold — 튜닝 절차

```
튜닝 절차:
1. 초기값 0.5 설정
2. 10개 대표 쿼리 테스트:
   - "매몰비용", "기회비용", "인플레이션", "수요와 공급",
   - "시장 실패", "공공재", "외부효과", "비교우위",
   - "게임이론", "행동경제학"
3. 각 쿼리 결과:
   - 상위 5개 KU의 relevance 수동 평가 (relevant/irrelevant)
   - precision@5 계산
4. threshold 조정:
   - precision < 60% → threshold 올림 (0.55, 0.6)
   - recall 부족 (관련 KU 미반환) → threshold 내림 (0.45, 0.4)
5. 검색 결과 0건 시: "관련 KU 없음" 메시지 반환
```

### E.2 실측 결과 (threshold 0.6)

| 쿼리 | 건수 | Top-1 유사도 | Top-1 Claim |
|------|------|------------|-------------|
| 매몰비용 | 3 | 60.4% | 매몰비용은 투자자의 손해 만회 심리를 교묘히 이용... |
| 인플레이션 | 3 | 56.2% | 초인플레이션은 전쟁이나 경제 위기 등... |
| 경쟁의 효과 | 3 | 60.3% | 경쟁은 소비자들이 질 좋은 상품을 싸게... |
| 기회비용 | 3 | 41.2% | 변동비는 매출의 증감과 더불어... |
| 세금 정책 | 3 | 46.8% | 국가는 세금, 공공요금, 금리... |
| 시장 실패 | 2 | 42.1% | 외부비용이 경제 주체의... |
| 독점 | 2 | 43.2% | 독과점 상태에서는 기업이... |
| 무역 | 1 | 43.0% | 무역은 여러 단계를 거친 물물교환... |
| 이자율 | 0 | N/A | (threshold 0.7이면 2건 반환) |
| 가격 결정 | 1 | 40.2% | 판매자들이 가격을 담합하면... |

**결론:** threshold 0.6은 precision 우선, 대부분 쿼리에서 관련 KU 반환. 이자율만 0건 (0.7이면 검색됨).

### 열린 질문 (Open Questions)
- [x] ChromaDB cosine distance vs L2 distance — cosine 확정 (기존 임베딩과 일치)
- [x] 검색 쿼리 전처리 (한국어 형태소 분석) 필요 여부 — raw 쿼리로 충분 (text-embedding-3-large가 한국어 처리)

---

## Stage F: 콘텐츠 생성

### 생성 파이프라인 설계

```
Input: topic (str) + format (str)
  │
  ▼
[1] 벡터 검색: topic → embedding → ChromaDB top_k=10
  │
  ▼
[2] KU 컨텍스트 조합:
    - 각 KU의 claim + evidence_summary + counter_summary
    - 최대 5-10개 KU (토큰 제한 고려)
  │
  ▼
[3] 프롬프트 조합:
    - 템플릿 로드 (blog/summary/thread)
    - {topic}, {ku_context}, {format_instructions} 치환
  │
  ▼
[4] LLM 호출: Claude API → 콘텐츠 생성
  │
  ▼
[5] 후처리:
    - 출처 KU ID 첨부
    - generations 테이블 기록
    - 결과 반환
```

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

### CLI 설계

```
ks                          # Typer 기반 CLI
├── ingest <path>           # JSON/PDF → 전체 파이프라인
│   ├── --format json|pdf   # 입력 형식 (자동 감지)
│   └── --dry-run           # DB 저장 없이 미리보기
├── search <query>          # 벡터 검색
│   ├── --top-k N           # 결과 수 (기본 10)
│   ├── --domain <d>        # 도메인 필터
│   └── --threshold F       # 유사도 임계값
├── generate                # 생성 서브커맨드
│   └── content             # 콘텐츠 생성
│       ├── --topic <t>     # 토픽
│       ├── --format <f>    # blog|summary|thread
│       └── --ku-ids <ids>  # 특정 KU 지정 (선택)
└── stats                   # 기본 통계
```

### Vault 렌더러 설계

```markdown
---
id: ku-econ-001-0042
book: econ-thinking-001
domain: 경제
subdomain: 행동경제학
confidence: 0.7
maturity: M0
tags: [매몰비용, 의사결정, 비합리성]
created: 2026-02-27
---

## Claim
매몰비용은 이미 지불되어 회수 불가능한 비용으로, 합리적 의사결정에서 고려하지 않아야 한다.

## Evidence
- 원문 근거 요약...

## Counter
- 반론/한계 요약...

## Connections
(Phase 3에서 edges 기반 자동 생성)
```

### 열린 질문 (Open Questions)
- [ ] vault/ 디렉터리 구조: `vault/domains/{domain}/` 확정 (masterplan §11)
- [ ] KU 마크다운에 connections 섹션을 Phase 2에서 포함할지 — 빈 섹션 or 생략

---

## 디버깅 이력 (Debug History)

| Bug # | Module | Issue | Fix | File |
|-------|--------|-------|-----|------|
| E-1 | vector.py | threshold 0.35 → 전 쿼리 0건 | cosine distance 실측 0.39~0.51이므로 0.6으로 상향 | src/search/vector.py |

---

## 교훈 (Lessons Learned)

- ChromaDB cosine distance는 0~2 범위 (0=동일, 2=반대). 실측 top-1이 0.39~0.60이므로 threshold는 0.6이 적절.
- `PYTHONUTF8=1` 환경변수가 없으면 Windows Bash에서 한국어 출력이 깨짐.

---

## Modified Files Summary

### Stage E (pending commit)

```
src/
├── cli.py
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
vault/
├── domains/
│   └── 경제/
```
