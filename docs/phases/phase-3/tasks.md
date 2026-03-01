# Phase 3: 87권 확장 + 그래프 레이어 — Tasks
> Last Updated: 2026-03-01

## Progress: 0/15 Tasks (0%)

---

### Stage H: 87권 마이그레이션 + 배치 인제스트 (L) — 0/7

- [ ] H.1 북 카탈로그 생성 (`scripts/build_catalog.py` → `books_catalog.yaml`)
  - CSV(`utf-8-sig`) + JSON 파일 목록 매칭 (87/87 매칭 확인)
  - 도메인별 book_id 할당: econ-thinking-001(기존) + econ-002~028, hist-001~018, humn-001~018, sci-001~023
  - domain_short_map 포함
  - 기존 경제학자의 생각법: `status: done`
- [ ] H.2 데이터 마이그레이션 (`scripts/migrate_data.py`)
  - 소스: `C:\Projects-2026\maintenance\books-final-processor\data\output\text\`
  - 대상: `data/raw/{도메인-하이픈}/` (4개 디렉터리)
  - 87개 파일 복사, 이미 존재 시 스킵 (멱등)
  - 검증: 87파일 존재 + JSON 파싱 가능
- [ ] H.3 `ku_extractor.py` domain_short 파라미터화
  - `DOMAIN_SHORT_MAP` 상수 추가 (모듈 상단)
  - line 154: `domain_short = "econ"` → `DOMAIN_SHORT_MAP.get(domain, ...)`
  - 기존 `domain="경제"` 레거시 호환 유지
- [ ] H.4 `renderer.py` 슬래시 도메인 경로 처리
  - `_domain_to_dir(domain)` 헬퍼: `역사/사회` → `역사-사회`
  - line 42: `domain_dir = output_dir / "domains" / _domain_to_dir(domain)`
- [ ] H.5 `config.yaml` 수정 + 기존 DB 도메인 통일
  - `books` 섹션 제거, `paths.catalog`, `batch` 섹션 추가
  - 기존 DB: `UPDATE books SET domain='경제/경영' WHERE domain='경제'`
  - 기존 DB: `UPDATE knowledge_units SET domain='경제/경영' WHERE domain='경제'`
  - 기존 `vault/domains/경제/` 삭제 → 재렌더링 대상
- [ ] H.6 배치 처리 스크립트 (`scripts/batch_ingest.py`)
  - `books_catalog.yaml` 읽기 → pending 책 순회
  - 1권당: `ingest_book()` → `extract_kus_from_spans()` → 진행 업데이트
  - 진행 추적: `logs/batch_progress.json` (북 단위 체크포인트)
  - CLI 옵션: `--domain`, `--from-book`, `--retry-failed`, `--dry-run`, `--status`
  - 에러 격리: 1권 실패 → 로그 기록 후 다음 권 계속
  - API rate limit: `delay_between_spans=0.5`, `delay_between_books=2.0`
- [ ] H.7 전체 검증 + Vault 재렌더링
  - `ks stats` → books=87, spans≥25,000, kus≥75,000
  - 4개 도메인 Vault 디렉터리 구조 확인
  - 2~3권 시범 실행 → 전체 실행 → 최종 검증

---

### Stage I: Graph Layer (M) — 0/5

- [ ] I.1 `src/graph/edge_builder.py` — within-book edge 생성
  - 같은 책 KU 간 관계를 LLM으로 자동 제안
  - 배치 처리: 책 단위 → KU 쌍 후보 → LLM 관계 판정
  - edge 6타입: explains, supports, contradicts, extends, example_of, analogous_to
- [ ] I.2 cross-domain edge 생성
  - 임베딩 유사도(>0.7)로 후보 추출 → LLM 관계 타입 판정
  - 도메인 A의 KU → 다른 도메인에서 유사 KU 검색 → edge 제안
- [ ] I.3 `src/graph/traversal.py` — 그래프 탐색
  - depth N hop 탐색
  - PathScore = HarmonicMean(edge_strengths) × Mean(KU_confidence)
- [ ] I.4 CLI `ks explore` + Vault connections 업데이트
  - `ks explore ku-id --depth 2` — 연결 KU 시각화
  - Vault markdown에 `## Connections` 섹션 자동 업데이트
- [ ] I.5 Dispute axis 자동 요약
  - contradicts edge 클러스터 분석
  - LLM으로 논쟁 축 요약 생성
  - `vault/disputes/` 디렉터리에 출력

---

### Stage J: Generation 확장 + Hybrid Search (M) — 0/3

- [ ] J.1 `src/search/hybrid.py` — Vector + Graph 복합 검색
  - Vector Search로 시드 KU → Graph 1-2 hop 확장
  - PathScore 기반 순위 매기기
- [ ] J.2 `src/generation/idea.py` — 아이디어 생성 파이프라인
  - business: 비즈니스 모델/서비스 아이디어
  - content: 콘텐츠 시리즈/주제 기획
  - serendipity: 랜덤 cross-domain 조합
- [ ] J.3 CLI `ks generate idea` + 통합 테스트
  - `ks generate idea --mode business --domains 경제/경영,과학/기술`
  - E2E 테스트: 아이디어 생성 → KU 역참조 확인

---

## Stage 의존성

```
Phase 2 (완료) ──→ H.1~H.5 (병렬 가능) ──→ H.6 ──→ H.7 ──→ I.1 ──→ I.2 ──→ I.3 ──→ I.4~I.5
                                                                                        ↓
                                                                                  J.1 ──→ J.2 ──→ J.3
```
