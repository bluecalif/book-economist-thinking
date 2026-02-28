# Phase 2: 서비스 레이어 — Context
> Last Updated: 2026-02-28

## 1. 핵심 파일

### 생성할 소스 파일

| 파일 | 용도 | Stage |
|------|------|-------|
| `src/search/vector.py` | ChromaDB 벡터 검색 | E |
| `src/generation/content.py` | 콘텐츠 생성 파이프라인 | F |
| `src/generation/templates/blog.txt` | 블로그 프롬프트 템플릿 | F |
| `src/generation/templates/summary.txt` | 요약 프롬프트 템플릿 | F |
| `src/generation/templates/thread.txt` | 스레드 프롬프트 템플릿 | F |
| `src/cli.py` | Typer CLI 진입점 | G |
| `src/vault/renderer.py` | KU → Obsidian 마크다운 | G |

### Phase 1 산출물 (참조)

| 파일 | 용도 |
|------|------|
| `src/db/models.py` | SQLite CRUD 헬퍼 |
| `src/db/vectors.py` | ChromaDB 래퍼 |
| `src/ingest/pdf_parser.py` | JSON/PDF 파싱 |
| `src/ingest/ku_extractor.py` | KU 추출 |
| `data/knowledge.db` | SQLite DB (books, raw_spans, knowledge_units) |
| `data/chroma/` | ChromaDB ku_embeddings |
| `config.yaml` | 런타임 설정 |

### 생성할 출력

| 경로 | 용도 |
|------|------|
| `vault/domains/경제/` | KU 마크다운 파일들 |

---

## 2. API 키 설정

Phase 2는 Phase 1에 추가로 Anthropic API가 필요:

```yaml
# config.yaml
api:
  openai_key_env: "OPENAI_API_KEY"      # 검색 쿼리 임베딩
  anthropic_key_env: "ANTHROPIC_API_KEY" # 콘텐츠 생성

models:
  embedding: "text-embedding-3-small"
  generation: "claude-sonnet-4-6"        # 콘텐츠 생성용
```

---

## 3. 주요 결정사항

| # | 결정 | 근거 | 대안 | 영향 |
|---|------|------|------|------|
| 1 | Typer CLI | 타입 힌트 기반, Click보다 간결 | Click | Stage G CLI 구현 |
| 2 | similarity threshold 0.6 확정 | 10쿼리 튜닝 완료, precision 우선 | 0.5 초기값 | E.2에서 조정 완료 |
| 3 | 검색 결과 0건 시 메시지 반환 | UX 향상 | 빈 결과 | vector.py 반환값 |
| 4 | 출처 KU ID 필수 첨부 | 생성물 신뢰성 | 선택적 | content.py 출력 |

### 미결정 사항 (Stage 진행 중 확정)

- [ ] 콘텐츠 생성 LLM: Claude vs GPT-4o (Stage F에서 비교 테스트)
- [ ] 검색된 KU를 프롬프트에 넣을 때 최적 개수: 3-5개 vs 5-10개
- [ ] KU 마크다운에 connections 섹션을 Phase 2에서 포함할지 (edges 없이 빈 섹션 or 생략)

---

## 4. ID 패턴 (Phase 2 추가분)

| 엔티티 | 패턴 | 예시 |
|--------|------|------|
| generation_id | `gen-{mode}-{YYYYMMDD}-{seq}` | `gen-content-20260227-001` |

(book_id, raw_span_id, ku_id는 Phase 1 context.md 참조)

---

## 5. 컨벤션 체크리스트

### 아키텍처
- [ ] CLI 명령어: `ks ingest`, `ks search`, `ks generate content`
- [ ] Obsidian 호환 마크다운 출력

### 생성 (L3)
- [ ] 출처 KU ID 필수 첨부
- [ ] generations 테이블 기록
- [ ] 템플릿 3종: blog, summary, thread

### 검색
- [x] similarity threshold 튜닝 완료 — 0.6 (10쿼리 테스트)
- [x] 검색 결과 0건 처리 — "관련 KU 없음" 메시지
- [x] 도메인 필터링 구조 준비 — `domain` 파라미터
