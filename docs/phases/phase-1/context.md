# Phase 1: 데이터 파이프라인 — Context
> Last Updated: 2026-02-28

## 1. 핵심 파일

### 생성할 소스 파일

| 파일 | 용도 | Stage |
|------|------|-------|
| `src/__init__.py` | 패키지 초기화 | A |
| `src/db/models.py` | SQLite DDL + CRUD 헬퍼 | B |
| `src/db/vectors.py` | ChromaDB 래퍼 (ku_embeddings) | B |
| `src/ingest/pdf_parser.py` | JSON/PDF → raw_spans | C |
| `src/ingest/ku_extractor.py` | raw_spans → KU (LLM API) | D |

### 참조할 기존 파일

| 파일 | 용도 |
|------|------|
| `55bbe4_경제학자의_생각법_text.json` | 주 입력 데이터 (391K, 5챕터, 400페이지) |
| `55bbe4_경제학자의_생각법_structure.json` | 챕터 메타데이터 (1.1K) |
| `55bbe48ee53666b54ce523d0ba4166b7.json` | PDF 파싱 원본 (2.2M, 보조 경로) |
| `docs/masterplan-v2.0.md` | 전체 아키텍처/스키마/로드맵 |
| `config.yaml` | 런타임 설정 (Stage A에서 생성) |

### 생성할 데이터/출력

| 경로 | 용도 |
|------|------|
| `data/knowledge.db` | SQLite 데이터베이스 |
| `data/chroma/` | ChromaDB 임베딩 저장소 |
| `data/raw/` | 원본 PDF (복사 보관) |

---

## 2. 데이터 스키마

### SQLite 테이블 (Phase 1 활성 사용: 3개 + DDL만: 2개)

#### books (활성)
```sql
CREATE TABLE books (
    id          TEXT PRIMARY KEY,   -- 'econ-thinking-001'
    title       TEXT NOT NULL,
    author      TEXT,
    domain      TEXT NOT NULL,      -- 인문|사회|역사|경제|과학|기술|경영
    filepath    TEXT,               -- 원본 PDF 경로
    total_pages INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### raw_spans (활성)
```sql
CREATE TABLE raw_spans (
    id          TEXT PRIMARY KEY,   -- 'econ-thinking-001-ch03-p042-s001'
    book_id     TEXT NOT NULL REFERENCES books(id),
    chapter     TEXT,
    page        INTEGER,
    seq         INTEGER,            -- 챕터 내 순서
    text        TEXT NOT NULL,
    span_type   TEXT DEFAULT 'paragraph',  -- paragraph|heading|list|table
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_raw_spans_book ON raw_spans(book_id);
```

#### knowledge_units (활성)
```sql
CREATE TABLE knowledge_units (
    id                  TEXT PRIMARY KEY,   -- 'ku-econ-001-0042'
    book_id             TEXT NOT NULL REFERENCES books(id),
    claim               TEXT NOT NULL,
    evidence_summary    TEXT,
    counter_summary     TEXT,
    domain              TEXT NOT NULL,
    subdomain           TEXT,
    tags                TEXT,                -- JSON array
    confidence          REAL DEFAULT 0.5,
    maturity            TEXT DEFAULT 'M0',
    source_spans        TEXT,                -- JSON array of raw_span ids
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ku_book ON knowledge_units(book_id);
CREATE INDEX idx_ku_domain ON knowledge_units(domain);
```

#### edges (DDL만, Phase 3 활성)
```sql
CREATE TABLE edges (
    id              TEXT PRIMARY KEY,
    from_ku_id      TEXT NOT NULL REFERENCES knowledge_units(id),
    to_ku_id        TEXT NOT NULL REFERENCES knowledge_units(id),
    relation_type   TEXT NOT NULL,
    strength        REAL DEFAULT 0.5,
    source          TEXT DEFAULT 'auto',
    description     TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_edges_from ON edges(from_ku_id);
CREATE INDEX idx_edges_to ON edges(to_ku_id);
CREATE INDEX idx_edges_type ON edges(relation_type);
```

#### generations (DDL만, Phase 2 활성)
```sql
CREATE TABLE generations (
    id          TEXT PRIMARY KEY,   -- 'gen-content-20260227-001'
    mode        TEXT NOT NULL,      -- content|idea
    format      TEXT,               -- blog|thread|newsletter|lecture|summary
    prompt      TEXT,
    output      TEXT NOT NULL,
    ku_ids      TEXT NOT NULL,      -- JSON array
    rating      INTEGER,            -- NULL|1|2
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### ChromaDB 컬렉션

```python
# ku_embeddings 컬렉션
collection = client.get_or_create_collection(
    name="ku_embeddings",
    metadata={"hnsw:space": "cosine"}
)
# document: claim + " " + evidence_summary
# metadata: { "ku_id": str, "domain": str, "book_id": str, "subdomain": str }
# id: ku_id
```

### ID 패턴 (Phase 1 사용분)

| 엔티티 | 패턴 | 예시 |
|--------|------|------|
| book_id | `{domain}-{title_slug}-{seq}` | `econ-thinking-001` |
| raw_span_id | `{book_id}-ch{nn}-p{nnn}-s{nnn}` | `econ-thinking-001-ch01-p042-s001` |
| ku_id | `ku-{domain}-{book_seq}-{ku_seq}` | `ku-econ-001-0042` |

### 입력 데이터 매핑 (JSON → DB)

```
text.json                          →  SQLite
─────────────────────────────────────────────────
book_id: 199                       →  books.id: "econ-thinking-001"
book_title                         →  books.title
metadata.total_pages               →  books.total_pages
chapters[].order_index             →  raw_spans.chapter (ch{nn} 형식)
chapters[].pages[].page_number     →  raw_spans.page
chapters[].pages[].text            →  raw_spans.text (페이지 단위, 1:1)
```

---

## 3. 주요 결정사항

| # | 결정 | 근거 | 대안 | 영향 |
|---|------|------|------|------|
| 1 | Raw SQL + 헬퍼 함수 | 테이블 5개, ORM 오버헤드 불필요 | SQLAlchemy ORM | models.py 구조 |
| 2 | 기존 JSON 우선 경로 | 이미 파싱된 데이터 존재 | PDF 직접 파싱 | Stage C 구현 방식 |
| 3 | edges DDL만 Phase 1 | Graph Layer는 Phase 3 | edges 완전 스킵 | DDL 생성만, CRUD 미구현 |
| 4 | GPT-4.1 mini 우선 | KU 추출 비용 효율 | GPT-4.1 | Stage D 비용/품질 |
| 5 | text-embedding-3-large | 정확도 우선 | text-embedding-3-small | Stage D 임베딩 |
| 6 | 페이지 단위 청킹 확정 (C-1) | OCR 줄바꿈이 문단 경계 미보장 | 줄바꿈 기반 분리 | Stage C 구현 |
| 7 | D.2 3단계 fallback | JSON 파싱 실패 대응 | 단순 재시도 | 추출 안정성 |

---

## 4. 컨벤션 체크리스트

### 아키텍처
- [x] L0 Raw → L1 KU 순서 준수
- [x] raw_spans 전건 DB 저장 + 건수 검증 — 341건
- [x] KU 100+ 추출 + ChromaDB 임베딩 — 997 KUs

### 지식 구조
- [x] KU 포맷: claim + evidence_summary + counter_summary
- [x] KU ID: `ku-{domain}-{book_seq}-{ku_seq}`
- [x] Maturity: M0 (자동추출) 기본값
- [x] source_spans: JSON array of raw_span ids

### 데이터
- [x] 5테이블 DDL (edges 포함) — Stage B 완료
- [x] ChromaDB ku_embeddings 컬렉션 — Stage B 완료
- [x] ID 패턴 준수 (book_id, raw_span_id, ku_id)

### 코딩
- [x] 코드: English (변수명, 함수명) — Stage B 확인
- [x] Raw SQL + 헬퍼 함수 (ORM 미사용) — Stage B 확인
- [x] 인코딩: utf-8-sig (read), utf-8 (write)
- [x] `PYTHONUTF8=1` 환경변수
