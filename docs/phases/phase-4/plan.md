# Phase 4: 전체 도서 확장 (Full Scale)
> Last Updated: 2026-03-02
> Status: Planning
> **전제:** Phase 3 완료 (12권 partially-full + 성능 평가 + 로직 개선)

## 1. Summary (개요)

**목적:** Phase 3에서 검증/개선된 파이프라인으로 나머지 전체 도서(75권)를 처리하여 87권 완전 커버리지를 달성한다.

**전제 조건:**
- Phase 3 Stage K 성능 평가 완료
- 로직 개선 사항이 충분히 반영되었음을 확인
- 개선 미완료 시 Phase 3에서 추가 개선 후 진행

**범위:**
- M: 로직 개선 확인 + 사전 준비
- N: 나머지 75권 배치 인제스트
- O: 전체 87권 edge 생성 (within-book + cross-domain)
- P: 전체 시스템 통합 검증

**예상 산출물:**
- 87권 전체 KU + ChromaDB embeddings (~75,000+ KU)
- 87권 전체 edges (within-book + cross-domain)
- 전체 Vault 구조 (4개 도메인)
- 전체 시스템 통합 검증 리포트

---

## 2. Current State (Phase 3 완료 시 예상)

| 항목 | Phase 3 완료 시 예상 |
|------|---------------------|
| Books | 12 |
| KUs | ~18,000 |
| Edges | ~35,000 (within-book + cross-domain) |
| 파이프라인 상태 | L0~L3 완성, 성능 평가 완료 |
| 로직 개선 | Stage K에서 수행 완료 |

---

## 3. Target State (목표 상태)

Phase 4 완료 후:
- `ks stats` → books=87, spans≥25,000, kus≥75,000, chroma≥75,000
- 전체 도메인 cross-domain edges 완성
- Dispute axis 4개 도메인 간 자동 식별
- `ks generate idea --mode serendipity` → 전체 87권 KU 기반 아이디어
- 전체 Vault (4개 도메인 디렉터리)

---

## 4. Implementation Stages

### 전체 흐름

```
Phase 3 (12권 + 평가 + 개선) 완료
    ↓
M: 사전 확인 ($0) → N: 75권 인제스트 (~$21) → O: 전체 edge (~$15-30) → P: 통합 검증 ($0-1)
```

### Stage M: 사전 확인 ($0) — 2 Tasks

**목표:** Phase 3 로직 개선 완료 확인, 배치 전략 수립

- Phase 3 Stage K 결과 검토
- 개선된 프롬프트/전략 반영 확인
- 75권 배치 계획 (도메인별 분할, 시간/비용 추정)

### Stage N: 나머지 75권 인제스트 (~$21) — 3 Tasks

**목표:** 나머지 75권 KU 추출 + 임베딩

- `python scripts/batch_ingest.py --all` (done 자동 skip)
- 도메인별 분할 실행 가능
- 예상 비용: ~$0.28/권 × 75 = ~$21
- 예상 시간: 4-6시간

### Stage O: 전체 edge 생성 (~$15-30) — 4 Tasks

**목표:** 87권 전체 within-book + cross-domain edges

- 75권 within-book edge 생성
- 87권 cross-domain edge 생성 (Phase 3에서 개선된 전략 적용)
- Vault connections 전체 업데이트
- Dispute axis 전체 도메인 요약

### Stage P: 통합 검증 ($0-1) — 2 Tasks

**목표:** 전체 시스템 E2E 검증

- `ks stats` 전체 메트릭 확인
- 콘텐츠/아이디어 생성 전체 규모 테스트
- 최종 품질 리포트

---

## 5. Task Breakdown

| Stage | Tasks | Size 분포 |
|-------|-------|----------|
| M | 2 | S:1, M:1 |
| N | 3 | S:1, M:1, L:1 |
| O | 4 | M:2, L:2 |
| P | 2 | S:1, M:1 |
| **합계** | **11** | |

---

## 6. Risks & Mitigation

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 75,000+ KU ChromaDB 성능 | 검색 지연 | 벤치마크 후 필요 시 인덱스 최적화 |
| Vault 75,000+ 파일 Obsidian 성능 | UX 저하 | 도메인별 분리 vault 옵션 |
| 배치 중단 | 재처리 비용 | LLM 캐시 + 체크포인트 |
| Phase 3 로직 개선 미완료 | Phase 4 품질 저하 | Stage M에서 게이트 판정, 미완료 시 Phase 3 재진입 |

---

## 7. Dependencies

### 내부 의존성

```
Phase 3 (완료 필수) → M → N → O → P
```

**핵심 전제:** Phase 3 Stage K의 로직 개선이 완료된 상태여야 함

### 외부 의존성

| 의존성 | 용도 | 비용 |
|--------|------|------|
| OpenAI API (GPT-4.1-mini) | KU 추출, edge 생성 | ~$21 (75권) + ~$15-30 (edges) |
| OpenAI API (text-embedding-3-large) | 임베딩 | ~$2 |

---

## 8. 비용 추정

| 단계 | 항목 | 비용 |
|------|------|------|
| N | 75권 KU 추출 | ~$21 |
| O | 전체 edge 생성 | ~$15-30 |
| P | 검증 (생성 테스트) | ~$0-1 |
| **Phase 4 합계** | | **~$36-52** |

**총 프로젝트 비용 (Phase 1~4):**
- Phase 1-2: ~$5
- Phase 3: ~$12-20
- Phase 4: ~$36-52
- **합계: ~$53-77**
