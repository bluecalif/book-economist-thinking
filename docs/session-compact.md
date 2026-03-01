# Session Compact

> Generated: 2026-03-01 (Session 21)
> Source: Phase 3 계획 전면 개정 (Pilot First) + dev-docs 업데이트

## Goal
Phase 3 계획을 비판적으로 검토하고, "Pilot First → Graph → Full Expansion" 전략으로 개정. Phase 3 dev-docs 4파일 업데이트 + project-overall 3파일 동기화.

## Completed
- [x] **Phase 3 기존 계획 비판적 검토**: 87권 일괄 → 파일럿 전환 필요성 확인
- [x] **KU 파이프라인 비용/품질 분석**: 1권당 ~$15-25, 341 spans → 997 KUs, 100% parse 성공률
- [x] **캐시 부재 문제 발견**: 현재 코드에 LLM 응답 캐시/체크포인트 전혀 없음
- [x] **개정 계획 수립**: Plan 에이전트로 상세 설계 (H.infra → H.pilot → I.pilot → Quality Gate → H.full → I.full → J)
- [x] **사용자 결정 확인**: 도메인당 1권 파일럿 OK, KU+Graph 함께 검증, LLM 캐시 핵심
- [x] **Phase 3 dev-docs 4파일 업데이트 완료**:
  - `docs/phases/phase-3/plan.md` — Pilot First 전략, 7단계 구조, 비용 비교
  - `docs/phases/phase-3/context.md` — llm_cache.py 추가, LLM 캐시 스키마, 결정사항 7-9번 추가
  - `docs/phases/phase-3/tasks.md` — 23 Tasks (기존 15 → 23), 의존성 그래프 갱신
  - `docs/phases/phase-3/design-notes.md` — 전략 변경 근거, 캐시 설계, 프롬프트 튜닝 전략
- [x] **project-overall 3파일 동기화 완료**
  - `docs/project-plan.md` — Phase 3 Stages 7단계, Pilot First 전략, 비용 갱신
  - `docs/project-context.md` — llm_cache.db 추가, 디렉터리 구조 갱신
  - `docs/project-tasks.md` — 0/23 Tasks, Key Decisions 16-18번 추가

## Current State
**Phase 3 dev-docs + project-overall 동기화 완료. 커밋 대기.**

### 커밋 히스토리 (변경 없음 — 아직 커밋 안 함)
```
8b88d2b docs: phase-3 설계 문서 생성
acc1942 phase-2 Stage G: CLI + Vault 렌더러 + 통합 테스트
```

### 변경된 파일 (uncommitted)
- `docs/phases/phase-3/plan.md` — 전면 재작성 (Pilot First)
- `docs/phases/phase-3/context.md` — 전면 재작성 (캐시 스키마 추가)
- `docs/phases/phase-3/tasks.md` — 전면 재작성 (15→23 Tasks)
- `docs/phases/phase-3/design-notes.md` — 전면 재작성 (전략 변경 근거)
- `docs/project-plan.md` — Phase 3 Stages 7단계 갱신
- `docs/project-context.md` — llm_cache.db, 디렉터리 구조 갱신
- `docs/project-tasks.md` — 0/23 Tasks, Key Decisions 16-18번

### DB 현황
- books=1, spans=341, kus=997, chroma=997, gens=2, edges=0

## Remaining / TODO
- [ ] **Git 커밋**: Phase 3 설계 문서 개정 (dev-docs + project-overall)
- [ ] **Phase 3 Stage H.infra 실행 착수**

## Key Decisions
- **Pilot First 전략 채택**: 87권 일괄 → 4권 파일럿(도메인당 1권) → Quality Gate → 전체 확장. 검증 전 리스크 노출 $55-95 (기존 $150-300의 1/3)
- **LLM 응답 캐시 도입**: `src/ingest/llm_cache.py` + `data/llm_cache.db`. hash(model+prompt+text) 키. 재실행 비용 $0
- **KU + Graph 함께 파일럿 검증**: end-to-end 품질 확인, 별도 검증 대비 판단 포인트 축소
- **파일럿 도서 선정**: 도메인당 1권, 경제는 기존 재사용. 구체적 도서는 카탈로그 생성 후 결정
- **Quality Gate 메트릭**: parse 성공률 ≥95%, claim 존재율 ≥80%, edge 적합도 ≥60-70%

## Context
다음 세션에서는 답변에 한국어를 사용하세요.

### 프로젝트 핵심 참조
- **마스터플랜**: `docs/masterplan-v2.0.md`
- **Phase 3 dev-docs**: `docs/phases/phase-3/` (plan, context, tasks, design-notes) — **이번 세션에서 전면 개정됨**
- **개정 계획 파일**: `C:\Users\User\.claude\plans\async-conjuring-allen.md` (Pilot First 상세 계획)
- **기술 스택**: Python 3.12, SQLite, ChromaDB, Typer CLI, GPT-4.1-mini
- **OpenAI API**: `.env` 파일에 OPENAI_API_KEY 설정됨

### 외부 데이터 소스 (Phase 3 필수)
- **87권 text.json**: `C:\Projects-2026\maintenance\books-final-processor\data\output\text\`
- **도서 목록 CSV**: `C:\Projects-2026\maintenance\books-final-processor\docs\100권 노션 원본_수정.csv` (utf-8-sig)

### Phase 3 전체 흐름
```
H.infra ($0) → H.pilot ($45-75) → I.pilot ($10-20) → Quality Gate
                                                         ├─ PASS → H.full ($80-150) → I.full ($40-80) → J ($0)
                                                         └─ FAIL → 프롬프트 튜닝 → 재실행 (캐시 $0)
```

### Phase 3 핵심 코드 수정 포인트
- `src/ingest/ku_extractor.py` line 154: `domain_short = "econ"` → `DOMAIN_SHORT_MAP.get(domain, ...)`
- `src/vault/renderer.py` line 42: `domain_dir` → `_domain_to_dir(domain)` 적용
- `config.yaml`: `books` 섹션 제거, `paths.catalog`, `batch` 섹션 추가
- **신규**: `src/ingest/llm_cache.py` — LLM 응답 캐시

### 디렉터리 구조
```
src/
├── __init__.py
├── cli.py              # Typer CLI (G.1)
├── db/
│   ├── models.py        # SQLite CRUD (5 tables) — edge CRUD 추가 필요
│   └── vectors.py       # ChromaDB wrapper
├── ingest/
│   ├── ku_extractor.py  # KU extraction — domain_short 수정 필요 (H.3)
│   ├── pdf_parser.py    # JSON parser — ingest_book() 재사용
│   └── llm_cache.py     # LLM 응답 캐시 — 신규 (H.cache)
├── search/
│   └── vector.py        # 벡터 검색
├── generation/
│   ├── content.py       # 콘텐츠 생성 파이프라인
│   └── templates/       # blog, summary, thread
├── graph/               # 신규 (I.pilot)
│   ├── edge_builder.py  # edge 생성
│   ├── traversal.py     # 그래프 탐색
│   └── dispute.py       # Dispute axis (I.full)
└── vault/
    └── renderer.py      # KU 마크다운 렌더러 — 경로 수정 필요 (H.4)
```

### Phase 3 완료 기준
- `ks stats` → books=87, spans≥25,000, kus≥75,000, chroma≥75,000
- `ks explore ku-id --depth 2` → 연결된 KU 탐색
- `ks generate idea --mode business --domains 경제/경영,과학/기술` → 아이디어 생성
- 4개 도메인 간 dispute 축 자동 식별

## Next Action
**Git 커밋 → Phase 3 Stage H.infra 실행 착수**
- `git commit` — Phase 3 설계 문서 개정 (7파일)
- H.infra 착수: H.1 북 카탈로그 생성부터 시작
