# Phase 2: 서비스 레이어 — Tasks
> Last Updated: 2026-02-28

## Progress: 3/11 Tasks (27%)

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

### Stage F: 콘텐츠 생성 (M) — 0/4

- [ ] F.1 `src/generation/content.py` 파이프라인
  - `generate_content()` — 토픽 → KU 검색 → 컨텍스트 조합 → LLM → 출력
  - 입력: topic (str), format (str), ku_ids (optional list)
  - KU 컨텍스트: claim + evidence_summary + counter_summary
- [ ] F.2 프롬프트 템플릿 3종
  - `blog.txt` — 1,500-3,000자 블로그 포스트
  - `summary.txt` — 300-500자 개념 요약
  - `thread.txt` — 5-10개 항목 소셜미디어 스레드
  - 변수: {topic}, {ku_context}, {format_instructions}
- [ ] F.3 출처 KU ID 첨부 로직
  - 생성 결과 끝에 "출처: ku-econ-001-xxxx, ..." 자동 첨부
  - 마크다운 출력 시 KU 링크 포함
- [ ] F.4 generations 테이블 기록
  - mode: "content", format, prompt, output, ku_ids (JSON), rating (NULL)

---

### Stage G: CLI + 통합 (L) — 0/4

- [ ] G.1 `src/cli.py` — ingest, search, generate 명령어
  - `ks ingest <path>` — JSON/PDF 자동 감지 → 전체 파이프라인
  - `ks search <query>` — 벡터 검색 + Rich 출력
  - `ks generate content --topic <t> --format <f>` — 콘텐츠 생성
  - `ks stats` — 기본 통계 (KU 수, 도메인 분포)
- [ ] G.2 `src/vault/renderer.py` — KU 마크다운 렌더링
  - YAML frontmatter: id, book, domain, subdomain, confidence, maturity, tags, created
  - 본문: Claim, Evidence, Counter, Connections
  - 출력 경로: `vault/domains/{domain}/{ku_id}.md`
- [ ] G.3 통합 테스트 (전체 파이프라인)
  - ingest → search → generate end-to-end
  - DB 정합성 확인: raw_spans <-> knowledge_units <-> ChromaDB
- [ ] G.4 완료 기준 4항목 검증
  - [ ] `ks ingest` → KU 추출 + DB 저장 + 마크다운 생성
  - [ ] `ks search "매몰비용"` → 관련 KU 반환
  - [ ] `ks generate content --topic "매몰비용" --format blog` → 블로그 초안
  - [ ] 생성 콘텐츠 품질 평가 (경미한 편집으로 게시 가능)
