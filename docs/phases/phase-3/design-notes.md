# Phase 3: Partially-Full — Design Notes
> Last Updated: 2026-03-02

## 전략 변경 이력

### v1→v2: 일괄 처리 → Pilot First

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| 1 | 87권 전체 인제스트 → 그래프 | 단순한 파이프라인 | 비검증 상태 투자 ~$36-49 | 기각 |
| 2 | Pilot First (4권 → QG → 전체) | 리스크 1/3, 조기 품질 검증 | 총 비용 약간 증가 | **v2 채택** |

### v2→v3: 87권 전체 → 카테고리당 3권 (12권)

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| 1 | 87권 전체 확장 (기존 v2) | 완전한 데이터 커버리지 | 로직 미검증 상태에서 대규모 투자 (~$33-43 추가) | 기각 |
| 2 | **카테고리당 3권 (12권) partially-full** | 전체 파이프라인 E2E 완성, 성능 평가 후 로직 개선 가능, 비용 절감 | 12권으로 cross-domain 다양성 제한 | **v3 채택** |
| 3 | 카테고리당 5권 (20권) | 더 나은 다양성 | 비용 증가, 평가 범위 과대 | 기각 |

**v3 채택 근거:**
1. **성능 평가 우선**: 87권 전체를 채우기 전에 파이프라인 성능(콘텐츠 생성 품질, 아이디어 유용성)을 먼저 검증
2. **로직 개선 기회**: 12권 데이터로 KU/Edge/Generation 로직 문제를 발견하고 개선
3. **비용 효율**: Phase 3에서 ~$12-20, 로직 확정 후 Phase 4에서 나머지 투자
4. **Cross-domain edge 문제**: 파일럿에서 0건 → 12권 규모에서 전략 개선 + 검증 필요

---

## H.cache: LLM 응답 캐시 설계

### 설계 대안

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| 1 | 파일 기반 캐시 (JSON 파일) | 간단 | 검색 느림, 관리 어려움 | 기각 |
| 2 | SQLite 캐시 (해시 키) | 빠른 조회, 토큰 사용량 추적 | 별도 DB 파일 | **채택** |
| 3 | Redis 캐시 | 고성능 | 외부 서비스 의존 | 기각 |

---

## 디버깅 이력 (Debug History)

| Bug # | Module | Issue | Fix | File |
|-------|--------|-------|-----|------|
| 1 | edge_builder | SQLite conn 멀티쓰레드 공유 시 ProgrammingError | KU 데이터 메인쓰레드에서 pre-load → dict로 전달 | `src/graph/edge_builder.py` |
| 2 | build_edges | OpenAI 429 quota exceeded (~50건) | 전체 0.4% 미만, 무시 가능 | `scripts/build_edges.py` |

### Bug-1: SQLite 멀티쓰레드 conn 공유

**증상:** `ThreadPoolExecutor`로 병렬 edge 생성 시 `sqlite3.ProgrammingError`
**원인:** `models.py`의 conn 객체를 worker 쓰레드에서 직접 사용
**수정:** `build_edges()`에서 KU 데이터를 메인 쓰레드에서 모두 읽어 dict로 전달

---

## 열린 질문 (Open Questions)

- [x] 파일럿 도서 구체적 선정 — 카탈로그 status=pilot 기반
- [ ] ChromaDB 18,000+ embedding 성능 — Phase 3 규모에서 확인
- [ ] Cross-domain edge 전략 — 임베딩 유사도 0.35로는 부족, 전용 전략 설계 필요 (I.partial)
- [ ] 성능 평가 기준 구체화 — Stage K에서 정량/정성 평가 방법 확정

---

## 교훈 (Lessons Learned)

- books-final-processor의 text.json 형식이 현재 파이프라인과 100% 호환
- CSV-JSON 매칭 시 공백 정규화가 핵심 (87/87 전부 매칭 가능)
- 기존 DB의 INSERT OR IGNORE 패턴 덕분에 배치 재실행이 안전
- **SQLite conn은 쓰레드 간 공유 불가** → pre-load 패턴
- **LLM strength 점수는 실질적 이진 판단** — fine-grained ranking 부적합
- **Cross-domain edge는 임베딩 유사도만으로 부족** — 전용 전략 필요
- **87권 전체 투자 전에 성능 평가가 필수** — 12권으로 E2E 검증 후 확장

---

## Modified Files Summary

```
수정 (완료):
├── src/ingest/ku_extractor.py    — DOMAIN_SHORT_MAP, domain_short 파라미터화, 캐시 래퍼 통합
├── src/vault/renderer.py         — _domain_to_dir(), Connections 섹션
├── src/cli.py                    — ks explore 명령 추가 ✅
├── src/db/models.py              — edge CRUD 3함수 추가 ✅
└── config.yaml                   — books 제거, catalog/batch 섹션 추가

신규 (완료):
├── src/ingest/llm_cache.py       — LLM 응답 캐시 ✅
├── books_catalog.yaml            — 87권 메타데이터 카탈로그 ✅
├── scripts/build_catalog.py      — 카탈로그 생성 ✅
├── scripts/migrate_data.py       — 데이터 마이그레이션 ✅
├── scripts/batch_ingest.py       — 배치 처리 ✅
├── scripts/build_edges.py        — 배치 edge 생성 ✅
├── src/graph/__init__.py         — graph 패키지 ✅
├── src/graph/edge_builder.py     — edge 생성 (쓰레드 안전) ✅
└── src/graph/traversal.py        — 그래프 탐색 ✅

신규 (예정):
├── src/graph/dispute.py          — Dispute axis 요약 (I.partial)
├── src/generation/idea.py        — 아이디어 생성 (J)
├── src/search/hybrid.py          — 복합 검색 (J)
└── reports/phase3_evaluation.md  — 성능 평가 리포트 (K)

리포트:
├── reports/pilot_quality.md      — KU 품질 리포트 ✅
└── reports/pilot_graph.md        — 그래프 품질 리포트 ✅
```
