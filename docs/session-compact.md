# Session Compact

> Generated: 2026-03-01 (Session 24)
> Source: Phase 3 H.pilot — 병렬 LLM 호출 구현 + 검증 완료

## Goal
Phase 3 Stage H.pilot 진행 — span-level 병렬 LLM 호출 도입으로 인제스트 성능 개선 (46분 → ~10분), 이후 H.7p 파일럿 3권 실제 인제스트 실행.

## Completed
- [x] **Session 22-23 작업** (이전 세션): H.infra 6/6 완료, 파일럿 3권 선정, batch_ingest.py 작성
- [x] **병렬 LLM 호출 구현** (4개 파일 수정)
  - `src/ingest/llm_cache.py` — WAL 모드 + timeout=30 적용 (병렬 캐시 접근 안전)
  - `src/ingest/ku_extractor.py` — `_process_span_llm()` 신규 함수, `ThreadPoolExecutor` 병렬 처리, `max_workers` 파라미터
  - `scripts/batch_ingest.py` — `--workers N` CLI 옵션, `_ingest_one_book()`/`run_batch()`에 max_workers 전달 체인
  - `config.yaml` — `batch.max_workers: 5` 기본값 추가
- [x] **검증 통과**
  - Import 테스트 OK
  - `--pilot --dry-run` OK (3권, workers=5 표시)
  - `--books econ-thinking-001 --workers 5 --dry-run` OK

## Current State
**Phase 3 Stage H.pilot: 병렬화 구현 완료, 커밋 대기 → H.7p 실행 대기.**

### 커밋 히스토리
```
b836f7f phase-3 Stage H.infra: 87권 확장 인프라 준비
3e4870f docs: 비용 추정치 실측 데이터 기반 수정 ($175-325 → ~$36-49)
d5ef001 docs: phase-3 설계 문서 개정 (Pilot First 전략)
```
(Session 23-24 변경사항 아직 미커밋)

### DB 현황
- books=1, spans=341, kus=997, chroma=997, gens=2, edges=0
- 도메인: `경제/경영` (기존 1권만)

### 파일 시스템 현황
- `books_catalog.yaml`: 87개 도서 (done=1, pilot=3, pending=83)
- `data/raw/`: 4개 디렉터리 = 87개 JSON
- `vault/domains/경제-경영/`: 997개 KU 마크다운

### 변경된 파일 (미커밋)
- `docs/phases/phase-3/tasks.md` — H.infra 6/6 체크 표시 + Progress 26%
- `books_catalog.yaml` — 3권 status=pilot 설정
- `scripts/batch_ingest.py` — 배치 인제스트 (신규 H.6p) + --workers 옵션
- `src/ingest/llm_cache.py` — WAL 모드 추가
- `src/ingest/ku_extractor.py` — 병렬 LLM 호출 (_process_span_llm + ThreadPoolExecutor)
- `config.yaml` — batch.max_workers: 5 추가
- `docs/session-compact.md` — 이 파일

### 병렬화 설계 핵심
- **전략**: "병렬 LLM 호출 → 순차 DB 저장" — ThreadPoolExecutor로 I/O-bound LLM 호출만 병렬, 결과를 span 원래 순서대로 모아서 ku_seq 순차 부여 + insert_ku() 순차 호출
- **하위 호환**: max_workers=1이면 기존 순차 방식과 동일 (delay 적용)
- **우선순위**: CLI --workers > config.yaml batch.max_workers > 기본값 1
- **충돌 방지**: LLM 캐시 DB에 WAL 모드 + timeout=30, knowledge.db는 LLM 후 순차 접근만

### 파일럿 Dry-run 결과
| 도서 | 도메인 | Spans | 예상 KUs |
|------|--------|-------|----------|
| 공정하다는 착각 | 인문/자기계발 | 391 | ~1,000+ |
| 노이즈 | 역사/사회 | 613 | ~1,500+ |
| 대량살상 수학무기 | 과학/기술 | 379 | ~900+ |
| **합계** | | **1,383** | **~3,400+** |

## Remaining / TODO
- [ ] **Git 커밋**: Session 23-24 변경사항 (병렬화 + batch_ingest + catalog + tasks)
- [ ] **H.7p 파일럿 3권 인제스트 실행** (~$1)
  - `python scripts/batch_ingest.py --pilot` (기본 workers=5)
  - 예상: 1,383 API 호출, ~10분 소요 (병렬화 후)
  - 진행 추적: `logs/batch_progress.json`
- [ ] **H.8p 파일럿 KU 품질 리포트**
  - 도메인별: KU 수, parse 성공률, claim 존재율, 태그 분포
  - `reports/pilot_quality.md` 출력
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
H.infra ($0) ✅ → H.pilot (~$1) ← 현재 위치 → I.pilot ($2-5) → Quality Gate
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
**Git 커밋 → H.7p 파일럿 3권 인제스트 실행**
1. Session 23-24 변경사항 Git 커밋
2. `PYTHONUTF8=1 python scripts/batch_ingest.py --pilot` 실행 (workers=5 기본)
3. 완료 후 `python scripts/batch_ingest.py --status`로 결과 확인
4. H.8p 품질 리포트 작성
