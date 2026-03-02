# Phase 3: Partially-Full (카테고리당 3권) — Tasks
> Last Updated: 2026-03-02

## Progress: 20/27 Tasks (74%)

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

### Stage H.pilot: 파일럿 인제스트 (~$1) — 3/3 ✅

- [x] H.6p 배치 처리 스크립트 (`scripts/batch_ingest.py`) — `ab78087`
  - `books_catalog.yaml` 읽기 → status 기반 필터링
  - CLI 옵션: `--pilot` (status=pilot만), `--books <ids>`, `--domain`, `--all`
  - ThreadPoolExecutor 병렬 LLM 호출, WAL 모드, --workers 옵션
  - 진행 추적: `logs/batch_progress.json` (북 단위 체크포인트)
  - LLM 캐시 통합
- [x] H.7p 파일럿 3권 인제스트 실행 — `3898df8`
  - 1,383 spans → 4,875 KUs (3권 신규)
  - DB 총계: books=4, spans=1,724, kus=5,872, chroma=5,872
- [x] H.8p 파일럿 KU 품질 리포트 생성 — `3898df8`
  - `reports/pilot_quality.md` 출력
  - Quality Gate PASS

---

### Stage I.pilot: 파일럿 그래프 (실측 ~$3) — 5/5 ✅

- [x] I.1p `src/graph/edge_builder.py` — edge 생성 모듈 — `78d75b8`
  - `src/db/models.py`에 edge CRUD 3함수 추가
  - 2-Tier 후보 선정 (within-book 0.7 + cross-domain 0.35) → LLM 관계 판정
  - 6 edge 타입, strength, source('auto'), description 포함
  - LLM 캐시 적용
- [x] I.2p 파일럿 edge 생성 실행 — `eaa9165`
  - 13,643 후보 → **11,662 edges** (85.5% 성공률)
  - 소요 60분, gpt-4.1-mini, workers=5
  - SQLite 멀티쓰레드 버그 수정 (KU pre-load 패턴)
- [x] I.3p `src/graph/traversal.py` — 그래프 탐색 — `78d75b8`
  - BFS + PathScore (HarmonicMean × Mean confidence)
- [x] I.4p CLI `ks explore` 명령 추가 — `78d75b8`
  - `explore ku-econ-001-0001 --depth 2` → 7노드 탐색 확인
- [x] I.5p 파일럿 그래프 품질 리포트 — `eaa9165`
  - `reports/pilot_graph.md` — **Quality Gate PASS**
  - Edge/KU=1.99, 6종 타입 다양성, 샘플 적합도 100%

---

### Quality Gate: 품질 판정 ✅ PASS

| # | 메트릭 | 목표 | 실측 | 결과 |
|---|--------|------|------|------|
| 1 | 도메인별 parse 성공률 | ≥ 95% | 100% | ✅ |
| 2 | 도메인별 claim 존재율 | ≥ 80% | 100% | ✅ |
| 3 | within-book edge 적합도 | ≥ 70% (10건) | 6/6 (100%) | ✅ |
| 4 | Edge 성공률 | ≥ 80% | 85.5% | ✅ |
| 5 | Edge/KU 비율 | ≥ 1.0 | 1.99 | ✅ |

**참고:** cross-domain edge 0건 (후보 35건 전부 LLM 거부) — I.partial에서 전용 전략 개선

---

### Stage H.partial: 추가 8권 인제스트 (~$2.2) — 2/2 ✅

- [x] H.9 카테고리당 추가 2권 선정 + 인제스트 실행
  - 8권 → 12,801 KUs 추출 (parse rate 98.6~100%)
  - 역사/사회: hist-003(2030축의전환), hist-014(노동의시대는끝났다)
  - 경제/경영: econ-014(경영의모험), econ-022(내러티브경제학)
  - 인문/자기계발: humn-001(12가지인생의법칙), humn-010(나는왜이일을하는가)
  - 과학/기술: sci-003(AI지도책), sci-010(그리드)
- [x] H.10 12권 전체 검증 + Vault 재렌더링
  - `ks stats` → books=12, spans=5,834, kus=18,673, chroma=18,673
  - 4개 도메인 × 3권 = 12권 확인
  - 도메인별 KU 분포: 역사 5,349 / 경제 4,647 / 과학 4,350 / 인문 4,327

---

### Stage I.partial: 12권 edge 생성 (~$5-10) — 4/4 ✅

- [x] I.6 신규 8권 within-book edge 생성
  - `python scripts/build_edges.py` — 39,886 within-book + 737 cross-book same-domain edges
- [x] I.7 cross-domain edge 전략 개선 + 생성
  - 2,996 cross-domain edges 생성 완료
  - 4개 도메인 간 교차 edge 생성
- [x] I.8 Vault connections 업데이트
  - `renderer.py`의 `## Connections` 섹션에 실제 edge 기반 [[wikilink]]
- [x] I.9 Dispute axis 자동 요약
  - `src/graph/dispute.py` 신규 생성 — contradicts 3,668건 → 80 클러스터 → LLM 요약
  - CLI `ks dispute build/list` 추가
  - `reports/dispute_axes.md` 리포트 생성 (80개 논쟁 축)
  - AgglomerativeClustering (cosine, threshold=0.5, MIN_CLUSTER_SIZE=10)
  - dry-run 모드로 비용 사전 확인 가능

---

### Stage J: Generation 확장 + Hybrid Search ($0-1) — 0/3

- [ ] J.1 `src/search/hybrid.py` — Vector + Graph 복합 검색
  - Vector Search로 시드 KU → Graph 1-2 hop 확장
  - PathScore 기반 re-ranking
- [ ] J.2 `src/generation/idea.py` — 아이디어 생성 파이프라인
  - business: 비즈니스 모델/서비스 아이디어
  - content: 콘텐츠 시리즈/주제 기획
  - serendipity: 랜덤 cross-domain 조합
- [ ] J.3 CLI `ks generate idea` + 통합 테스트

---

### Stage K: 성능 평가 + 로직 개선 ($1-3) — 0/4

- [ ] K.1 콘텐츠 생성 품질 평가
  - 다양한 토픽 10건+ 생성 → 품질 평가 (게시 가능성)
  - KU 출처 추적 정확도 확인
- [ ] K.2 아이디어 생성 평가
  - business/content/serendipity 각 모드 5건+ 생성
  - 실행 가능성 정성 평가
- [ ] K.3 Cross-domain 가치 평가
  - 단일 도메인 vs cross-domain 검색 비교
  - cross-domain edge 품질 샘플링
- [ ] K.4 로직 개선 실행 (필요 시)
  - KU 추출 프롬프트 튜닝
  - Edge 전략 보정
  - 생성 템플릿 다양화
  - 개선 사항 Phase 4 반영 계획 수립

---

## Stage 의존성

```
Phase 2 (완료) → H.infra ✅ → H.pilot ✅ → I.pilot ✅ → Quality Gate ✅
                                                           ↓ PASS
                                          H.partial (H.9→H.10) → I.partial (I.6→I.7→I.8, I.7→I.9)
                                                                                    ↓
                                                                             J (J.1→J.2→J.3)
                                                                                    ↓
                                                                    K (K.1, K.2, K.3 병렬 → K.4)
                                                                                    ↓
                                                                             Phase 4
```
