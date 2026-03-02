# Phase 4: 전체 도서 확장 — Tasks
> Last Updated: 2026-03-02

## Progress: 0/11 Tasks (0%)

---

### Stage M: 사전 확인 ($0) — 0/2

- [ ] M.1 Phase 3 로직 개선 완료 확인
  - Stage K 성능 평가 리포트 검토
  - KU 추출 프롬프트 최종 버전 확정
  - Edge 전략 (cross-domain 포함) 최종 확정
  - 미완료 사항 있으면 Phase 3 재진입 결정
- [ ] M.2 75권 배치 전략 수립
  - 도메인별 분할 실행 계획
  - 시간/비용 최종 추정
  - rate limit 대응 전략

---

### Stage N: 나머지 75권 인제스트 (~$21) — 0/3

- [ ] N.1 75권 배치 인제스트 실행
  - `python scripts/batch_ingest.py --all` (done 자동 skip)
  - 도메인별 분할 실행 권장
  - 예상 시간: 4-6시간
- [ ] N.2 전체 검증
  - `ks stats` → books=87, spans≥25,000, kus≥75,000
  - 도메인별 KU 분포 확인
- [ ] N.3 Vault 재렌더링
  - 4개 도메인 Vault 디렉터리 구조 확인
  - 75,000+ 파일 Obsidian 성능 벤치마크

---

### Stage O: 전체 edge 생성 (~$15-30) — 0/4

- [ ] O.1 75권 within-book edge 생성
  - `python scripts/build_edges.py` (기존 done 자동 skip)
- [ ] O.2 전체 cross-domain edge 생성
  - Phase 3에서 개선된 전략 적용
  - 87권 4개 도메인 간 교차 edge
- [ ] O.3 Vault connections 전체 업데이트
  - 실제 edge 기반 [[wikilink]] 생성
- [ ] O.4 Dispute axis 전체 도메인 요약
  - contradicts edge 클러스터 분석
  - 4개 도메인 간 논쟁 축 자동 식별

---

### Stage P: 통합 검증 ($0-1) — 0/2

- [ ] P.1 전체 시스템 E2E 검증
  - `ks stats` 전체 메트릭 최종 확인
  - `ks search`, `ks explore`, `ks generate content`, `ks generate idea` 전체 규모 테스트
- [ ] P.2 최종 품질 리포트
  - 87권 규모 성능 평가
  - Phase 3 12권 대비 품질 변화 분석
  - `reports/phase4_final.md` 출력

---

## Stage 의존성

```
Phase 3 완료 (K.4 로직 개선 확인)
    ↓
M (M.1→M.2) → N (N.1→N.2→N.3) → O (O.1→O.2→O.3, O.2→O.4) → P (P.1→P.2)
```
