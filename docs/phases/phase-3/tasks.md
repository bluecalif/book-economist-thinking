# Phase 3: 87권 확장 + 그래프 레이어 — Tasks
> Last Updated: 2026-03-01

## Progress: 6/23 Tasks (26%)

---

### Stage H.infra: 인프라 준비 (API 비용 $0) — 6/6 ✅

- [x] H.1 북 카탈로그 생성 (`scripts/build_catalog.py` → `books_catalog.yaml`)
  - CSV(`utf-8-sig`) + JSON 파일 목록 매칭 (87/87 확인됨)
  - 도메인별 book_id 할당: econ-thinking-001(기존) + econ-002~028, hist-001~018, humn-001~018, sci-001~023
  - status 필드: done(기존 1권), pilot(도메인당 1권), pending(나머지)
  - domain_short_map 포함
- [x] H.2 데이터 마이그레이션 (`scripts/migrate_data.py`)
  - 소스: `C:\Projects-2026\maintenance\books-final-processor\data\output\text\`
  - 대상: `data/raw/{도메인-하이픈}/` (4개 디렉터리)
  - 87개 파일 복사, 이미 존재 시 스킵 (멱등)
  - 검증: 87파일 존재 + JSON 파싱 가능
- [x] H.3 `ku_extractor.py` domain_short 파라미터화
  - `DOMAIN_SHORT_MAP` 상수 추가 (모듈 상단)
  - line 154: `domain_short = "econ"` → `DOMAIN_SHORT_MAP.get(domain, ...)`
  - 기존 `domain="경제"` 레거시 호환 유지
- [x] H.4 `renderer.py` 슬래시 도메인 경로 처리
  - `_domain_to_dir(domain)` 헬퍼: `역사/사회` → `역사-사회`
  - line 42: `domain_dir = output_dir / "domains" / _domain_to_dir(domain)`
- [x] H.5 `config.yaml` 수정 + 기존 DB 도메인 통일
  - `books` 섹션 제거, `paths.catalog`, `batch` 섹션 추가
  - 기존 DB: `UPDATE books SET domain='경제/경영' WHERE domain='경제'`
  - 기존 DB: `UPDATE knowledge_units SET domain='경제/경영' WHERE domain='경제'`
  - 기존 `vault/domains/경제/` → `경제-경영/`으로 재렌더링
- [x] H.cache LLM 응답 캐시 레이어 (`src/ingest/llm_cache.py`)
  - 캐시 키: `hash(model + system_prompt + user_prompt_text)`
  - 저장소: `data/llm_cache.db` (SQLite)
  - cache hit → DB 응답 반환 ($0), cache miss → API 호출 + 저장
  - `ku_extractor.py`의 `call_llm()` 호출을 캐시 래퍼로 교체
  - 임베딩 캐시: ChromaDB에 이미 있으면 skip
  - 단위 테스트 포함

---

### Stage H.pilot: 파일럿 인제스트 (~$1) — 0/3

- [ ] H.6p 배치 처리 스크립트 (`scripts/batch_ingest.py`)
  - `books_catalog.yaml` 읽기 → status 기반 필터링
  - CLI 옵션: `--pilot` (status=pilot만), `--books <ids>`, `--domain`, `--all`
  - CLI 옵션: `--dry-run`, `--status`, `--retry-failed`
  - 진행 추적: `logs/batch_progress.json` (북 단위 체크포인트)
  - 에러 격리: 1권 실패 → 로그 기록 후 다음 권 계속
  - API rate limit: `delay_between_spans=0.5`, `delay_between_books=2.0`
  - LLM 캐시 통합
- [ ] H.7p 파일럿 3권 인제스트 실행
  - `python scripts/batch_ingest.py --pilot` 실행
  - 기존 econ-thinking-001은 skip (status=done)
  - 역사/사회, 인문/자기계발, 과학/기술 각 1권 신규 인제스트
- [ ] H.8p 파일럿 KU 품질 리포트 생성
  - 도메인별: KU 수, parse 성공률, claim 존재율, 태그 분포, claim 길이 분포
  - counter_summary 비율 (논증형 도서 검증)
  - `reports/pilot_quality.md` 출력

---

### Stage I.pilot: 파일럿 그래프 (추정 $2-5) — 0/5

- [ ] I.1p `src/graph/edge_builder.py` — edge 생성 모듈
  - `src/db/models.py`에 edge CRUD 헬퍼 추가 (insert_edge, list_edges_by_ku 등)
  - within-book: 같은 책 KU 쌍 → 임베딩 유사도 > 0.7 필터 → LLM 관계 판정
  - cross-domain: 다른 도메인 KU 간 유사도 후보 → LLM 판정
  - 6 edge 타입: explains, supports, contradicts, extends, example_of, analogous_to
  - strength, source('auto'), description 필드 포함
  - LLM 캐시 적용
- [ ] I.2p 파일럿 edge 생성 실행
  - within-book: 4-5권 각각 실행
  - cross-domain: 4개 도메인 간 교차 실행
  - 예상: 200-500 edges
- [ ] I.3p `src/graph/traversal.py` — 그래프 탐색
  - depth N hop 탐색
  - PathScore = HarmonicMean(edge_strengths) × Mean(KU_confidence)
  - 입력: seed KU ID + depth → 연결 KU 리스트 반환
- [ ] I.4p CLI `ks explore` 명령 추가
  - `ks explore <ku-id> --depth 2`
  - Rich table로 연결 KU 표시 (relation_type, strength, domain)
- [ ] I.5p 파일럿 그래프 품질 리포트
  - edge 수 (within vs cross), 도메인 쌍별 분포, 타입 분포
  - 샘플 10건 수동 검토용 출력
  - `reports/pilot_graph.md` 출력

---

### Quality Gate: 품질 판정

| # | 메트릭 | 목표 | 불합격 시 |
|---|--------|------|-----------|
| 1 | 도메인별 parse 성공률 | ≥ 95% | 프롬프트 조정 → 재실행 (캐시 히트 $0) |
| 2 | 도메인별 claim 존재율 | ≥ 80% | claim 추출 가이드라인 추가 |
| 3 | cross-domain edge 적합도 | ≥ 60% (10건) | 유사도 threshold 상향 |
| 4 | within-book edge 적합도 | ≥ 70% (10건) | edge 프롬프트 조정 |

---

### Stage H.full: 나머지 83권 배치 (~$23) — 0/2

- [ ] H.9 나머지 83권 배치 인제스트
  - `python scripts/batch_ingest.py --all` (done/pilot 자동 skip)
  - 도메인별 분할 실행 가능 (`--domain`)
  - 예상 시간: 4-6시간
- [ ] H.10 전체 검증 + Vault 재렌더링
  - `ks stats` → books=87, spans≥25,000, kus≥75,000
  - 4개 도메인 Vault 디렉터리 구조 확인
  - 도메인별 KU 분포 균형 확인

---

### Stage I.full: 전체 그래프 + Dispute (추정 $10-20) — 0/4

- [ ] I.6 전체 within-book edge 생성
  - 87권 각각 실행 (파일럿 done 자동 skip)
- [ ] I.7 전체 cross-domain edge 생성
  - 4개 도메인 간 교차 edge 생성
- [ ] I.8 Vault connections 업데이트
  - `renderer.py`의 `## Connections` 섹션에 실제 edge 기반 링크 생성
  - 현재 "(Phase 3에서 edges 기반 자동 생성)" → 실제 [[wikilink]] 교체
- [ ] I.9 Dispute axis 자동 요약
  - `src/graph/dispute.py` 신규 생성
  - contradicts edge 클러스터 → LLM 논쟁 축 요약
  - `vault/disputes/` 출력

---

### Stage J: Generation 확장 + Hybrid Search ($0) — 0/3

- [ ] J.1 `src/search/hybrid.py` — Vector + Graph 복합 검색
  - Vector Search로 시드 KU → Graph 1-2 hop 확장
  - PathScore 기반 re-ranking
- [ ] J.2 `src/generation/idea.py` — 아이디어 생성 파이프라인
  - business: 비즈니스 모델/서비스 아이디어
  - content: 콘텐츠 시리즈/주제 기획
  - serendipity: 랜덤 cross-domain 조합
  - `src/generation/content.py` 패턴 참조
- [ ] J.3 CLI `ks generate idea` + 통합 테스트
  - `ks generate idea --mode business --domains 경제/경영,과학/기술`
  - E2E 테스트: 아이디어 생성 → KU 역참조 확인

---

## Stage 의존성

```
Phase 2 (완료) → H.infra (H.1~H.5, H.cache 병렬) → H.pilot (H.6p→H.7p→H.8p)
                                                                    ↓
                                                        I.pilot (I.1p→I.2p→I.3p→I.4p)
                                                               I.2p→I.5p
                                                                    ↓
                                                             Quality Gate
                                                                    ↓ PASS
                                                    H.full (H.9→H.10) → I.full (I.6→I.7→I.8, I.7→I.9)
                                                                                        ↓
                                                                                 J (J.1→J.2→J.3)
```
