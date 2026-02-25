# Phase 1: 1권 MVP
> Last Updated: 2026-02-25
> Status: Planning

## 1. Summary

**목적:** 경제학자의 생각법 1권으로 전체 파이프라인(PDF → KU 추출 → DB 저장 → 의미 검색 → 콘텐츠 생성 → 마크다운 출력)을 완성한다.

**범위:** L0 Raw, L1 KU, L3 Generation (콘텐츠 생성 기본), Search (벡터), CLI, Vault

**예상 산출물:**
- 작동하는 `ks` CLI (ingest, search, generate content)
- 100-200개 KU (경제학자의 생각법)
- SQLite DB + ChromaDB 임베딩
- Obsidian 호환 마크다운 vault
- 콘텐츠 생성 템플릿 3종 (blog, thread, summary)

## 2. Current State

- 마스터플랜 v2.0 확정
- 기존 파싱 데이터 존재: `55bbe4_경제학자의_생각법_structure.json` (5챕터), `55bbe4_경제학자의_생각법_text.json` (400페이지)
- `.claude/` 커맨드/스킬/훅 구성 완료
- 소스 코드, DB, 디렉터리 구조 미생성

## 3. Target State (masterplan §14)

- [ ] `ks ingest book.pdf` → KU 추출 + DB 저장 + 마크다운 생성
- [ ] `ks search "매몰비용"` → 관련 KU 반환
- [ ] `ks generate content --topic "매몰비용" --format blog` → 블로그 초안 생성
- [ ] 생성된 콘텐츠가 실제 사용 가능한 품질인지 평가

## 4. Implementation Stages

### Stage A: 프로젝트 초기화 (S)

- `pyproject.toml` 생성 (의존성: click/typer, pymupdf, chromadb, openai, anthropic, pydantic)
- `src/` 디렉터리 구조 생성 (masterplan §12)
- `data/`, `vault/` 디렉터리 생성
- `config.yaml` 기본 설정 파일
- `.gitignore` 생성

### Stage B: DB 스키마 (M)

- `src/db/models.py` — SQLite DDL (books, raw_spans, knowledge_units, generations)
  - edges 테이블은 Phase 2에서 추가
- `src/db/vectors.py` — ChromaDB 래퍼 (ku_embeddings 컬렉션)
- DB 초기화 함수 + 기본 CRUD

### Stage C: PDF 파싱 (M)

- `src/ingest/pdf_parser.py` — 기존 JSON 데이터 활용 + PDF 직접 파싱 경로
- 입력: PDF 또는 기존 파싱 JSON
- 출력: raw_spans 테이블 저장
- 챕터/페이지/순서 메타데이터 추출

### Stage D: KU 추출 (L)

- `src/ingest/ku_extractor.py` — raw_spans → KU 변환 (LLM API)
- KU 추출 프롬프트 (masterplan §5 참조)
- 임베딩 생성 + ChromaDB 저장
- knowledge_units 테이블 저장
- source_spans 역참조 기록

### Stage E: 의미 검색 (S)

- `src/search/vector.py` — ChromaDB 쿼리 래퍼
- 쿼리 → 임베딩 → 유사도 검색 → KU 반환
- 도메인 필터링 (Phase 2+ 활용)

### Stage F: 콘텐츠 생성 (L)

- `src/generation/content.py` — 생성 파이프라인
- `src/generation/templates/` — blog, thread, summary 템플릿
- 토픽/KU → 관련 KU 검색 → 컨텍스트 조합 → LLM → 초안
- generations 테이블 기록 + 사용된 KU ID 첨부

### Stage G: CLI + Vault (M)

- `src/cli.py` — Click/Typer CLI 진입점
  - `ks ingest <path>` — Stage C+D 연결
  - `ks search <query>` — Stage E 연결
  - `ks generate content` — Stage F 연결
  - `ks stats` — 기본 통계
- `src/vault/renderer.py` — KU → Obsidian 마크다운 렌더링

## 5. Task Breakdown

| # | Task | Stage | Size | 의존성 | 설명 |
|---|------|-------|------|--------|------|
| 1 | pyproject.toml + 디렉터리 | A | S | - | 프로젝트 뼈대 |
| 2 | .gitignore | A | S | - | data/, *.db, chroma/ 등 제외 |
| 3 | config.yaml | A | S | - | API 키, 모델, 경로 설정 |
| 4 | SQLite 스키마 + CRUD | B | M | 1 | books, raw_spans, knowledge_units, generations |
| 5 | ChromaDB 래퍼 | B | M | 1 | ku_embeddings 컬렉션, add/query |
| 6 | PDF 파서 (JSON 활용) | C | M | 4 | 기존 파싱 JSON → raw_spans |
| 7 | PDF 파서 (직접 파싱) | C | M | 4 | PyMuPDF 경로 (JSON 없을 때) |
| 8 | KU 추출기 | D | L | 4,5,6 | LLM 프롬프트 + 임베딩 + DB 저장 |
| 9 | 벡터 검색 | E | S | 5 | ChromaDB 쿼리 래퍼 |
| 10 | 콘텐츠 생성 파이프라인 | F | L | 8,9 | 토픽→검색→생성→저장 |
| 11 | 프롬프트 템플릿 3종 | F | M | - | blog, thread, summary |
| 12 | CLI 진입점 | G | M | 6,8,9,10 | ks ingest/search/generate/stats |
| 13 | 마크다운 렌더러 | G | S | 4 | KU → Obsidian 마크다운 |
| 14 | 통합 테스트 | G | M | 12 | 전체 파이프라인 E2E |

## 6. Risks & Mitigation

| 리스크 | 영향 | 대응 |
|--------|------|------|
| KU 추출 프롬프트 품질 | 전체 시스템 품질 좌우 | 소규모 샘플(1챕터)로 프롬프트 반복 최적화 후 전체 처리 |
| LLM API 비용 초과 | 예산 초과 | GPT-4o mini 우선 사용, 필요시 Claude로 재처리 |
| 기존 JSON 데이터 구조 불일치 | Stage C 지연 | JSON 구조 사전 분석 → 파서 어댑터 작성 |
| ChromaDB 로컬 성능 | 검색 속도 | 200 KU 규모에서는 문제 없음, Phase 3에서 재평가 |

## 7. Dependencies

**내부:**
- Stage B → C, D, E, F, G (DB가 모든 모듈의 기반)
- Stage D → F (KU가 있어야 생성 가능)
- Stage E → F (검색이 생성 파이프라인에 포함)

**외부:**
- Python 3.11+ (anaconda3 환경)
- LLM API 키 (OpenAI / Anthropic)
- PyMuPDF (`pymupdf` 패키지)
- ChromaDB (`chromadb` 패키지)
- Click 또는 Typer (`click` / `typer` 패키지)
