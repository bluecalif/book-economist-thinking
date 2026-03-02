# Project Context
> Last Updated: 2026-03-02

## Tech Stack

| 계층 | 기술 | 버전/비고 |
|------|------|----------|
| 언어 | Python | 3.12 (anaconda3) |
| LLM API | GPT-4.1-mini | KU 추출, edge 생성 |
| 임베딩 | text-embedding-3-large (OpenAI) | 정확도 우선 |
| Vector DB | ChromaDB | 로컬, 13,000~75,000 KU 규모 |
| 관계형 DB | SQLite | 로컬, 제로 설정 |
| CLI | Typer | 타입 힌트 기반 |
| 마크다운 출력 | Obsidian 호환 | 시각적 탐색 + 수동 편집 |
| 웹 크롤링 | Requests + BeautifulSoup / Playwright | Phase 5에서 도입 |
| 개발 환경 | Windows 10, Git Bash, Claude Code | |

### 스택 원칙
- **로컬 우선**: 외부 서비스 의존 최소화 (LLM API 제외)
- **마이그레이션 가능**: SQLite → PostgreSQL, ChromaDB → pgvector 전환 경로 확보
- **단일 언어**: Python 통일

---

## Data Schema

### SQLite 테이블 (5개)

```sql
-- L0: 원본 텍스트
books (id TEXT PK, title, author, domain, filepath, total_pages, created_at)
raw_spans (id TEXT PK, book_id FK→books, chapter, page, seq, text, span_type, created_at)

-- L1: 지식 단위
knowledge_units (id TEXT PK, book_id FK→books, claim, evidence_summary, counter_summary,
                 domain, subdomain, tags JSON, confidence REAL, maturity TEXT,
                 source_spans JSON, created_at, updated_at)

-- L2: 관계 그래프
edges (id TEXT PK, from_ku_id FK→KU, to_ku_id FK→KU, relation_type, strength REAL,
       source TEXT, description, created_at)

-- L3: 생성 이력
generations (id TEXT PK, mode, format, prompt, output, ku_ids JSON, rating INT, created_at)
```

### ChromaDB 컬렉션
- `ku_embeddings` — KU claim+evidence 임베딩, metadata: ku_id, domain, book_id

### ID 패턴

| 엔티티 | 패턴 | 예시 |
|--------|------|------|
| book_id | `{domain}-{title_slug}-{seq}` | `econ-thinking-001` |
| raw_span_id | `{book_id}-ch{nn}-p{nnn}-s{nnn}` | `econ-thinking-001-ch03-p042-s005` |
| ku_id | `ku-{domain}-{book_seq}-{ku_seq}` | `ku-econ-001-0042` |
| edge_id | `edge-{from_ku_seq}-{to_ku_seq}-{type}` | `edge-0042-0038-explains` |
| generation_id | `gen-{mode}-{timestamp}` | `gen-content-20260227-001` |

### Edge 타입 (6종)

| 타입 | 의미 |
|------|------|
| `explains` | A가 B를 설명 |
| `supports` | A가 B를 뒷받침 |
| `contradicts` | A와 B가 상충 |
| `extends` | A가 B를 확장 |
| `example_of` | A가 B의 사례 |
| `analogous_to` | A와 B가 유사 구조 |

---

## Conventions

### 아키텍처
- 레이어 구조: L0 Raw → L1 KU → L2 Graph → L3 Generation → L4 Evolution
- CLI 명령어: `ks ingest`, `search`, `explore`, `generate`, `crawl`, `sync`, `stats`, `export`

### 지식 구조
- KU 포맷: claim + evidence_summary + counter_summary
- Maturity: M0 (자동추출) → M1 (수동검토) → M2 (외부보강)

### 코딩 컨벤션
- 코드: English (변수명, 함수명, 주석)
- 문서/커밋: Korean (한국어)
- DB 접근: Raw SQL + 헬퍼 함수 (ORM 미사용)
- 인코딩: utf-8-sig (read), utf-8 (write), PYTHONUTF8=1

### 디렉터리 구조
```
src/
├── cli.py
├── ingest/ (pdf_parser.py, ku_extractor.py, llm_cache.py, splitter.py)
├── search/ (vector.py, hybrid.py)
├── generation/ (content.py, idea.py, templates/)
├── graph/ (edge_builder.py, traversal.py, dispute.py)
├── db/ (models.py, vectors.py)
└── vault/ (renderer.py)
data/ (knowledge.db, llm_cache.db, chroma/, raw/)
scripts/ (batch_ingest.py, build_edges.py, build_catalog.py, migrate_data.py)
vault/ (Obsidian 호환 마크다운)
config.yaml
pyproject.toml
```

---

## Shared Dependencies

### Python 패키지
- `pymupdf` — PDF 파싱
- `chromadb` — 벡터 DB
- `openai` — 임베딩 + GPT-4.1-mini
- `anthropic` — Claude API
- `pydantic` — 데이터 검증
- `pyyaml` — config 파싱
- `typer` — CLI
- `rich` — CLI 출력 포매팅

### 외부 서비스
- OpenAI API — 임베딩, KU 추출, edge 생성 (GPT-4.1-mini)
- Anthropic API — 생성 (Claude)

### 데이터베이스
- `data/llm_cache.db` — LLM 응답 캐시 (SQLite, hash 기반 키)

### 도메인 체계
| 카테고리 | domain_short | 전체 | Phase 3 | Phase 4 |
|---------|-------------|------|---------|---------|
| 역사/사회 | hist | 18 | 3 | 18 |
| 경제/경영 | econ | 28 | 3 | 28 |
| 인문/자기계발 | humn | 18 | 3 | 18 |
| 과학/기술 | sci | 23 | 3 | 23 |
| **합계** | | **87** | **12** | **87** |
