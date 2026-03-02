# Phase 4: 전체 도서 확장 — Context
> Last Updated: 2026-03-02

## 1. 핵심 파일

### 수정 대상 (Phase 3에서 완성된 코드 재사용)

| 파일 | 용도 |
|------|------|
| `scripts/batch_ingest.py` | `--all` 모드로 75권 인제스트 |
| `scripts/build_edges.py` | 배치 edge 생성 |
| `src/graph/edge_builder.py` | Phase 3에서 개선된 cross-domain 전략 적용 |
| `src/graph/dispute.py` | 전체 도메인 dispute axis |
| `src/vault/renderer.py` | 전체 Vault connections |

### 신규 생성 예정

| 파일 | 용도 | Stage |
|------|------|-------|
| `reports/phase4_final.md` | 최종 품질 리포트 | P |

---

## 2. 데이터 스키마

Phase 3과 동일. 스키마 변경 없음.

### Phase 4 대상 도서

| 카테고리 | Phase 3 완료 | Phase 4 추가 | 최종 합계 |
|---------|-------------|-------------|----------|
| 역사/사회 | 3 | 15 | 18 |
| 경제/경영 | 3 | 25 | 28 |
| 인문/자기계발 | 3 | 15 | 18 |
| 과학/기술 | 3 | 20 | 23 |
| **합계** | **12** | **75** | **87** |

---

## 3. 주요 결정사항

| # | 결정 | 근거 |
|---|------|------|
| 1 | Phase 3 로직 개선 완료 확인 후 진행 | 미개선 로직으로 75권 투자 방지 |
| 2 | 기존 인프라/코드 100% 재사용 | Phase 3에서 파이프라인 완성됨 |

---

## 4. 컨벤션 체크리스트

Phase 3과 동일한 컨벤션 적용:
- [x] L0~L3 레이어 구조
- [x] KU/Edge 스키마
- [x] 인코딩 규칙
- [ ] 전체 규모 성능 확인 필요 (ChromaDB 75,000+, Obsidian vault)
