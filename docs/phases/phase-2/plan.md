# Phase 2: 서비스 레이어 (Stage E~G)
> Last Updated: 2026-02-27
> Status: Planned
> **전제:** Phase 1 완료 (raw_spans + KU + 임베딩 DB 확보)

## 1. Summary (개요)

**목적:** Phase 1에서 구축한 데이터 파이프라인 위에 검색, 콘텐츠 생성, CLI 인터페이스를 올려 실제 사용 가능한 시스템을 완성한다.

**범위:**
- L1 검색: ChromaDB 벡터 검색 모듈
- L3 Generation: 토픽 기반 콘텐츠 생성 (blog, summary, thread)
- CLI: `ks search`, `ks generate content`
- Vault: KU 마크다운 렌더링 (Obsidian 호환)

**예상 산출물:**
- 소스 코드 5개 모듈 (search/vector, generation/content, generation/templates, cli, vault/renderer)
- 프롬프트 템플릿 3종
- Obsidian 호환 마크다운 vault
- E2E 통합 테스트

---

## 2. Phase 1 산출물 (입력)

Phase 2는 Phase 1의 다음 산출물에 의존:
- `data/knowledge.db` — books, raw_spans, knowledge_units 테이블 (데이터 포함)
- `data/chroma/` — ku_embeddings 컬렉션 (100+ KU 임베딩)
- `src/db/models.py` — CRUD 헬퍼 함수
- `src/db/vectors.py` — ChromaDB 래퍼
- `config.yaml` — 런타임 설정

---

## 3. Target State (목표 상태)

Phase 2 완료 후 (= 기존 masterplan §14 Phase 1 완료 기준):
- `ks search "매몰비용"` → 관련 KU 반환 (claim, domain, confidence 표시)
- `ks generate content --topic "매몰비용" --format blog` → 블로그 초안 생성
- 생성된 콘텐츠가 실제 사용 가능한 품질 (경미한 편집으로 게시 가능)
- KU가 DB + ChromaDB + Vault에 일관되게 저장
- E2E 테스트 PASS

---

## 4. Implementation Stages

### Stage E: 의미 검색 (S) — 3 Task

**목표:** ChromaDB 벡터 검색 모듈

- `src/search/vector.py` — 쿼리 임베딩 → ChromaDB 유사도 검색 → KU 반환
- 검색 결과 포매팅 — claim, domain, confidence, similarity score 표시
- 도메인 필터링 — metadata 기반 (Phase 2는 단일 도메인이지만 구조 준비)
- similarity threshold 튜닝 (초기값 0.5)

**의존성:** Phase 1 Stage D (임베딩 데이터)

### Stage F: 콘텐츠 생성 (M) — 4 Task

**목표:** 토픽 → KU 검색 → 프롬프트 → LLM → 콘텐츠 초안

- `src/generation/content.py` — 생성 파이프라인 (토픽 → 검색 → 컨텍스트 조합 → 생성)
- 프롬프트 템플릿 3종:
  - `blog` — 1,500-3,000자 블로그 포스트
  - `summary` — 300-500자 개념 요약
  - `thread` — 5-10개 항목 소셜미디어 스레드
- 출처 KU ID 필수 첨부 — 생성 결과에 사용된 KU ID 목록 기록
- generations 테이블 기록 — mode, format, prompt, output, ku_ids

**의존성:** Stage E (검색 모듈)

### Stage G: CLI + 통합 (L) — 4 Task

**목표:** CLI 진입점 + Vault 렌더러 + 전체 파이프라인 통합 테스트

- `src/cli.py` — Typer 기반 CLI
  - `ks ingest <path>` — PDF/JSON → raw_spans → KU → 임베딩 → Vault
  - `ks search <query>` — 벡터 검색 + 결과 출력
  - `ks generate content --topic <t> --format <f>` — 콘텐츠 생성
- `src/vault/renderer.py` — KU → Obsidian 호환 마크다운 (YAML frontmatter + claim/evidence/counter)
- 통합 테스트 — 전체 파이프라인 end-to-end
- 완료 기준 검증 (masterplan §14)

**의존성:** Phase 1 전체 + Stage E, F

---

## 5. Task Breakdown

| ID | Task | Stage | Size | 의존성 | 비고 |
|----|------|-------|------|--------|------|
| E.1 | vector.py 구현 | E | S | Phase 1 D.4 | ChromaDB 검색 |
| E.2 | 검색 결과 포매팅 + threshold 튜닝 | E | S | E.1 | 초기 0.5, 10쿼리 테스트 |
| E.3 | 도메인 필터링 | E | S | E.1 | metadata 기반 |
| F.1 | content.py 파이프라인 | F | M | E.1 | 토픽→검색→생성 |
| F.2 | 프롬프트 템플릿 3종 | F | M | F.1 | blog, summary, thread |
| F.3 | 출처 KU ID 첨부 | F | S | F.1 | 생성 결과에 KU ID 기록 |
| F.4 | generations 테이블 기록 | F | S | Phase 1 B.2, F.1 | mode, format, output, ku_ids |
| G.1 | cli.py (ingest, search, generate) | G | M | C.2, E.1, F.1 | Typer CLI |
| G.2 | vault/renderer.py | G | M | Phase 1 D.3 | KU → 마크다운 |
| G.3 | 통합 테스트 | G | L | G.1, G.2 | end-to-end |
| G.4 | 완료 기준 검증 | G | S | G.3 | masterplan §14 4항목 |

**합계:** 11개 Task (S: 5, M: 4, L: 2)

---

## 6. Risks & Mitigation

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| 검색 정확도 미달 | 콘텐츠 생성 품질 하락 | 중 | E.2에서 threshold 튜닝, embedding 모델 전환 가능 |
| 콘텐츠 생성 품질 미달 | MVP 가치 검증 실패 | 중 | 프롬프트 반복 최적화, Claude vs GPT-4o 비교 |
| 검색 결과 0건 | 사용자 경험 저하 | 저 | "관련 KU 없음" 메시지 + threshold 하향 제안 |
| Vault 렌더링 Obsidian 비호환 | 마크다운 깨짐 | 저 | frontmatter 검증, 실제 Obsidian 테스트 |

---

## 7. Dependencies

### 내부 의존성

```
Phase 1 (A~D) ──→ Stage E ──→ Stage F ──→ Stage G
                                          └──→ Stage G
```

- Phase 1 → E: KU 임베딩 데이터 필요
- Stage E → F: 검색 모듈 필요
- Stage E, F → G: 전체 모듈 통합

### 외부 의존성

| 의존성 | 용도 | Phase 2 필수 |
|--------|------|-------------|
| OpenAI API (text-embedding-3-small) | 검색 쿼리 임베딩 | Yes |
| Anthropic API (Claude) | 콘텐츠 생성 | Yes |
| typer | CLI 프레임워크 | Yes |
| rich | CLI 출력 포매팅 | Optional |

### Phase 3 연결

Phase 2 산출물 → Phase 3 입력:
- 검색/생성 모듈 (`src/search/`, `src/generation/`)
- CLI 프레임워크 (`src/cli.py`)
- Vault 렌더러 (`src/vault/renderer.py`)
- 완성된 1권 파이프라인 전체
