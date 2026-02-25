# Project Status
> Last Updated: 2026-02-25

## Overview

| Phase | Status | Progress | 핵심 산출물 |
|-------|--------|----------|------------|
| Phase 1: 1권 MVP | Planning | 0% | ingest → search → generate 파이프라인 |
| Phase 2: 그래프+아이디어 | - | - | edge_builder, traversal, idea.py |
| Phase 3: 87권+진화 | - | - | 배치 처리, crawler, hybrid search |
| Phase 4: 웹 UI | - | - | FastAPI, 프론트엔드 |

## Phase 1: 1권 MVP

**목표:** 경제학자의 생각법 1권으로 전체 파이프라인(ingest → search → generate) 완성 + 생성 기능 가치 검증

**범위:** L0 Raw + L1 KU + L3 Generation (기본) + Search + CLI + Vault

**설계 문서:** `docs/phases/phase-1-mvp/`

### 작업 현황

| Stage | 작업 | 상태 | 산출물 |
|-------|------|------|--------|
| A | 프로젝트 초기화 | 대기 | `pyproject.toml`, 디렉터리 구조 |
| B | DB 스키마 | 대기 | `src/db/models.py`, `src/db/vectors.py` |
| C | PDF 파싱 | 대기 | `src/ingest/pdf_parser.py` |
| D | KU 추출 | 대기 | `src/ingest/ku_extractor.py` |
| E | 의미 검색 | 대기 | `src/search/vector.py` |
| F | 콘텐츠 생성 | 대기 | `src/generation/content.py`, 템플릿 |
| G | CLI + Vault | 대기 | `src/cli.py`, `src/vault/renderer.py` |

### 완료 기준 (masterplan §14)

- [ ] `ks ingest book.pdf` → KU 추출 + DB 저장 + 마크다운 생성
- [ ] `ks search "매몰비용"` → 관련 KU 반환
- [ ] `ks generate content --topic "매몰비용" --format blog` → 블로그 초안 생성
- [ ] 생성된 콘텐츠가 실제 사용 가능한 품질인지 평가

## Phase 2: 그래프 + 아이디어 + 5권 확장

**목표:** Cross-domain 연결의 가치 검증

**범위:** L2 Graph + L3 Generation (아이디어) + 5권 배치

**설계 문서:** (Phase 1 완료 후 생성)

### 완료 기준 (masterplan §14)

- [ ] `ks explore ku-id --depth 2` → 연결된 KU 탐색
- [ ] `ks generate idea --mode business --domains 경제,기술` → 아이디어 후보 생성
- [ ] Cross-domain 연결에서 실제로 유용한 통찰이 나오는지 평가

## Phase 3: 87권 완료 + 진화

**목표:** 전체 규모 달성 + 외부 지식 유입

**범위:** L4 Evolution + 배치 확장 + Hybrid Search

**설계 문서:** (Phase 2 완료 후 생성)

### 완료 기준 (masterplan §14)

- [ ] 87권 전체 처리 완료
- [ ] `ks crawl --ku ku-id` → 웹에서 보강 정보 수집 + KU 업데이트 제안
- [ ] 7개 도메인 간 dispute 축 자동 식별

## Phase 4: 웹 UI (선택)

**조건:** Phase 1-3의 가치 검증 결과 필요시만 진행

**범위:** FastAPI + 경량 프론트엔드

## Key Decisions

| 날짜 | 결정 | 근거 | 영향 범위 |
|------|------|------|----------|
| 2026-02-25 | v2.0 전면 재설계 | Generation-first, 87권 확장, CLI 우선 | 전체 |
| 2026-02-25 | Python CLI + SQLite/ChromaDB | 로컬 우선, 단일 언어, 마이그레이션 가능 | 전체 |
| 2026-02-25 | 1권 MVP → 점진적 확장 | 매 단계 가치 검증, 파이프라인 완성 후 배치 | 실행 전략 |
| 2026-02-25 | L3 Dispute → L2 하위 기능 | contradicts edge 클러스터로 처리 | L2, L3 |
| 2026-02-25 | 기존 파싱 데이터 활용 | 55bbe4 structure/text JSON 존재 | Phase 1 Stage C |
