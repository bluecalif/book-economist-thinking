# Phase 3: 87권 확장 + 그래프 레이어 — Design Notes
> Last Updated: 2026-03-02

## 전략 변경: 일괄 처리 → Pilot First

### 설계 대안 (Alternatives Considered)

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| 1 | 87권 전체 인제스트 → 그래프 (기존 plan) | 단순한 파이프라인 | 비검증 상태 투자 (실측 기준 ~$36-49), 품질 문제 발견 시 재작업 | **Pilot First로 변경** |
| 2 | Pilot First (4권 → Quality Gate → 전체) | 리스크 1/3, 조기 품질 검증 | 총 비용 약간 증가, 단계 증가 | **채택** |
| 3 | 도메인별 순차 확장 (1 도메인씩) | 도메인별 최적화 가능 | 너무 느림, cross-domain 검증 지연 | 기각 |

### Pilot First 전략 근거

1. **비경제 도메인 KU 품질 미검증**: 현재까지 경제 도서 1권만 테스트. 역사(서술형), 인문(에세이형), 과학(기술형) 도서에서 동일 프롬프트의 KU 추출 품질 불명
2. **비용 리스크 감소**: Quality Gate 전 노출 ~$3-6 (실측 기반, 기존 추정 $55-95의 1/10)
3. **프롬프트 튜닝 기회**: 파일럿 결과로 도메인별 프롬프트 오버라이드 가능성 판단
4. **Graph end-to-end 검증**: KU 품질뿐 아니라 edge 생성 품질도 함께 검증

---

## H.cache: LLM 응답 캐시 설계

### 설계 대안

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| 1 | 파일 기반 캐시 (JSON 파일) | 간단 | 검색 느림, 관리 어려움 | 기각 |
| 2 | SQLite 캐시 (해시 키) | 빠른 조회, 토큰 사용량 추적, 프롬프트 변경 시 자동 무효화 | 별도 DB 파일 | **채택** |
| 3 | Redis 캐시 | 고성능 | 외부 서비스 의존, 로컬 우선 원칙 위반 | 기각 |

### 캐시 동작 원리

```python
# 의사 코드
def cached_call_llm(client, text, model, system_prompt):
    key = sha256(f"{model}|{system_prompt}|{text}").hexdigest()

    cached = cache_db.get(key)
    if cached:
        return cached.response  # $0

    response = client.chat.completions.create(...)
    cache_db.put(key, response, model, tokens_in, tokens_out)
    return response
```

**핵심 특성:**
- 프롬프트 텍스트가 해시에 포함 → 프롬프트 변경 시 자동으로 새 API 호출
- 동일 프롬프트+동일 텍스트 → 항상 캐시 히트
- 토큰 사용량 기록 → 비용 추적 가능
- edge 생성 LLM 호출에도 동일 메커니즘 적용

### 비용 절감 시나리오

| 시나리오 | 캐시 없이 | 캐시 있으면 |
|----------|----------|------------|
| 파일럿 3권 정상 완료 | ~$1 | ~$1 (첫 실행) |
| 프롬프트 튜닝 후 1개 도메인 재실행 | ~$0.28 추가 | ~$0 (프롬프트 변경 span만 재호출) |
| 배치 중단 후 재시작 | 전액 재실행 | $0 (완료된 span 캐시 히트) |
| 동일 book 전체 재인제스트 | ~$0.28 | $0 |

> **실측 근거:** econ-thinking 1권 = input $0.09 (220K tokens) + output $0.19 (110K tokens) = $0.28

---

## Stage H.infra: 기존 plan 계승 내용

### books-final-processor → 현재 프로젝트 데이터 흐름

```
books-final-processor (소스)
├── docs/100권 노션 원본_수정.csv      ──→  build_catalog.py  ──→  books_catalog.yaml
└── data/output/text/*_text.json       ──→  migrate_data.py   ──→  data/raw/{domain}/

현재 프로젝트 (대상)
├── books_catalog.yaml                 ──→  batch_ingest.py   ──→  knowledge.db + chroma/
└── data/raw/{domain}/*_text.json      ──→  ingest_book()     ──→  raw_spans → KUs
```

### text.json 파일명 패턴

```
{6자리_hash}_{제목_공백제거}_text.json
```
87/87 전부 매칭 확인됨 (공백 정규화 포함)

### domain_short 하드코딩 문제

**현재 코드** (`ku_extractor.py:154`):
```python
domain_short = "econ"  # 경제 → econ
```

**수정:**
```python
DOMAIN_SHORT_MAP = {
    "역사/사회": "hist",
    "경제/경영": "econ",
    "인문/자기계발": "humn",
    "과학/기술": "sci",
    "경제": "econ",   # 레거시
}
domain_short = DOMAIN_SHORT_MAP.get(domain, domain[:4].lower())
```

### 기존 데이터 도메인 마이그레이션

```sql
UPDATE books SET domain='경제/경영' WHERE id='econ-thinking-001';
UPDATE knowledge_units SET domain='경제/경영' WHERE book_id='econ-thinking-001';
```

### 배치 처리 안전장치

1. **멱등성**: `INSERT OR IGNORE` → 같은 책 재실행 안전
2. **체크포인트**: `logs/batch_progress.json` → 북 단위 상태 추적
3. **에러 격리**: `try/except` → 1권 실패 시 다음 권 계속
4. **재시작**: `--from-book` 옵션 → 중간부터 재시작
5. **Rate limit**: `delay_between_spans=0.5`, `delay_between_books=2.0`
6. **LLM 캐시**: 재시작 시 완료된 span은 $0

---

## Quality Gate: 프롬프트 튜닝 전략

파일럿에서 비경제 도메인의 KU 품질이 낮을 경우 도메인별 프롬프트 분기 가능:

```python
# 현재: 단일 프롬프트
USER_PROMPT_TEMPLATE = "..."

# 개선안 (Quality Gate 결과에 따라 선택적 적용):
DOMAIN_PROMPT_OVERRIDES = {
    "역사/사회": "... 역사적 사건의 인과관계, 시대 간 비교, 사회 구조적 패턴을 중심으로 ...",
    "과학/기술": "... 기술적 원리, 실험 결과, 인과 메커니즘을 중심으로 ...",
}
```

단, 파일럿 결과가 양호하면 **단일 프롬프트를 유지** (불필요한 복잡성 회피).

---

## 디버깅 이력 (Debug History)

| Bug # | Module | Issue | Fix | File |
|-------|--------|-------|-----|------|
| 1 | edge_builder | SQLite conn 멀티쓰레드 공유 시 ProgrammingError | KU 데이터 메인쓰레드에서 pre-load → dict로 전달 | `src/graph/edge_builder.py` |
| 2 | build_edges | OpenAI 429 quota exceeded (~50건) | 전체 0.4% 미만, 무시 가능 | `scripts/build_edges.py` |

### Bug-1: SQLite 멀티쓰레드 conn 공유

**증상:** `ThreadPoolExecutor`로 병렬 edge 생성 시 `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`

**원인:** `models.py`의 conn 객체를 worker 쓰레드에서 직접 사용. SQLite는 기본적으로 쓰레드 간 conn 공유를 허용하지 않음.

**수정:** `build_edges()`에서 edge 생성 전에 필요한 KU 데이터를 메인 쓰레드에서 모두 읽어 dict로 변환. worker 쓰레드는 dict만 참조하고 DB 접근 안 함. `llm_cache.py`는 호출마다 새 conn을 생성하므로 안전.

---

## 열린 질문 (Open Questions)

- [x] 파일럿 도서 구체적 선정 — 카탈로그 status=pilot 기반 (도메인당 1권)
- [ ] ChromaDB 75,000+ embedding 성능 — 벤치마크 필요
- [ ] Vault 75,000+ 파일 시 Obsidian 성능 — 대규모 vault 테스트 필요
- [x] within-book edge 먼저? cross-domain 먼저? — within-book 우선 (높은 신뢰도)
- [x] 87권 배치 시간 — 1권당 ~3-5분 × 86권 ≈ 4-7시간
- [ ] Cross-domain edge 전략 — 임베딩 유사도 0.35 threshold로는 부족, 전용 전략 설계 필요

---

## 교훈 (Lessons Learned)

- books-final-processor의 text.json 형식이 현재 파이프라인과 100% 호환 → PDF 재파싱 불필요
- CSV-JSON 매칭 시 공백 정규화가 핵심 (87/87 전부 매칭 가능)
- 기존 DB의 INSERT OR IGNORE 패턴 덕분에 배치 재실행이 안전
- **현재 코드에 캐시/체크포인트 메커니즘이 전혀 없음** → H.cache에서 반드시 해결
- **비경제 도메인 KU 품질은 실제 실행 전까지 알 수 없음** → Pilot First 전략 필수
- **SQLite conn은 쓰레드 간 공유 불가** → pre-load 패턴 또는 쓰레드별 새 conn 생성
- **LLM strength 점수는 실질적 이진 판단** — 관계 인정 시 99.1%가 0.7+ → fine-grained ranking 부적합
- **Cross-domain edge는 임베딩 유사도만으로 부족** — threshold 하향 또는 토픽 기반 매칭 등 전용 전략 필요
- **Edge 생성 실측 비용** — 4권 11,662 edges에 60분, gpt-4.1-mini (87권 확장 시 추정치 산정 근거)

---

## Modified Files Summary

```
수정 (완료):
├── src/ingest/ku_extractor.py    — DOMAIN_SHORT_MAP, domain_short 파라미터화, 캐시 래퍼 통합
├── src/vault/renderer.py         — _domain_to_dir(), Connections 섹션
├── src/cli.py                    — ks explore 명령 추가 ✅
├── src/db/models.py              — edge CRUD 3함수 추가 ✅
└── config.yaml                   — books 제거, catalog/batch 섹션 추가

신규 (완료):
├── src/ingest/llm_cache.py       — LLM 응답 캐시 ✅
├── books_catalog.yaml            — 87권 메타데이터 카탈로그 ✅
├── scripts/build_catalog.py      — 카탈로그 생성 ✅
├── scripts/migrate_data.py       — 데이터 마이그레이션 ✅
├── scripts/batch_ingest.py       — 배치 처리 (--pilot/--all) ✅
├── scripts/build_edges.py        — 배치 edge 생성 ✅
├── src/graph/__init__.py         — graph 패키지 ✅
├── src/graph/edge_builder.py     — edge 생성 (쓰레드 안전) ✅
└── src/graph/traversal.py        — 그래프 탐색 (BFS + PathScore) ✅

신규 (예정):
├── src/graph/dispute.py          — Dispute axis 요약 (I.full)
├── src/generation/idea.py        — 아이디어 생성 (J)
└── src/search/hybrid.py          — 복합 검색 (J)

리포트:
├── reports/pilot_quality.md      — KU 품질 리포트 ✅
└── reports/pilot_graph.md        — 그래프 품질 리포트 ✅
```
