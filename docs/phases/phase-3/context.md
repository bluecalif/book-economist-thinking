# Phase 3: 87권 확장 + 그래프 레이어 — Context
> Last Updated: 2026-03-02

## 1. 핵심 파일

### 수정 대상

| 파일 | 변경 내용 |
|------|-----------|
| `src/ingest/ku_extractor.py` | `DOMAIN_SHORT_MAP` 상수 추가, line 154 `domain_short` 파라미터화, `llm_cache` 통합 |
| `src/vault/renderer.py` | `_domain_to_dir()` 헬퍼 추가, line 42 도메인 경로 수정, Connections 섹션 실제 링크 |
| `src/cli.py` | `ks explore`, `ks generate idea` 명령 추가 |
| `src/db/models.py` | edge CRUD 헬퍼 함수 추가 (insert_edge, list_edges_by_ku 등) |
| `config.yaml` | `books` 섹션 제거 → `catalog`, `batch` 섹션 추가 |

### 신규 생성

| 파일 | 용도 | Stage |
|------|------|-------|
| `src/ingest/llm_cache.py` | **LLM 응답 캐시** (비용 절감 핵심) | H.infra |
| `books_catalog.yaml` | 87권 메타데이터 카탈로그 | H.infra |
| `scripts/build_catalog.py` | CSV + JSON → 카탈로그 생성 | H.infra |
| `scripts/migrate_data.py` | text.json 복사 스크립트 | H.infra |
| `scripts/batch_ingest.py` | 배치 처리 (--pilot/--all 모드) | H.pilot |
| `src/graph/__init__.py` | graph 패키지 초기화 | I.pilot |
| `src/graph/edge_builder.py` | edge 자동 생성 | I.pilot |
| `src/graph/traversal.py` | 그래프 탐색 (depth N hop) | I.pilot |
| `src/graph/dispute.py` | Dispute axis 자동 요약 | I.full |
| `src/generation/idea.py` | 아이디어 생성 (3모드) | J |
| `src/search/hybrid.py` | Vector + Graph 복합 검색 | J |

### 참조 (읽기 전용)

| 파일 | 용도 |
|------|------|
| `src/ingest/pdf_parser.py` | `ingest_book()` 함수 — 배치에서 재사용 |
| `src/db/models.py` | CRUD 헬퍼 — INSERT OR IGNORE 멱등성 |
| `src/db/vectors.py` | ChromaDB 래퍼 — 배치 임베딩 |
| `src/search/vector.py` | 벡터 검색 — hybrid search 기반 |
| `src/generation/content.py` | 콘텐츠 생성 — idea.py 참고 모델 |

### 외부 참조 (1회성)

| 파일 | 용도 |
|------|------|
| `C:\Projects-2026\maintenance\books-final-processor\docs\100권 노션 원본_수정.csv` | 87권 메타데이터 소스 |
| `C:\Projects-2026\maintenance\books-final-processor\data\output\text\*.json` | 87권 text.json 소스 |

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

### Book ID 패턴

| 도메인 | book_id 범위 | 권수 |
|--------|-------------|-----|
| 경제/경영 | `econ-thinking-001` (기존) + `econ-002`~`econ-028` | 28 |
| 역사/사회 | `hist-001`~`hist-018` | 18 |
| 인문/자기계발 | `humn-001`~`humn-018` | 18 |
| 과학/기술 | `sci-001`~`sci-023` | 23 |

### KU ID 패턴

```
ku-{domain_short}-{book_seq}-{ku_seq:04d}
예: ku-hist-003-0042
```

### LLM 캐시 스키마 (신규)

```sql
-- data/llm_cache.db
CREATE TABLE llm_cache (
    cache_key   TEXT PRIMARY KEY,  -- hash(model + system_prompt + user_prompt)
    response    TEXT NOT NULL,      -- LLM raw response
    model       TEXT NOT NULL,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**동작 원리:**
- cache hit → DB에서 응답 반환 (API 호출 $0)
- cache miss → API 호출 + DB 저장
- 프롬프트 변경 시 → 해시 달라지므로 자동으로 새 호출 (명시적 무효화 불필요)
- edge 생성 LLM 호출에도 동일 캐시 적용

### text.json 스키마 (입력)

```json
{
  "book_id": 199,
  "book_title": "경제학자의 생각법",
  "metadata": {
    "total_pages": 400,
    "main_start_page": 17,
    "main_end_page": 370,
    "chapter_count": 5
  },
  "text_content": {
    "chapters": [
      {
        "order_index": 0,
        "chapter_number": 1,
        "title": "챕터명",
        "start_page": 17,
        "end_page": 90,
        "pages": [
          {"page_number": 17, "text": "..."}
        ]
      }
    ]
  }
}
```

### books_catalog.yaml 스키마

```yaml
domain_short_map:
  역사/사회: hist
  경제/경영: econ
  인문/자기계발: humn
  과학/기술: sci

books:
  - id: econ-thinking-001
    title: "경제학자의 생각법"
    domain: "경제/경영"
    domain_short: econ
    author: "이완배"
    year: 2021
    json_path: "data/raw/경제-경영/55bbe4_경제학자의_생각법_text.json"
    status: done          # done|pilot|pending|in_progress|failed
```

### 데이터 디렉터리 구조 (목표)

```
data/
├── knowledge.db          (87권 데이터)
├── llm_cache.db          (LLM 응답 캐시 — 신규)
├── chroma/               (75,000+ embeddings)
└── raw/
    ├── 역사-사회/         (18권 text.json)
    ├── 경제-경영/         (28권 text.json)
    ├── 인문-자기계발/     (18권 text.json)
    └── 과학-기술/         (23권 text.json)

vault/domains/
├── 역사-사회/
├── 경제-경영/
├── 인문-자기계발/
└── 과학-기술/
```

### 배치 진행 추적 (`logs/batch_progress.json`)

```json
{
  "total": 87, "done": 45, "failed": 1, "pilot": 4,
  "books": {
    "econ-thinking-001": {"status": "done", "spans": 341, "kus": 997, "completed_at": "..."},
    "hist-001": {"status": "done", "spans": 287, "kus": 831, "completed_at": "..."},
    "econ-002": {"status": "failed", "error": "...", "failed_at": "..."}
  }
}
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
| 7 | **Pilot First 전략** | 비경제 도메인 KU 품질 미검증, 비용 리스크 1/3 감소 |
| 8 | **LLM 응답 캐시 도입** | 재실행 비용 $0, 프롬프트 튜닝 안전성 확보 |
| 9 | **KU + Graph 함께 파일럿 검증** | end-to-end 품질 확인, 별도 검증 대비 판단 포인트 축소 |
| 10 | **SQLite 멀티쓰레드 해법: KU pre-load** | conn 객체 쓰레드 공유 불가 → 메인 쓰레드에서 KU dict 로드 후 전달 |
| 11 | **Cross-domain edge 전략 재검토 필요** | threshold=0.35에서 후보 35건, LLM 전부 거부 → 전용 전략 필요 |
| 12 | **Strength 실질 이진 판단** | LLM이 관계 인정 시 99.1%가 0.7+ → threshold 의미 제한적 |

---

## 4. 컨벤션 체크리스트

### 아키텍처 (masterplan §3)
- [x] L0 Raw → L1 KU → L2 Graph → L3 Generation 순서 준수
- [x] CLI 명령어 체계 유지 (ks ingest, search, explore, generate)
- [x] `ks explore` 명령 추가 완료 (I.4p)
- [ ] J에서 `ks generate idea` 명령 추가 예정

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
