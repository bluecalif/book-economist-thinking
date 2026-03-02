# Session Compact

> Generated: 2026-03-02 (Session 27)
> Source: Phase 3 I.pilot — edge_builder, traversal, CLI explore 구현

## Goal
Phase 3 Stage I.pilot 구현 — KU 간 edge 생성 파이프라인 + 그래프 탐색.

## Completed
- [x] **H.infra 6/6** (Session 22-23): 87권 카탈로그, 데이터 경로, batch_ingest.py
- [x] **병렬 LLM 호출 구현** (Session 24): ThreadPoolExecutor, WAL 모드, --workers 옵션
- [x] **H.7p 파일럿 3권 인제스트 실행** (Session 25): 1,383 spans → 4,875 KUs
- [x] **H.8p 파일럿 KU 품질 리포트** (Session 26): Quality Gate PASS
- [x] **I.1p edge CRUD + edge_builder** (Session 27)
  - `src/db/models.py`: insert_edge, list_edges_by_ku, count_edges 추가
  - `src/graph/__init__.py`: 패키지 생성
  - `src/graph/edge_builder.py`: 2-Tier 후보 선정 + LLM 판정 + 병렬 build_edges
- [x] **I.2p build_edges.py** (Session 27)
  - `scripts/build_edges.py`: --mode within|cross-chapter|cross-domain|all, --dry-run
  - dry-run 검증: within 13,490 + cross-ch 118 + cross-domain 35 = 13,643 후보 쌍
- [x] **I.3p traversal.py** (Session 27)
  - `src/graph/traversal.py`: BFS + PathScore (HarmonicMean × Mean confidence)
- [x] **I.4p CLI explore** (Session 27)
  - `src/cli.py`: `ks explore <ku-id> --depth 2` 명령어 추가

## Current State
**Phase 3 Stage I.1p~I.4p 완료 → I.2p 실행(edge 실제 생성) + I.5p(품질 리포트) 대기.**

### 커밋 히스토리
```
3898df8 phase-3 H.8p: 파일럿 품질 리포트 + 인제스트 결과물
ab78087 phase-3 H.pilot: 병렬 LLM 호출 구현 + 배치 인제스트 스크립트
b836f7f phase-3 Stage H.infra: 87권 확장 인프라 준비
```

### DB 현황
- books=4, spans=1,724, kus=5,872, chroma=5,872, gens=2, edges=0
- 도메인: `경제/경영`(1권), `인문/자기계발`(1권), `역사/사회`(1권), `과학/기술`(1권)

### Edge 후보 실측 (dry-run)
| 전략 | 후보 쌍 |
|------|---------|
| Within-chapter | 13,490 |
| Cross-chapter (centroid) | 118 |
| Cross-domain | 35 |
| **합계 (중복제거)** | **13,643** |

유사도 범위: 0.350~0.999, 평균 0.532

### 디렉터리 구조 (변경분)
```
src/
├── graph/                 # 신규 패키지
│   ├── __init__.py
│   ├── edge_builder.py    # 후보 선정 + LLM 판정 + build_edges
│   └── traversal.py       # BFS + PathScore
├── db/
│   └── models.py          # edge CRUD 3함수 추가
└── cli.py                 # explore 명령어 추가

scripts/
└── build_edges.py         # 배치 edge 생성
```

## Remaining / TODO
- [ ] **I.2p 실행**: `python scripts/build_edges.py --mode all --workers 5` (추정 ~$3)
- [ ] **I.5p 그래프 품질 리포트**: `reports/pilot_graph.md`
- [ ] **Git 커밋**: I.pilot 코드
- [ ] **Quality Gate**: edge 적합도 ≥60-70%
- [ ] **Stage H.full** (~$23) — 나머지 83권
- [ ] **Stage I.full** (추정 $10-20) — 전체 그래프 + Dispute
- [ ] **Stage J** ($0) — Hybrid Search + Idea Generation

## Key Decisions
- **2-Tier 접근**: within-chapter 전수 + cross-chapter centroid 샘플링 (비용 37% 절감)
- **threshold 0.35**: ChromaDB 유사도 실측 기반 (top-10 기준 0.40~0.53)
- **Centroid 선정**: 챕터 평균 벡터와 가장 가까운 KU 5개
- **Edge 6타입**: supports, contradicts, extends, explains, example_of, analogous_to
- **LLM 판정**: none 또는 strength < 0.3 → edge 미생성
- **Edge ID 규칙**: `edge-{from_ku_short}-{to_ku_short}`

## Context
다음 세션에서는 답변에 한국어를 사용하세요.

### 프로젝트 핵심 참조
- **마스터플랜**: `docs/masterplan-v2.0.md`
- **Phase 3 dev-docs**: `docs/phases/phase-3/` (plan, context, tasks, design-notes)
- **기술 스택**: Python 3.12 (anaconda3), SQLite, ChromaDB, Typer CLI, GPT-4.1-mini

### Phase 3 전체 흐름
```
H.infra ($0) ✅ → H.pilot (~$1) ✅ → H.8p (품질 리포트) ✅
                                        → I.pilot (코드) ✅ → I.2p 실행 + I.5p 리포트 ← 현재 위치
                                          ├─ PASS → H.full (~$23) → I.full ($10-20) → J ($0)
                                          └─ FAIL → 프롬프트 튜닝 → 재실행 (캐시 $0)
```

## Next Action
1. `python scripts/build_edges.py --mode all --workers 5` 실행 → edge 생성
2. `python -m src.cli explore ku-econ-001-0001 --depth 2` → 그래프 탐색 확인
3. `reports/pilot_graph.md` 품질 리포트 작성
4. Quality Gate 판정
5. Git 커밋
