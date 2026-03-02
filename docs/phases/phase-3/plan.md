# Phase 3: Partially-Full (카테고리당 3권) + 성능 평가
> Last Updated: 2026-03-03
> Status: In Progress (H.partial ✅ → I.partial 대기)
> **전제:** Phase 2 완료 (1권 파이프라인 + 검색 + 생성 + CLI + Vault)

## 1. Summary (개요)

**목적:** 카테고리당 3권(총 12권)으로 KU + Edge + Generation + Search 파이프라인을 end-to-end 완성하고, 전체 프로젝트 성능과 목표 달성도를 평가한다. 필요 시 KU/Graph 로직을 개선한다.

**전략 변경 (v2→v3):** 87권 전체 확장 → **카테고리당 3권 partially-full**. 전체 파이프라인(L0~L3)을 소규모로 완성하고, 성능 평가 후 로직 개선을 거쳐 Phase 4에서 전체 확장.

**범위:**
- H.infra: 인프라 준비 (코드 수정, 카탈로그, 마이그레이션, LLM 캐시) ✅
- H.pilot: 4권 파일럿 인제스트 (도메인당 1권) ✅
- I.pilot: 파일럿 그래프 레이어 (edge 생성 + 탐색) ✅
- Quality Gate: 품질 판정 ✅ PASS
- **H.partial: 카테고리당 추가 2권 인제스트 (8권 추가 → 총 12권)**
- **I.partial: 12권 전체 edge 생성 + cross-domain edge**
- J: Generation 확장 (아이디어 생성 + 하이브리드 검색)
- **K: 성능 평가 + 로직 개선**

**예상 산출물:**
- 12권 KU + ChromaDB embeddings (~18,000 KU 추정)
- 12권 within-book + cross-domain edges
- `src/generation/idea.py` + `src/search/hybrid.py`
- 성능 평가 리포트 (`reports/phase3_evaluation.md`)
- 로직 개선 사항 (필요 시)

---

## 2. Current State (현재 상태)

| 항목 | 값 |
|------|---|
| Books | 12 (4개 도메인 × 3권 완료) |
| Raw Spans | 5,834 |
| Knowledge Units | 18,673 |
| ChromaDB Embeddings | 18,673 |
| Generations | 2 |
| Edges | 11,662 (파일럿 4권 within-book only) |
| LLM 캐시 | 구현 완료 |

### 도메인별 현황

| 카테고리 | 전체 | 완료 | KU 수 |
|---------|------|------|-------|
| 역사/사회 | 18 | 3 (노이즈, 2030축의전환, 노동의시대는끝났다) | 5,349 |
| 경제/경영 | 28 | 3 (경제학자의생각법, 경영의모험, 내러티브경제학) | 4,647 |
| 인문/자기계발 | 18 | 3 (공정하다는착각, 12가지인생의법칙, 나는왜이일을하는가) | 4,327 |
| 과학/기술 | 23 | 3 (대량살상수학무기, AI지도책, 그리드) | 4,350 |
| **합계** | **87** | **12** | **18,673** |

---

## 3. Target State (목표 상태)

Phase 3 완료 후:
- `ks stats` → books=12, spans≥5,000, kus≥18,000, chroma≥18,000
- Within-book + cross-domain edges 생성 완료
- `ks search "기술 혁신과 노동시장"` → 다수 도메인에서 KU 반환
- `ks explore ku-id --depth 2` → 연결된 KU 탐색
- `ks generate idea --mode business --domains 경제/경영,과학/기술` → 아이디어 생성
- **성능 평가 리포트**: 콘텐츠 생성 품질, 아이디어 유용성, cross-domain 가치 측정
- **로직 개선 사항 반영** (필요 시)

---

## 4. Implementation Stages

### 전체 흐름

```
H.infra ($0) ✅ → H.pilot (~$1) ✅ → I.pilot (~$3) ✅ → Quality Gate ✅
                                                           ↓ PASS
                                              H.partial (~$2.2) ✅ → I.partial (~$5-10)
                                                                        ↓
                                                              J ($0-1) → K ($1-3)
                                                                          ↓
                                                         로직 개선 완료 확인 → Phase 4
```

### Stage H.infra: 인프라 준비 ($0) — ✅ 완료

(기존과 동일, 6 Tasks 완료)

### Stage H.pilot: 파일럿 인제스트 (~$1) — ✅ 완료

(기존과 동일, 3 Tasks 완료)

### Stage I.pilot: 파일럿 그래프 (~$3) — ✅ 완료

(기존과 동일, 5 Tasks 완료)

### Quality Gate: 품질 판정 — ✅ PASS

(기존과 동일)

### Stage H.partial: 추가 8권 인제스트 (~$2.2) — ✅ 완료

8권 추가 인제스트 완료. 12권 전체 검증 통과. (books=12, kus=18,673)

### Stage I.partial: 12권 edge 생성 (~$5-10) — 4 Tasks

**목표:** 12권 전체 within-book edge + cross-domain edge 생성

- 신규 8권 within-book edge 생성
- **cross-domain edge 전략 개선** (기존 파일럿에서 0건 문제 해결)
- Vault connections 업데이트

**의존성:** H.partial 완료

### Stage J: Generation 확장 + Hybrid Search ($0-1) — 3 Tasks

**목표:** 아이디어 생성 파이프라인 + Vector+Graph 복합 검색

**의존성:** I.partial 완료

### Stage K: 성능 평가 + 로직 개선 ($1-3) — 4 Tasks

**목표:** 전체 파이프라인 성능 평가, 프로젝트 목표 달성도 측정, 필요 시 로직 개선

**평가 기준 (masterplan §15):**
| 기준 | 측정 방법 |
|------|----------|
| 콘텐츠 생성 품질 | 생성 초안의 50%+ 경미한 편집으로 게시 가능 |
| 아이디어 유용성 | 실행 가능한 아이디어 산출 여부 |
| Cross-domain 가치 | 단일 vs cross-domain 검색 비교 |
| 환각 방지 | 모든 주장이 KU source_spans로 추적 가능 |
| 파이프라인 안정성 | 새 책 추가 수동 개입 10분 이내 |

**로직 개선 대상 (잠재):**
- KU 추출 프롬프트 튜닝 (도메인별 최적화)
- Cross-domain edge 전략 (임베딩 유사도 외 토픽 기반 매칭)
- Strength 점수 보정 (현재 실질 이진 판단 문제)
- 생성 프롬프트 템플릿 다양화

**의존성:** J 완료

---

## 5. Task Breakdown

→ 상세: `tasks.md`

| Stage | Tasks | Size 분포 |
|-------|-------|----------|
| H.infra | 6 ✅ | S:4, M:2 |
| H.pilot | 3 ✅ | S:1, M:1, L:1 |
| I.pilot | 5 ✅ | S:2, M:2, L:1 |
| H.partial | 2 ✅ | M:1, L:1 |
| I.partial | 4 | S:1, M:2, L:1 |
| J | 3 | M:2, L:1 |
| K | 4 | S:1, M:2, L:1 |
| **합계** | **27** | 완료 16, 잔여 11 |

---

## 6. Risks & Mitigation

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Cross-domain edge 전략 부족 | 아이디어 생성 품질 저하 | I.partial에서 전용 전략 설계, 토픽 기반 매칭 실험 |
| 12권으로 성능 평가 한계 | 평가 신뢰도 부족 | 카테고리당 3권으로 최소 다양성 확보, 정성 평가 병행 |
| 로직 개선 범위 확대 | Phase 3 지연 | 핵심 개선만 Phase 3, 나머지는 Phase 4에서 |
| 생성 품질 미달 | 프로젝트 목표 재검토 필요 | Stage K에서 조기 발견, 프롬프트/전략 조정 |

---

## 7. Dependencies

### 내부 의존성

```
Phase 2 (완료) → H.infra ✅ → H.pilot ✅ → I.pilot ✅ → Quality Gate ✅
                                                           ↓ PASS
                                              H.partial → I.partial → J → K
                                                                         ↓
                                                              로직 개선 완료 → Phase 4
```

### 외부 의존성

| 의존성 | 용도 | 비용 |
|--------|------|------|
| OpenAI API (GPT-4.1-mini) | KU 추출, edge 생성 | ~$2.2 (8권) + ~$5-10 (edges) |
| OpenAI API (text-embedding-3-large) | 임베딩 | < $1 |
| books-final-processor text.json | 원본 텍스트 | 이미 복사 완료 |

---

## 8. 비용 추정

| 단계 | 항목 | 비용 | 상태 |
|------|------|------|------|
| H.infra~Quality Gate | 파일럿 KU + edge | ~$4 | ✅ 완료 |
| H.partial | 추가 8권 KU 추출 | ~$2.2 | ✅ 완료 |
| I.partial | 12권 edge 생성 | ~$5-10 | 대기 |
| J | 아이디어 생성 테스트 | ~$0-1 | 대기 |
| K | 성능 평가 (생성 테스트) | ~$1-3 | 대기 |
| **Phase 3 합계** | | **~$12-20** | |

**vs 기존 Phase 3 (87권):** ~$36-49 → **~$12-20** (60% 절감)
