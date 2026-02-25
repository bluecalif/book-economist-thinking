---
name: db-schema
description: SQLite + ChromaDB 스키마 가드레일. 5개 테이블(books, raw_spans, knowledge_units, edges, generations), ChromaDB ku_embeddings 컬렉션, book_id/ku_id 패턴, Edge 6타입, FK 관계, 인덱스 설계. 테이블 설계, 스키마 수정, DB 생성, 데이터베이스 구조 작업 시 자동 활성화.
---

# DB Schema Guardrail

## 목적

SQLite + ChromaDB 스키마 규칙 준수를 강제한다. 스키마 변경 시 반드시 이 가이드를 참조해야 한다.

## 사용 시점

- DB 스키마 생성/수정
- `db/models.py` 작업
- ChromaDB 설정
- 테이블 관계 논의
- 마이그레이션 작업

---

## SQLite 테이블 (5개)

### 1. books

```sql
CREATE TABLE books (
    id          TEXT PRIMARY KEY,   -- 예: 'econ-thinking-001'
    title       TEXT NOT NULL,
    author      TEXT,
    domain      TEXT NOT NULL,      -- 인문|사회|역사|경제|과학|기술|경영
    filepath    TEXT,               -- 원본 PDF 경로
    total_pages INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

- `id`: TEXT, 형식 `{domain_short}-{book_name}-{seq}`
- `domain`: 7개 값만 허용

### 2. raw_spans

```sql
CREATE TABLE raw_spans (
    id          TEXT PRIMARY KEY,   -- 예: 'econ-thinking-001-ch03-p042-s005'
    book_id     TEXT NOT NULL REFERENCES books(id),
    chapter     TEXT,
    page        INTEGER,
    seq         INTEGER,            -- 챕터 내 순서
    text        TEXT NOT NULL,
    span_type   TEXT DEFAULT 'paragraph',  -- paragraph|heading|list|table
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3. knowledge_units

```sql
CREATE TABLE knowledge_units (
    id                  TEXT PRIMARY KEY,   -- 예: 'ku-econ-001-0042'
    book_id             TEXT NOT NULL REFERENCES books(id),
    claim               TEXT NOT NULL,
    evidence_summary    TEXT,
    counter_summary     TEXT,
    domain              TEXT NOT NULL,
    subdomain           TEXT,
    tags                TEXT,                -- JSON array
    confidence          REAL DEFAULT 0.5,
    maturity            TEXT DEFAULT 'M0',   -- M0|M1|M2
    source_spans        TEXT,                -- JSON array of raw_span ids
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4. edges

```sql
CREATE TABLE edges (
    id              TEXT PRIMARY KEY,
    from_ku_id      TEXT NOT NULL REFERENCES knowledge_units(id),
    to_ku_id        TEXT NOT NULL REFERENCES knowledge_units(id),
    relation_type   TEXT NOT NULL,      -- 6타입만 허용 (아래 참조)
    strength        REAL DEFAULT 0.5,
    source          TEXT DEFAULT 'auto', -- auto|manual|crawl
    description     TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edges_from ON edges(from_ku_id);
CREATE INDEX idx_edges_to ON edges(to_ku_id);
CREATE INDEX idx_edges_type ON edges(relation_type);
```

### 5. generations

```sql
CREATE TABLE generations (
    id          TEXT PRIMARY KEY,
    mode        TEXT NOT NULL,      -- content|idea
    format      TEXT,               -- blog|thread|newsletter|lecture|summary
    prompt      TEXT,
    output      TEXT NOT NULL,
    ku_ids      TEXT NOT NULL,      -- JSON array
    rating      INTEGER,            -- NULL|1(bad)|2(good)
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Edge 6타입 (CRITICAL)

이 6개만 사용. 임의 추가 금지.

| 타입 | 의미 | 예시 |
|------|------|------|
| `explains` | A가 B를 설명 | "비교우위" explains "무역 이득" |
| `supports` | A가 B를 뒷받침 | 실험 결과 supports 이론적 주장 |
| `contradicts` | A와 B가 상충 | 효율시장가설 contradicts 행동경제학 |
| `extends` | A가 B를 확장 | 게임이론 extends 합리적 선택 |
| `example_of` | A가 B의 사례 | 죄수의 딜레마 example_of 게임이론 |
| `analogous_to` | A와 B가 유사 구조 | 자연선택 analogous_to 시장 경쟁 |

---

## ChromaDB

- **컬렉션명**: `ku_embeddings`
- **임베딩 모델**: text-embedding-3-small (OpenAI) 또는 동급
- **문서 ID**: KU ID와 동일 (`ku-econ-001-0042`)
- **메타데이터**: `book_id`, `domain`, `confidence`, `maturity`

---

## ID 패턴 요약

| 엔티티 | 패턴 | 예시 |
|--------|------|------|
| book | `{domain}-{name}-{seq}` | `econ-thinking-001` |
| raw_span | `{book_id}-ch{nn}-p{nnn}-s{nnn}` | `econ-thinking-001-ch03-p042-s005` |
| KU | `ku-{domain}-{book_seq}-{ku_seq}` | `ku-econ-001-0042` |
| edge | UUID 또는 자동 생성 | `edge-001` |
| generation | UUID 또는 자동 생성 | `gen-001` |

---

## 도메인 값 (7개)

`인문`, `사회`, `역사`, `경제`, `과학`, `기술`, `경영`

이 7개만 허용. 약어 매핑:

| 한글 | 약어 |
|------|------|
| 인문 | hum |
| 사회 | soc |
| 역사 | hist |
| 경제 | econ |
| 과학 | sci |
| 기술 | tech |
| 경영 | mgmt |

---

## 체크리스트

스키마 관련 작업 시 확인:

- [ ] 테이블명/컬럼명이 위 정의와 일치하는가?
- [ ] FK 관계가 올바른가? (raw_spans→books, knowledge_units→books, edges→knowledge_units)
- [ ] edge의 relation_type이 6타입 중 하나인가?
- [ ] JSON 필드(tags, source_spans, ku_ids)가 TEXT로 저장되는가?
- [ ] ChromaDB 컬렉션명이 `ku_embeddings`인가?
- [ ] ID 패턴이 규칙을 따르는가?

---

## 관련 파일

- `src/db/models.py` — SQLite 스키마 + CRUD
- `src/db/vectors.py` — ChromaDB 래퍼
- `docs/masterplan-v2.0.md` §4-§7 — 레이어별 상세 설계
