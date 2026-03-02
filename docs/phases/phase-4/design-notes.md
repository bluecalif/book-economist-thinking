# Phase 4: 전체 도서 확장 — Design Notes
> Last Updated: 2026-03-02

## 설계 대안 (Alternatives Considered)

| # | 대안 | 장점 | 단점 | 결정 |
|---|------|------|------|------|
| 1 | Phase 3에서 87권 전체 (기존 v2) | 한 번에 완성 | 로직 미검증 상태 투자 | 기각 → Phase 3/4 분리 |
| 2 | Phase 4에서 나머지 전체 일괄 | 단순 | 대규모 배치 리스크 | 도메인별 분할 실행 권장 |
| 3 | 도메인별 순차 확장 | 도메인별 모니터링 가능 | 느림 | 선택적 적용 |

## 열린 질문 (Open Questions)

- [ ] ChromaDB 75,000+ embedding 성능 — Phase 4에서 실제 확인
- [ ] Vault 75,000+ 파일 Obsidian 성능 — 대규모 vault 벤치마크 필요
- [ ] Phase 3 로직 개선 범위 — Stage K 결과에 따라 확정

## 교훈 (Lessons Learned)

(Phase 4 실행 시 업데이트 예정)

## Modified Files Summary

(Phase 4 실행 시 업데이트 예정)
