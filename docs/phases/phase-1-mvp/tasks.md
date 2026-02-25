# Phase 1: 1권 MVP — Tasks
> Last Updated: 2026-02-25
> Status: Planning

## Stage A: 프로젝트 초기화

- [ ] A.1 `pyproject.toml` 생성 (의존성 정의)
- [ ] A.2 `src/` 디렉터리 구조 생성 (`__init__.py` 포함)
- [ ] A.3 `data/`, `vault/` 디렉터리 생성
- [ ] A.4 `config.yaml` 기본 설정
- [ ] A.5 `.gitignore` 생성

## Stage B: DB 스키마

- [ ] B.1 `src/db/models.py` — SQLite DDL (books, raw_spans, knowledge_units, generations)
- [ ] B.2 `src/db/models.py` — 기본 CRUD 함수 (insert, get, list, update)
- [ ] B.3 `src/db/vectors.py` — ChromaDB 초기화 + ku_embeddings 컬렉션
- [ ] B.4 `src/db/vectors.py` — add/query/delete 래퍼
- [ ] B.5 DB 초기화 스크립트 또는 함수

## Stage C: PDF 파싱

- [ ] C.1 기존 JSON 구조 분석 (structure.json, text.json)
- [ ] C.2 `src/ingest/pdf_parser.py` — JSON → raw_spans 변환
- [ ] C.3 `src/ingest/pdf_parser.py` — PyMuPDF 직접 파싱 경로
- [ ] C.4 raw_spans 저장 + 검증 (챕터/페이지/순서)

## Stage D: KU 추출

- [ ] D.1 KU 추출 프롬프트 작성 (masterplan §5 기반)
- [ ] D.2 `src/ingest/ku_extractor.py` — LLM API 호출 모듈
- [ ] D.3 KU 추출 + knowledge_units 테이블 저장
- [ ] D.4 임베딩 생성 + ChromaDB 저장
- [ ] D.5 source_spans 역참조 기록
- [ ] D.6 1챕터 샘플로 품질 검증 → 프롬프트 최적화

## Stage E: 의미 검색

- [ ] E.1 `src/search/vector.py` — 쿼리 임베딩 + ChromaDB 검색
- [ ] E.2 결과 포맷팅 (claim, domain, confidence 표시)
- [ ] E.3 도메인 필터링 파라미터

## Stage F: 콘텐츠 생성

- [ ] F.1 `src/generation/content.py` — 생성 파이프라인 (토픽→검색→컨텍스트→LLM→출력)
- [ ] F.2 `src/generation/templates/blog.md` — 블로그 템플릿
- [ ] F.3 `src/generation/templates/thread.md` — 스레드 템플릿
- [ ] F.4 `src/generation/templates/summary.md` — 요약 템플릿
- [ ] F.5 generations 테이블 기록 + KU ID 첨부
- [ ] F.6 생성 품질 평가 (실제 사용 가능 여부)

## Stage G: CLI + Vault

- [ ] G.1 `src/cli.py` — `ks ingest <path>` 명령
- [ ] G.2 `src/cli.py` — `ks search <query>` 명령
- [ ] G.3 `src/cli.py` — `ks generate content` 명령
- [ ] G.4 `src/cli.py` — `ks stats` 명령
- [ ] G.5 `src/vault/renderer.py` — KU → Obsidian 마크다운 노트
- [ ] G.6 통합 테스트: ingest → search → generate E2E

## 완료 기준 체크 (masterplan §14)

- [ ] `ks ingest book.pdf` → KU 추출 + DB 저장 + 마크다운 생성
- [ ] `ks search "매몰비용"` → 관련 KU 반환
- [ ] `ks generate content --topic "매몰비용" --format blog` → 블로그 초안 생성
- [ ] 생성된 콘텐츠가 실제 사용 가능한 품질인지 평가
