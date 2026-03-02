# Session Compact

> Generated: 2026-03-02 (Session 28)
> Source: Phase 3 I.pilot 완료 — edge 생성 실행 + 품질 리포트 + Quality Gate PASS

## Goal
Phase 3 Stage I.pilot 완료 — edge 생성 파이프라인 실행, 그래프 탐색 검증, 품질 리포트 작성.

## Completed
- [x] **H.infra 6/6** (Session 22-23): 87권 카탈로그, 데이터 경로, batch_ingest.py
- [x] **병렬 LLM 호출 구현** (Session 24): ThreadPoolExecutor, WAL 모드, --workers 옵션
- [x] **H.7p 파일럿 3권 인제스트 실행** (Session 25): 1,383 spans → 4,875 KUs
- [x] **H.8p 파일럿 KU 품질 리포트** (Session 26): Quality Gate PASS
- [x] **I.1p~I.4p edge 코드 구현** (Session 27): edge_builder, traversal, CLI explore
- [x] **I.pilot 코드 커밋** (Session 28): `78d75b8`
  - src/db/models.py: edge CRUD 3함수
  - src/graph/: edge_builder.py, traversal.py, __init__.py
  - src/cli.py: explore 명령어
  - scripts/build_edges.py: 배치 edge 생성
- [x] **I.2p edge 생성 실행** (Session 28)
  - SQLite 멀티쓰레드 버그 발견 및 수정 (conn 쓰레드 공유 → KU pre-load 패턴)
  - 13,643 후보 → **11,662 edges 생성** (85.5% 성공률)
  - 소요 60분, gpt-4.1-mini, workers=5
  - 마지막 ~50건 OpenAI quota exceeded (429) — 전체 0.4% 미만
- [x] **I.3p~I.4p 탐색 검증** (Session 28): `explore ku-econ-001-0001 --depth 2` → 7노드 탐색 확인
- [x] **I.5p 품질 리포트** (Session 28): `reports/pilot_graph.md` 작성, **Quality Gate PASS**
- [x] **결과 커밋** (Session 28): `eaa9165`

## Current State
**Phase 3 Stage I.pilot 완료. H.full (83권 인제스트) 진행 가능.**

### 커밋 히스토리
```
eaa9165 phase-3 I.pilot: edge 생성 실행 + 쓰레드 안전성 수정 + 품질 리포트
78d75b8 phase-3 I.pilot: edge 생성 파이프라인 + 그래프 탐색 구현
3898df8 phase-3 H.8p: 파일럿 품질 리포트 + 인제스트 결과물
ab78087 phase-3 H.pilot: 병렬 LLM 호출 구현 + 배치 인제스트 스크립트
b836f7f phase-3 Stage H.infra: 87권 확장 인프라 준비
```

### DB 현황
- books=4, spans=1,724, kus=5,872, chroma=5,872, gens=2, **edges=11,662**
- 도메인: `경제/경영`(1권), `인문/자기계발`(1권), `역사/사회`(1권), `과학/기술`(1권)

### Edge 실적 요약
| 항목 | 값 |
|------|-----|
| 후보 쌍 | 13,643 |
| 생성된 edges | 11,662 (85.5%) |
| Relation type | extends 42.7%, supports 34.7%, contradicts 10.3%, explains 9.5%, analogous_to 2.3%, example_of 0.6% |
| Strength | 평균 0.779, 99.1%가 0.7 이상 |
| 샘플 적합도 | 6/6 (100%) |
| Cross-domain edge | 0건 (후보 35건 있었으나 LLM 판정에서 거부) |

### Changed Files (이번 세션)
- `src/graph/edge_builder.py` — SQLite 멀티쓰레드 버그 수정 (KU pre-load 패턴)
- `reports/pilot_graph.md` — 신규: 그래프 품질 리포트
- `docs/session-compact.md` — 세션 문서 업데이트

## Remaining / TODO
- [ ] **Stage H.full** (~$23) — 나머지 83권 인제스트
  - [ ] 배치 전략 계획 (비용/시간 추정)
  - [ ] batch_ingest.py 실행
  - [ ] 품질 리포트
- [ ] **Stage I.full** (추정 $10-20) — 전체 87권 그래프 edge 생성
  - [ ] cross-domain 전략 개선 필요
- [ ] **Stage J** ($0) — Hybrid Search + Idea Generation
  - [ ] CLI search 명령어
  - [ ] 생성 파이프라인

## Key Decisions
- **SQLite 멀티쓰레드 해법**: conn 객체를 쓰레드 간 공유하면 안 됨 → `build_edges()`에서 KU 데이터를 메인 쓰레드에서 pre-load 후 dict로 전달. llm_cache.py는 호출마다 새 conn 생성하므로 안전.
- **Cross-domain edge 부족**: threshold=0.35에서 후보 35건만 생성, LLM 판정에서 전부 거부 → 향후 전용 전략 필요 (threshold 하향 또는 다른 접근법)
- **Strength 편향**: LLM이 관계를 인정하면 대부분 0.7+ → 실질적으로 이진 판단에 가까움
- **Quality Gate PASS 기준**: 성공률 >80%, 6종 타입 다양성, 샘플 적합도 >80%, Edge/KU >1.0

## Context
다음 세션에서는 답변에 한국어를 사용하세요.

### 프로젝트 핵심 참조
- **마스터플랜**: `docs/masterplan-v2.0.md`
- **Phase 3 dev-docs**: `docs/phases/phase-3/` (plan, context, tasks, design-notes)
- **기술 스택**: Python 3.12 (anaconda3), SQLite, ChromaDB, Typer CLI, GPT-4.1-mini
- **품질 리포트**: `reports/pilot_graph.md`, `reports/pilot_quality.md`

### Phase 3 전체 흐름
```
H.infra ($0) ✅ → H.pilot (~$1) ✅ → H.8p (품질 리포트) ✅
                                       → I.pilot (코드+실행+리포트) ✅ ← 완료
                                         ├─ PASS ✅ → H.full (~$23) → I.full ($10-20) → J ($0)
                                         └─ FAIL → 프롬프트 튜닝 → 재실행 (캐시 $0)
```

### 디렉터리 구조
```
src/
├── graph/
│   ├── __init__.py
│   ├── edge_builder.py    # 2-Tier 후보 선정 + LLM 판정 (쓰레드 안전)
│   └── traversal.py       # BFS + PathScore
├── db/
│   ├── models.py          # books, raw_spans, kus, edges CRUD
│   └── vectors.py         # ChromaDB 래퍼
├── ingest/
│   ├── ku_extractor.py    # LLM 기반 KU 추출
│   ├── llm_cache.py       # SQLite 캐시 (쓰레드 안전)
│   └── splitter.py        # 텍스트 분할
└── cli.py                 # stats, ingest, explore 명령어

scripts/
├── batch_ingest.py        # 배치 인제스트
└── build_edges.py         # 배치 edge 생성

reports/
├── pilot_quality.md       # H.8p KU 품질 리포트
└── pilot_graph.md         # I.5p 그래프 품질 리포트
```

## Next Action
1. Stage H.full 계획 수립 — 83권 인제스트 배치 전략 (예상 비용 ~$23, 시간 추정)
2. 또는 사용자가 지정하는 다음 단계
