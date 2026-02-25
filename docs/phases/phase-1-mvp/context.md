# Phase 1: 1권 MVP — Context
> Last Updated: 2026-02-25

## 1. 핵심 파일

### 참조 (읽기)
| 파일 | 용도 |
|------|------|
| `docs/masterplan-v2.0.md` | 전체 아키텍처, 스키마, CLI 명세 |
| `55bbe4_경제학자의_생각법_structure.json` | 책 구조 (5챕터) |
| `55bbe4_경제학자의_생각법_text.json` | 파싱된 텍스트 (400페이지) |
| `경제학자의 생각법.pdf` | 원본 PDF |

### 생성/수정
| 파일 | Stage | 용도 |
|------|-------|------|
| `pyproject.toml` | A | 패키지 설정 + 의존성 |
| `config.yaml` | A | 런타임 설정 |
| `src/db/models.py` | B | SQLite 스키마 + CRUD |
| `src/db/vectors.py` | B | ChromaDB 래퍼 |
| `src/ingest/pdf_parser.py` | C | PDF/JSON → raw_spans |
| `src/ingest/ku_extractor.py` | D | raw_spans → KU |
| `src/search/vector.py` | E | 의미 검색 |
| `src/generation/content.py` | F | 콘텐츠 생성 |
| `src/generation/templates/*.md` | F | 프롬프트 템플릿 |
| `src/cli.py` | G | CLI 진입점 |
| `src/vault/renderer.py` | G | KU → 마크다운 |

## 2. 데이터 스키마

### SQLite (masterplan §4-5, §7)

**Phase 1에서 사용하는 테이블:**

```sql
-- L0: 원본
books (id TEXT PK, title, author, domain, filepath, total_pages, created_at)
raw_spans (id TEXT PK, book_id FK→books, chapter, page, seq, text, span_type, created_at)

-- L1: 지식 단위
knowledge_units (id TEXT PK, book_id FK→books, claim, evidence_summary, counter_summary,
                 domain, subdomain, tags JSON, confidence REAL, maturity TEXT,
                 source_spans JSON, created_at, updated_at)

-- L3: 생성 이력
generations (id TEXT PK, mode, format, prompt, output, ku_ids JSON, rating INT, created_at)
```

**Phase 1에서 제외:**
- `edges` 테이블 → Phase 2에서 추가

### ChromaDB

- 컬렉션: `ku_embeddings`
- Document: KU claim + evidence_summary
- Metadata: `{ku_id, book_id, domain, subdomain, confidence, maturity}`
- Embedding: text-embedding-3-small (OpenAI)

### ID 패턴

| 엔티티 | 패턴 | 예시 |
|--------|------|------|
| book | `{domain_abbr}-{title_abbr}-{seq}` | `econ-thinking-001` |
| raw_span | `{book_id}-ch{nn}-p{nnn}-s{nnn}` | `econ-thinking-001-ch03-p042-s005` |
| KU | `ku-{domain}-{book_seq}-{ku_seq}` | `ku-econ-001-0042` |
| generation | `gen-{mode}-{timestamp}` | `gen-content-20260225-143022` |

## 3. 주요 결정사항

| 결정 | 선택 | 근거 |
|------|------|------|
| CLI 프레임워크 | Click 또는 Typer | 확정 필요 — Typer가 타입 힌트 기반으로 더 간결 |
| 임베딩 모델 | text-embedding-3-small | 비용 효율, 200 KU 규모 충분 |
| KU 추출 LLM | GPT-4o mini 우선 | 비용 절감, 품질 검증 후 필요시 업그레이드 |
| 기존 JSON 활용 | 우선 JSON 경로, PDF 직접 파싱은 보조 | 파싱 비용/시간 절약 |
| edges 테이블 | Phase 1에서 DDL만, 사용은 Phase 2 | 의존성 최소화 |

## 4. 컨벤션 체크리스트

### 아키텍처
- [ ] 레이어 구조: L0 Raw → L1 KU → (L2 skip) → L3 Generation
- [ ] CLI: `ks ingest`, `ks search`, `ks generate content`, `ks stats`

### 지식 구조
- [ ] KU: claim + evidence_summary + counter_summary
- [ ] KU ID: `ku-{domain}-{book_seq}-{ku_seq}`
- [ ] Maturity: M0 (자동추출)

### 데이터
- [ ] 4개 테이블 활성: books, raw_spans, knowledge_units, generations
- [ ] ChromaDB: ku_embeddings 컬렉션
- [ ] 생성 결과에 출처 KU ID 필수 첨부

### 인코딩
- [ ] CSV/JSON 읽기: `encoding='utf-8-sig'`
- [ ] 파일 쓰기: `encoding='utf-8'` 명시
- [ ] `PYTHONUTF8=1` 환경 변수
