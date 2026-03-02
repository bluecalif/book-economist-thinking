# Session Compact

> Generated: 2026-03-02 (Session 26)
> Source: Phase 3 H.8p — 파일럿 품질 리포트 완료, Quality Gate PASS

## Goal
Phase 3 Stage H.8p 완료 — 파일럿 4권 품질 리포트 작성 및 Quality Gate PASS 판정. Stage I.pilot 이행.

## Completed
- [x] **H.infra 6/6** (Session 22-23): 87권 카탈로그, 데이터 경로, batch_ingest.py
- [x] **병렬 LLM 호출 구현** (Session 24): ThreadPoolExecutor, WAL 모드, --workers 옵션
- [x] **Git 커밋** (Session 25): `ab78087 phase-3 H.pilot: 병렬 LLM 호출 구현 + 배치 인제스트 스크립트`
- [x] **H.7p 파일럿 3권 인제스트 실행** (Session 25)
  - 공정하다는 착각 (humn-006): 391 spans → 1,483 KUs
  - 노이즈 (hist-016): 613 spans → 2,047 KUs
  - 대량살상 수학무기 (sci-023): 379 spans → 1,345 KUs
  - **합계**: 1,383 spans → 4,875 KUs, 실패 0권
  - 소요 시간: ~31분, parse rate ~99%, "database is locked" 간헐 발생 → 자동 재시도 성공

- [x] **H.8p 파일럿 KU 품질 리포트** (Session 26)
  - `reports/pilot_quality.md` 생성
  - claim 100%, evidence 100%, source_spans 100%, tags 97.3%
  - **Quality Gate: PASS**

## Current State
**Phase 3 Stage H.8p 완료 → I.pilot 대기.**

### 커밋 히스토리
```
ab78087 phase-3 H.pilot: 병렬 LLM 호출 구현 + 배치 인제스트 스크립트
b836f7f phase-3 Stage H.infra: 87권 확장 인프라 준비
3e4870f docs: 비용 추정치 실측 데이터 기반 수정 ($175-325 → ~$36-49)
d5ef001 docs: phase-3 설계 문서 개정 (Pilot First 전략)
```
(파일럿 인제스트 결과물 — vault, logs — 미커밋)

### DB 현황
- books=4, spans=1,724, kus=5,872, chroma=5,872, gens=2, edges=0
- 도메인: `경제/경영`(1권), `인문/자기계발`(1권), `역사/사회`(1권), `과학/기술`(1권)

### 파일 시스템 현황
- `books_catalog.yaml`: 87개 도서 (done=1, pilot=3, pending=83)
- `data/raw/`: 4개 디렉터리 = 87개 JSON
- `vault/domains/`: 4개 도메인 디렉터리, 5,872개 KU 마크다운
- `logs/batch_progress.json`: 파일럿 진행 로그

### 미커밋 파일
- `vault/domains/과학-기술/` — 신규 (1,345 KU 마크다운)
- `vault/domains/역사-사회/` — 신규 (2,047 KU 마크다운)
- `vault/domains/인문-자기계발/` — 신규 (1,483 KU 마크다운)
- `logs/batch_progress.json` — 배치 진행 로그
- `reports/pilot_quality.md` — H.8p 품질 리포트

### 인제스트 성능 지표
| 도서 | 도메인 | Spans | KUs | Parse Rate |
|------|--------|-------|-----|------------|
| 공정하다는 착각 | 인문/자기계발 | 391 | 1,483 | ~99% |
| 노이즈 | 역사/사회 | 613 | 2,047 | ~99% |
| 대량살상 수학무기 | 과학/기술 | 379 | 1,345 | 99.2% |
| **합계** | | **1,383** | **4,875** | |

## Remaining / TODO
- [ ] **Git 커밋**: 파일럿 인제스트 결과물 (vault, logs, reports)
- [ ] **Stage I.pilot** (추정 $2-5) — edge_builder, traversal, CLI explore
- [ ] **Quality Gate** — parse ≥95%, claim ≥80%, edge 적합도 ≥60-70%
- [ ] **Stage H.full** (~$23) — 나머지 83권
- [ ] **Stage I.full** (추정 $10-20) — 전체 그래프 + Dispute
- [ ] **Stage J** ($0) — Hybrid Search + Idea Generation

## Key Decisions
- **Pilot First 전략**: 87권 일괄 → 4권 파일럿(도메인당 1권) → Quality Gate → 전체 확장
- **LLM 응답 캐시**: `src/ingest/llm_cache.py` — hash(model+prompt+text) 키, 재실행 비용 $0
- **도메인 통일**: `경제` → `경제/경영` (DB + Vault + 코드 전체 동기화)
- **카탈로그 매칭**: 최장 접두사 우선 + used 집합으로 중복 방지 (87/87 고유 매칭)
- **데이터 경로**: `data/raw/{도메인-하이픈}/` 구조 (슬래시→하이픈)
- **파일럿 도서 선정**: 논증형 도서 우선 (카너먼, 샌델, 오닐) — claim/counter 품질 검증에 적합
- **병렬화**: ThreadPoolExecutor(max_workers=5), LLM 호출만 병렬 + DB 저장 순차

## Context
다음 세션에서는 답변에 한국어를 사용하세요.

### 프로젝트 핵심 참조
- **마스터플랜**: `docs/masterplan-v2.0.md`
- **Phase 3 dev-docs**: `docs/phases/phase-3/` (plan, context, tasks, design-notes)
- **기술 스택**: Python 3.12 (anaconda3), SQLite, ChromaDB, Typer CLI, GPT-4.1-mini
- **OpenAI API**: `.env` 파일에 OPENAI_API_KEY 설정됨
- **87권 소스 CSV**: `C:\Projects-2026\maintenance\books-final-processor\docs\100권 노션 원본_수정.csv` (utf-8-sig)

### Phase 3 전체 흐름
```
H.infra ($0) ✅ → H.pilot (~$1) ✅ → H.8p (품질 리포트) ✅
                                        → I.pilot ($2-5) ← 현재 위치 → Quality Gate
                                          ├─ PASS → H.full (~$23) → I.full ($10-20) → J ($0)
                                          └─ FAIL → 프롬프트 튜닝 → 재실행 (캐시 $0)
```

### Phase 3 완료 기준
- `ks stats` → books=87, spans≥25,000, kus≥75,000, chroma≥75,000
- `ks explore ku-id --depth 2` → 연결된 KU 탐색
- `ks generate idea --mode business --domains 경제/경영,과학/기술` → 아이디어 생성
- 4개 도메인 간 dispute 축 자동 식별

### 디렉터리 구조
```
src/
├── cli.py              # Typer CLI — catalog 기반으로 수정 완료
├── db/
│   ├── models.py        # SQLite CRUD (5 tables)
│   └── vectors.py       # ChromaDB wrapper
├── ingest/
│   ├── ku_extractor.py  # KU extraction — 병렬 LLM 호출 (ThreadPoolExecutor)
│   ├── pdf_parser.py    # JSON parser — catalog 기반으로 수정 완료
│   └── llm_cache.py     # LLM 응답 캐시 (WAL 모드)
├── search/
│   └── vector.py
├── generation/
│   ├── content.py
│   └── templates/
└── vault/
    └── renderer.py      # _domain_to_dir() 적용 완료

scripts/
├── batch_ingest.py      # 배치 인제스트 (H.6p, --workers 옵션)
├── build_catalog.py     # 카탈로그 빌더
├── migrate_data.py      # 데이터 마이그레이션
├── test_e2e.py
└── test_e2e_phase1.py

tests/
└── test_llm_cache.py    # 캐시 단위 테스트 (4/4 pass)
```

## Next Action
**Git 커밋 후 Stage I.pilot 시작**
1. 파일럿 결과물 Git 커밋 (vault, logs, reports)
2. Stage I.pilot 설계 — edge_builder, traversal, CLI explore
   - edge 6타입: `supports`, `contradicts`, `extends`, `applies`, `causes`, `analogous`
   - 파일럿 4권 KU 간 edge 생성 (LLM 호출)
   - `ks explore ku-id --depth 2` CLI 명령 구현
3. Quality Gate: edge 적합도 ≥60-70%
