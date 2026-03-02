# Phase 3: Partially-Full (카테고리당 3권) — Context
> Last Updated: 2026-03-02

## 1. 핵심 파일

### 수정 완료

| 파일 | 변경 내용 |
|------|-----------|
| `src/ingest/ku_extractor.py` | `DOMAIN_SHORT_MAP` 상수 추가, domain_short 파라미터화, `llm_cache` 통합 |
| `src/vault/renderer.py` | `_domain_to_dir()` 헬퍼 추가, 도메인 경로 수정, Connections 섹션 실제 링크 |
| `src/cli.py` | `ks explore` 명령 추가 |
| `src/db/models.py` | edge CRUD 헬퍼 함수 추가 (insert_edge, list_edges_by_ku 등) |
| `config.yaml` | `books` 섹션 제거 → `catalog`, `batch` 섹션 추가 |

### 신규 생성 완료

| 파일 | 용도 |
|------|------|
| `src/ingest/llm_cache.py` | LLM 응답 캐시 |
| `books_catalog.yaml` | 87권 메타데이터 카탈로그 |
| `scripts/build_catalog.py` | CSV + JSON → 카탈로그 생성 |
| `scripts/migrate_data.py` | text.json 복사 스크립트 |
| `scripts/batch_ingest.py` | 배치 처리 (--pilot/--all 모드) |
| `scripts/build_edges.py` | 배치 edge 생성 |
| `src/graph/__init__.py` | graph 패키지 |
| `src/graph/edge_builder.py` | edge 생성 (쓰레드 안전) |
| `src/graph/traversal.py` | 그래프 탐색 (BFS + PathScore) |

### Changed Files (I.9)

| 파일 | 변경 내용 |
|------|-----------|
| `src/graph/dispute.py` | 신규 — contradicts edge 클러스터링 + LLM 논쟁 축 요약 |
| `src/cli.py` | `ks dispute build/list` 서브커맨드 추가, `✓` 유니코드 → 텍스트 변경 |
| `reports/dispute_axes.md` | 자동생성 — 80개 논쟁 축 리포트 |

### Changed Files (J.1~J.3)

| 파일 | 변경 내용 |
|------|-----------|
| `src/search/hybrid.py` | 신규 — Vector + Graph 복합 검색 (HybridResult, hybrid_search, format_hybrid_results_rich) |
| `src/generation/idea.py` | 신규 — 아이디어 생성 파이프라인 (IdeaResult, generate_idea, 3모드) |
| `src/generation/templates/idea_business.txt` | 신규 — 비즈니스 아이디어 프롬프트 |
| `src/generation/templates/idea_content.txt` | 신규 — 콘텐츠 시리즈 기획 프롬프트 |
| `src/generation/templates/idea_serendipity.txt` | 신규 — 세렌디피티 아이디어 프롬프트 |
| `src/cli.py` | `hsearch` + `generate idea` 명령 추가 |

### 신규 생성 예정

| 파일 | 용도 | Stage |
|------|------|-------|
| `reports/phase3_evaluation.md` | 성능 평가 리포트 | K |

### 참조 (읽기 전용)

| 파일 | 용도 |
|------|------|
| `src/ingest/pdf_parser.py` | `ingest_book()` 함수 — 배치에서 재사용 |
| `src/db/models.py` | CRUD 헬퍼 — INSERT OR IGNORE 멱등성 |
| `src/db/vectors.py` | ChromaDB 래퍼 — 배치 임베딩 |
| `src/search/vector.py` | 벡터 검색 — hybrid search 기반 |
| `src/generation/content.py` | 콘텐츠 생성 — idea.py 참고 모델 |

---

## 2. 데이터 스키마

### 도메인 매핑 (4개 카테고리)

```python
DOMAIN_SHORT_MAP = {
    "역사/사회": "hist",
    "경제/경영": "econ",
    "인문/자기계발": "humn",
    "과학/기술": "sci",
    "경제": "econ",   # 레거시 호환
}
```

### Phase 3 대상 도서 (12권) — 전체 완료

| 카테고리 | 완료 | KU 수 | 도서 |
|---------|------|-------|------|
| 역사/사회 | 3 | 5,349 | hist-016(노이즈), hist-003(2030축의전환), hist-014(노동의시대는끝났다) |
| 경제/경영 | 3 | 4,647 | econ-thinking-001(경제학자의생각법), econ-014(경영의모험), econ-022(내러티브경제학) |
| 인문/자기계발 | 3 | 4,327 | humn-006(공정하다는착각), humn-001(12가지인생의법칙), humn-010(나는왜이일을하는가) |
| 과학/기술 | 3 | 4,350 | sci-023(대량살상수학무기), sci-003(AI지도책), sci-010(그리드) |

### LLM 캐시 스키마

```sql
-- data/llm_cache.db
CREATE TABLE llm_cache (
    cache_key   TEXT PRIMARY KEY,
    response    TEXT NOT NULL,
    model       TEXT NOT NULL,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Changed Files (H.9/H.10)

| 파일 | 변경 내용 |
|------|-----------|
| `books_catalog.yaml` | 8권 status: pending → partial → done |
| `logs/batch_progress.json` | 8권 인제스트 완료 기록 추가 |
| `data/knowledge.db` | 12권 KU/spans 삽입 (18,673 KUs) |
| `data/chroma/` | 18,673 임베딩 저장 |
| `vault/domains/*/ku-*.md` | 8권 KU 마크다운 렌더링 |

### 데이터 디렉터리 구조 (Phase 3 목표)

```
data/
├── knowledge.db          (12권 데이터)
├── llm_cache.db          (LLM 응답 캐시)
├── chroma/               (~18,000 embeddings)
└── raw/
    ├── 역사-사회/         (18권 text.json — 3권 사용)
    ├── 경제-경영/         (28권 text.json — 3권 사용)
    ├── 인문-자기계발/     (18권 text.json — 3권 사용)
    └── 과학-기술/         (23권 text.json — 3권 사용)
```

---

## 3. 주요 결정사항

| # | 결정 | 근거 |
|---|------|------|
| 1 | 4개 카테고리 그대로 사용 | books-final-processor CSV 활용, 7도메인 세분화 안 함 |
| 2 | text.json 프로젝트 내 복사 (standalone) | 외부 의존 제거 |
| 3 | domain_short 매핑: hist/econ/humn/sci | KU ID 4자리 약어, 기존 econ 호환 |
| 4 | 기존 domain "경제"→"경제/경영" 통일 | 4개 카테고리 일관성 |
| 5 | 도메인 디렉터리: 슬래시→하이픈 | OS 경로 안전성 |
| 6 | GPT-4.1-mini 유지 | Phase 1-2와 동일, 비용 효율 |
| 7 | Pilot First 전략 채택 | 비경제 도메인 KU 품질 미검증, 비용 리스크 1/3 감소 |
| 8 | LLM 응답 캐시 도입 | 재실행 비용 $0, 프롬프트 튜닝 안전성 확보 |
| 9 | KU + Graph 함께 파일럿 검증 | end-to-end 품질 확인 |
| 10 | SQLite 멀티쓰레드 해법: KU pre-load | conn 객체 쓰레드 공유 불가 |
| 11 | Cross-domain edge 전략 재검토 필요 | threshold=0.35에서 후보 35건, LLM 전부 거부 |
| 12 | Strength 실질 이진 판단 | LLM이 관계 인정 시 99.1%가 0.7+ |
| **13** | **Phase 3 범위를 카테고리당 3권(12권)으로 축소** | **전체 파이프라인 완성 + 성능 평가 우선, 전체 확장은 Phase 4로** |
| **14** | **Stage K 성능 평가 추가** | **로직 개선 기회를 Phase 4 전에 확보** |
| **15** | **hybrid_score = alpha(0.6)*similarity + (1-alpha)*path_score** | **벡터 우세 가중, path_score max 정규화** |
| **16** | **serendipity 모드: DB에서 cross-domain edge 랜덤 3쌍 샘플링** | **별도 검색 없이 기존 edge 활용** |
| **17** | **기존 코드 재사용 (content.py → idea.py)** | **_build_ku_context, _append_sources, insert_generation 임포트** |

---

## 4. 컨벤션 체크리스트

### 아키텍처 (masterplan §3)
- [x] L0 Raw → L1 KU → L2 Graph → L3 Generation 순서 준수
- [x] CLI 명령어 체계 유지 (ks ingest, search, explore, generate)
- [x] `ks explore` 명령 추가 완료 (I.4p)
- [x] `ks dispute build/list` 명령 추가 완료 (I.9)
- [x] J에서 `ks hsearch`, `ks generate idea` 명령 추가 완료 (J.3)

### 지식 구조 (masterplan §5)
- [x] KU 포맷: claim + evidence_summary + counter_summary
- [x] KU ID 패턴: `ku-{domain_short}-{book_seq}-{ku_seq}`
- [x] Maturity: M0 (자동추출)

### 데이터 (masterplan §4-7)
- [x] 5개 테이블 스키마 변경 없음
- [x] ChromaDB ku_embeddings 컬렉션 재사용
- [x] edges 테이블 활성화 — 11,662 edges
- [x] edge CRUD 헬퍼 함수 models.py에 추가 완료

### 인코딩
- [x] CSV 읽기: `utf-8-sig`
- [x] 파일 쓰기: `utf-8` explicit
- [x] `PYTHONUTF8=1` 환경변수
