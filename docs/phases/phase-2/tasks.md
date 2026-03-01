# Phase 2: 서비스 레이어 — Tasks
> Last Updated: 2026-02-28

## Progress: 11/11 Tasks (100%) ✅

---

### Stage E: 의미 검색 (S) — 3/3 ✅

- [x] E.1 `src/search/vector.py` 구현
  - `search_kus()` — 쿼리 텍스트 → 임베딩 → ChromaDB 검색 → KU 반환
  - top_k 파라미터 (기본 10)
  - similarity threshold (기본 0.6, 튜닝 완료)
  - 검색 결과 0건 시 "관련 KU 없음" 메시지 반환
- [x] E.2 검색 결과 포매팅 + threshold 튜닝
  - `format_results()` — 텍스트 테이블, `format_results_rich()` — Rich 테이블
  - 출력: claim, domain, confidence, similarity score, KU ID
  - **threshold 튜닝 결과:** 0.6 (10쿼리 테스트, precision 우선)
    - 매몰비용 60%, 인플레이션 56%, 경쟁 60%, 기회비용 41%, 세금 47%
- [x] E.3 도메인 필터링
  - ChromaDB metadata where 조건 (`domain` 파라미터)
  - 테스트 완료: `domain="경제"` 필터 정상 동작

---

### Stage F: 콘텐츠 생성 (M) — 4/4 ✅

- [x] F.1 `src/generation/content.py` 파이프라인
  - `generate_content()` — 토픽 → KU 검색 → 컨텍스트 조합 → LLM → 출력
  - 입력: topic (str), format (str), ku_ids (optional list)
  - KU 컨텍스트: claim + evidence_summary + counter_summary
  - 모델: gpt-4.1-mini (config.yaml `models.generation`)
- [x] F.2 프롬프트 템플릿 3종
  - `blog.txt` — 1,500-3,000자 블로그 포스트
  - `summary.txt` — 300-500자 개념 요약
  - `thread.txt` — 5-10개 항목 소셜미디어 스레드
  - 변수: {topic}, {ku_context}
- [x] F.3 출처 KU ID 첨부 로직
  - 생성 결과 끝에 `\n\n---\n출처: ku-xxx, ku-yyy` 자동 첨부
- [x] F.4 generations 테이블 기록
  - mode: "content", format, prompt, output, ku_ids (JSON), rating (NULL)
  - `insert_generation()`, `get_generation()` CRUD 헬퍼 추가 (`src/db/models.py`)

---

### Stage G: CLI + 통합 (L) — 4/4 ✅

- [x] G.1 `src/cli.py` — ingest, search, generate 명령어
  - `ks ingest <path>` — JSON 파싱 → KU 추출 → 임베딩 → Vault 렌더링
  - `ks search <query>` — 벡터 검색 + Rich 테이블 출력
  - `ks generate content --topic <t> --format <f>` — 콘텐츠 생성
  - `ks stats` — DB/ChromaDB 통계 + 도메인 분포
  - `--dry-run`, `--verbose`, `--config` 글로벌 옵션
- [x] G.2 `src/vault/renderer.py` — KU 마크다운 렌더링
  - YAML frontmatter: id, book, domain, subdomain, confidence, maturity, tags, created
  - 본문: Claim, Evidence, Counter, Connections
  - 출력 경로: `vault/domains/{domain}/{ku_id}.md` (997건 렌더링 완료)
- [x] G.3 통합 테스트 (전체 파이프라인)
  - `scripts/test_e2e.py` — DB 정합성 + ChromaDB + 검색 + 생성 + 렌더링 5개 테스트
  - DB 정합성 확인: raw_spans ↔ knowledge_units ↔ ChromaDB
- [x] G.4 완료 기준 4항목 검증
  - [x] `ks stats` → books=1, spans=341, kus=997, chroma=997
  - [x] `ks search "매몰비용"` → 9건 반환 (top 60.4%)
  - [x] `ks generate content --topic "인플레이션" --format summary` → 요약 생성 확인
  - [x] Vault 렌더링 997건 + frontmatter 구조 확인
