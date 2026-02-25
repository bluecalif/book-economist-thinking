# Knowledge System 설계 문서 v2.0

> Generation-First, Incrementally Scalable Knowledge Pipeline

---

## 0. 문서 이력

| 버전 | 날짜 | 변경 |
|------|------|------|
| v1.0 | 2026-02 | 초기 설계 (FastAPI + Next.js, 단일 책 대상) |
| v2.0 | 2026-02-25 | 전면 재설계 — Python Pipeline + LLM API + 경량 DB, 87권 대상, 생성 중심 |

### v1.0 → v2.0 핵심 변경

| 항목 | v1.0 | v2.0 |
|------|------|------|
| 대상 | 경제학 1권 | **87권, 7개 도메인** |
| 스택 | FastAPI + Next.js + Supabase | **Python CLI + LLM API + SQLite/ChromaDB** |
| 핵심 기능 | 지식 구조화 + 검색 | **생성(콘텐츠/아이디어) + 지식 구조화** |
| 진화 메커니즘 | Usage-driven PR 모델 | **웹 크롤링 + 반자동 KU 확장** |
| 프론트엔드 | Next.js SPA | **CLI 우선, 웹 UI는 Phase 4+** |
| 실행 전략 | Waterfall (Phase 1→2→3) | **1권 MVP → 점진적 확장 + 매 단계 가치 검증** |

---

## 1. 프로젝트 목적

87권(인문, 사회, 역사, 경제, 과학, 기술, 경영)의 도서를 구조화된 지식 시스템으로 변환하여:

1. **콘텐츠 생성 엔진** — KU 기반 블로그, 뉴스레터, 교육 콘텐츠 초안 자동 생성
2. **아이디어 발견 엔진** — Cross-domain KU 조합으로 비즈니스/콘텐츠 아이디어 탐색
3. **도메인 간 지식 연결** — 7개 도메인의 교차점에서 새로운 통찰 발견
4. **지식 진화** — 웹 크롤링으로 외부 지식을 흡수하여 KU를 지속 보강

### 핵심 원칙

- **Generation-first**: 지식을 쌓는 것이 아니라 **사용하는 것**이 목적. 모든 설계 결정은 "이것이 더 나은 콘텐츠/아이디어를 생성하는 데 기여하는가?"로 판단
- **Incremental value**: 매 단계에서 즉시 사용 가능한 가치를 산출. "지식의 묘지" 방지
- **1권 완성 → 배치 확장**: 파이프라인을 1권에서 완성한 후 87권으로 확장

---

## 2. 기술 스택

| 계층 | 기술 | 근거 |
|------|------|------|
| 언어 | Python 3.11+ | 데이터 파이프라인 + LLM API 생태계 최적 |
| LLM API | Claude / GPT-4o / GPT-4o mini | KU 추출, 생성, 그래프 구축 |
| 임베딩 | text-embedding-3-small (OpenAI) 또는 동급 | 비용 효율적 의미 검색 |
| Vector DB | ChromaDB (로컬) | 설치 즉시 사용, 13,000 KU 규모 충분 |
| 관계형 DB | SQLite | 로컬, 제로 설정, 마이그레이션 용이 |
| CLI | Click 또는 Typer | Python CLI 프레임워크 |
| 마크다운 출력 | Obsidian 호환 | 시각적 탐색 + 수동 편집 병행 |
| 웹 크롤링 | Requests + BeautifulSoup / Playwright | L4 Phase에서 도입 |
| API 서버 | FastAPI | Phase 4+에서 필요시 도입 |

### 스택 선정 원칙

- **로컬 우선**: 외부 서비스 의존 최소화 (LLM API 제외)
- **마이그레이션 가능**: SQLite → PostgreSQL, ChromaDB → pgvector 전환 경로 확보
- **단일 언어**: Python으로 통일하여 개발/유지 비용 최소화

---

## 3. 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                    CLI Interface                     │
│  search · generate · explore · ingest · crawl        │
├──────────┬──────────┬──────────┬──────────┬──────────┤
│  L0 Raw  │  L1 KU   │ L2 Graph │  L3 Gen  │ L4 Evo  │
│  원본     │  지식단위  │  관계     │  생성     │  진화    │
├──────────┴──────────┴──────────┴──────────┴──────────┤
│               Storage (SQLite + ChromaDB)             │
├──────────────────────────────────────────────────────┤
│               Markdown Vault (Obsidian 호환)          │
└──────────────────────────────────────────────────────┘
```

### v1.0과의 구조적 차이

- **L3 → Gen(생성)으로 교체**: v1.0의 L3(Dispute Axis)는 Phase 3으로 이동. 생성 레이어가 그 자리를 차지
- **Dispute Axis는 L2의 하위 기능으로 흡수**: 별도 레이어가 아닌 Graph Layer의 edge 타입(`contradicts`)으로 처리. 다저자 환경에서 자연 발생
- **L4 Evolution = 웹 크롤링 중심**: PR 모델 대신 외부 정보 흡수 + 반자동 KU 확장

---

## 4. L0 — Raw Text Layer

### 목적

- 원본 텍스트 보존 (불변)
- 모든 KU의 근거 추적 원점
- PDF 파싱 결과 저장

### 스키마

```sql
CREATE TABLE books (
    id          TEXT PRIMARY KEY,   -- 예: 'econ-thinking-001'
    title       TEXT NOT NULL,
    author      TEXT,
    domain      TEXT NOT NULL,      -- 인문|사회|역사|경제|과학|기술|경영
    filepath    TEXT,               -- 원본 PDF 경로
    total_pages INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE raw_spans (
    id          TEXT PRIMARY KEY,   -- 예: 'econ-thinking-001-ch03-p042-s005'
    book_id     TEXT NOT NULL REFERENCES books(id),
    chapter     TEXT,
    page        INTEGER,
    seq         INTEGER,            -- 챕터 내 순서
    text        TEXT NOT NULL,
    span_type   TEXT DEFAULT 'paragraph',  -- paragraph|heading|list|table
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 처리 파이프라인

```
PDF → PyMuPDF/pdfplumber → 챕터/페이지 분할 → raw_spans 저장
```

---

## 5. L1 — Knowledge Unit Layer

### KU 정의

KU는 **claim + evidence로 구성된 최소 논증 단위**. v1.0의 핵심 설계를 계승.

### 스키마

```sql
CREATE TABLE knowledge_units (
    id                  TEXT PRIMARY KEY,   -- 예: 'ku-econ-001-0042'
    book_id             TEXT NOT NULL REFERENCES books(id),
    claim               TEXT NOT NULL,       -- 핵심 주장 (1-2문장)
    evidence_summary    TEXT,                -- 근거 요약
    counter_summary     TEXT,                -- 반례/한계 요약 (있을 경우)
    domain              TEXT NOT NULL,       -- 1차 도메인
    subdomain           TEXT,                -- 세부 분야 (예: 행동경제학)
    tags                TEXT,                -- JSON array, 키워드 태그
    confidence          REAL DEFAULT 0.5,    -- 0.0-1.0
    maturity            TEXT DEFAULT 'M0',   -- M0|M1|M2
    source_spans        TEXT,                -- JSON array of raw_span ids
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Maturity 모델 (간소화)

| 단계 | 조건 | 설명 |
|------|------|------|
| M0 | LLM 자동 추출 | claim + evidence 존재, 미검증 |
| M1 | 수동 검토 완료 | claim 정확성, evidence 매핑 확인 |
| M2 | 외부 지식 보강 | 웹 크롤링 또는 다른 책의 KU와 교차 검증 완료 |

> v1.0의 M3(사용자 피드백 반영)은 제거. 1인 환경에서 M0→M1→M2가 충분.

### KU 추출 프롬프트 전략

```
[System] 당신은 책의 내용을 구조화된 지식 단위로 추출하는 전문가입니다.

[User] 다음 텍스트에서 Knowledge Unit을 추출하세요.

규칙:
1. 각 KU는 하나의 명확한 claim(주장)을 가져야 합니다
2. claim을 뒷받침하는 evidence(근거)를 원문에서 인용하세요
3. 저자가 제시한 한계나 반례가 있으면 counter로 기록하세요
4. claim이 없는 서술(배경 설명, 일화 등)은 KU로 추출하지 마세요
5. 하나의 텍스트에서 여러 KU가 나올 수 있습니다

출력 형식: JSON array
[{"claim": "...", "evidence_summary": "...", "counter_summary": "...", "tags": [...]}]

텍스트:
{chunk_text}
```

---

## 6. L2 — Graph Layer

### 목적

- KU 간 관계 모델링
- Cross-domain 연결 탐색
- 콘텐츠/아이디어 생성의 시드 제공

### 스키마

```sql
CREATE TABLE edges (
    id              TEXT PRIMARY KEY,
    from_ku_id      TEXT NOT NULL REFERENCES knowledge_units(id),
    to_ku_id        TEXT NOT NULL REFERENCES knowledge_units(id),
    relation_type   TEXT NOT NULL,      -- explains|supports|contradicts|extends|example_of|analogous_to
    strength        REAL DEFAULT 0.5,   -- 0.0-1.0
    source          TEXT DEFAULT 'auto', -- auto|manual|crawl
    description     TEXT,               -- 관계 설명 (1문장)
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edges_from ON edges(from_ku_id);
CREATE INDEX idx_edges_to ON edges(to_ku_id);
CREATE INDEX idx_edges_type ON edges(relation_type);
```

### Edge 타입

| 타입 | 의미 | 예시 |
|------|------|------|
| `explains` | A가 B를 설명 | "비교우위" explains "무역 이득" |
| `supports` | A가 B를 뒷받침 | 실험 결과 supports 이론적 주장 |
| `contradicts` | A와 B가 상충 | 효율시장가설 contradicts 행동경제학 |
| `extends` | A가 B를 확장 | 게임이론 extends 합리적 선택 |
| `example_of` | A가 B의 사례 | 죄수의 딜레마 example_of 게임이론 |
| `analogous_to` | A와 B가 유사 구조 | 자연선택 analogous_to 시장 경쟁 |

### Edge 생성 전략

**Phase 1 (책 내부):** 같은 책의 KU 간 관계를 LLM으로 자동 제안 → 수동 확인

**Phase 2 (책 간 / cross-domain):** 서로 다른 책의 KU를 임베딩 유사도로 후보 추출 → LLM으로 관계 타입 판정

```python
# Cross-domain edge 후보 탐색 (의사 코드)
for ku_a in domain_A_kus:
    similar_kus = vector_search(ku_a.embedding, domain=other_domains, top_k=5)
    for ku_b in similar_kus:
        if cosine_similarity(ku_a, ku_b) > 0.7:
            edge_candidate = llm_judge_relation(ku_a, ku_b)
            if edge_candidate.confidence > 0.6:
                save_edge(edge_candidate)
```

### Dispute Axis (L2 하위 기능)

v1.0의 L3 Dispute Axis는 별도 레이어가 아닌 **`contradicts` edge의 클러스터**로 처리:

```sql
-- 논쟁 축 = contradicts edge가 밀집된 KU 그룹
CREATE VIEW dispute_clusters AS
SELECT from_ku_id, to_ku_id, description
FROM edges
WHERE relation_type = 'contradicts'
ORDER BY strength DESC;
```

5권 이상 등록 후 `contradicts` edge가 충분히 축적되면, LLM으로 논쟁 축을 자동 요약:
- "시장 효율성에 대한 상반된 견해" (경제 vs 행동경제학)
- "기술 결정론 vs 사회 구성론" (기술 vs 사회)

---

## 7. L3 — Generation Layer

> **v2.0의 핵심 차별화.** v1.0에서 부차적이었던 생성 기능을 1등 시민으로 격상.

### 두 가지 생성 모드

#### 7.1 콘텐츠 생성 (Content Generation)

```python
# CLI 사용 예
$ ks generate content --topic "매몰비용" --format blog --depth deep
$ ks generate content --topic "게임이론의 실생활 적용" --format thread
$ ks generate content --ku ku-econ-001-0042,ku-mgmt-003-0015 --format newsletter
```

**파이프라인:**

```
1. 토픽/KU 지정
2. 관련 KU 검색 (Vector Search + Graph 1-hop)
3. KU 컨텍스트 조합 (claim + evidence + 관련 KU)
4. 프롬프트 템플릿 적용
5. LLM 호출 → 초안 생성
6. 출력 저장 (마크다운 + 사용된 KU ID 기록)
```

**지원 포맷:**

| 포맷 | 설명 | 예상 길이 |
|------|------|----------|
| `blog` | 블로그 포스트 | 1,500-3,000자 |
| `thread` | 소셜미디어 스레드 | 5-10개 항목 |
| `newsletter` | 뉴스레터 섹션 | 500-1,000자 |
| `lecture` | 강의 노트 | 2,000-5,000자 |
| `summary` | 개념 요약 | 300-500자 |

#### 7.2 아이디어 생성 (Idea Generation)

```python
# CLI 사용 예
$ ks generate idea --mode business --domains 경제,기술
$ ks generate idea --mode content --ku ku-hist-005-0023 --cross-domain
$ ks generate idea --mode serendipity  # 랜덤 cross-domain 조합
```

**파이프라인:**

```
1. 도메인/KU 선택 (또는 랜덤)
2. Cross-domain KU 쌍 탐색 (Graph traversal + analogous_to edges)
3. 교차점 분석 프롬프트 → LLM 호출
4. 아이디어 후보 생성 (비즈니스 모델, 콘텐츠 시리즈, 교육 커리큘럼 등)
5. 출력 저장 + 사용된 KU 역참조 기록
```

**아이디어 모드:**

| 모드 | 설명 |
|------|------|
| `business` | 비즈니스 모델/서비스 아이디어 |
| `content` | 콘텐츠 시리즈/주제 기획 |
| `serendipity` | 랜덤 cross-domain 조합에서 발견 |

### 생성 품질 관리

- 생성 결과에 항상 **출처 KU ID**를 첨부 → 근거 추적 가능
- 생성 이력을 DB에 기록 → 어떤 KU가 자주 사용되는지 추적 (자연적 usage data)
- 생성 결과의 사용자 평가 (간단한 👍/👎) → KU confidence 업데이트 입력

```sql
CREATE TABLE generations (
    id          TEXT PRIMARY KEY,
    mode        TEXT NOT NULL,      -- content|idea
    format      TEXT,               -- blog|thread|newsletter|...
    prompt      TEXT,               -- 사용된 프롬프트
    output      TEXT NOT NULL,      -- 생성 결과
    ku_ids      TEXT NOT NULL,      -- JSON array, 사용된 KU ID 목록
    rating      INTEGER,            -- NULL|1(👎)|2(👍)
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. L4 — Evolution Layer

### 목적

외부 지식을 흡수하여 기존 KU를 보강하고, 시스템의 지식 범위를 확장.

### 8.1 웹 크롤링 기반 KU 확장

```python
# CLI 사용 예
$ ks crawl --ku ku-econ-001-0042 --sources academic,news
$ ks crawl --domain 기술 --topic "생성형 AI" --limit 10
```

**파이프라인:**

```
1. 대상 KU 또는 토픽 선택
2. 웹 검색 (Google Scholar, 뉴스, 블로그)
3. 관련 콘텐츠 수집 + 요약
4. 기존 KU와 비교 분석 (LLM)
5. 확장 제안 생성:
   - 기존 KU의 evidence 보강
   - 새로운 counter_summary 추가
   - 신규 KU 후보 제안
6. 사용자 승인 후 반영
```

### 8.2 수동 편집

모든 KU는 마크다운으로도 존재하므로 Obsidian에서 직접 편집 가능. 편집 후 `ks sync` 명령으로 DB와 동기화.

```python
$ ks sync  # vault/ 마크다운 변경사항 → DB 반영
```

### 8.3 Maturity 자동 승격

v1.0의 Usage-driven maturation을 간소화:

| 조건 | 동작 |
|------|------|
| 생성에 3회 이상 사용 + 평균 rating ≥ 2 | M0 → M1 후보 제안 |
| 외부 소스로 evidence 보강 완료 | M1 → M2 후보 제안 |
| cross-domain edge 2개 이상 검증 | confidence +0.1 |

> v1.0의 "검색 20회, 사용 5회" 임계치를 대폭 낮춤. 1인 사용 현실에 맞게 조정.

---

## 9. Search (기능 모듈)

> 별도 레이어가 아닌 L1+L2를 조합한 **기능 모듈**.

### 9.1 의미 검색 (Vector Search)

```python
$ ks search "인센티브가 행동을 바꾸는 메커니즘"
$ ks search "시장 실패" --domain 경제,경영
```

ChromaDB에서 임베딩 유사도 검색. 결과에 KU의 claim, domain, confidence 표시.

### 9.2 그래프 탐색 (Graph Traversal)

```python
$ ks explore ku-econ-001-0042 --depth 2
$ ks explore --domain 경제 --cross-domain  # 경제 KU에서 다른 도메인으로 연결된 KU
```

특정 KU에서 edge를 따라 연결된 KU를 탐색. depth 지정 가능.

### 9.3 복합 검색 (Phase 2+)

```
1. Vector Search로 시드 KU 탐색
2. Graph 1-2 hop 확장
3. PathScore로 경로 순위 매기기 (v1.0의 설계 계승)
```

```
PathScore = HarmonicMean(edge_strengths) × Mean(KU_confidence)
```

> v1.0의 `(1 - contradiction_density)` 항 제거. `contradicts` edge도 아이디어 생성에서는 가치 있으므로 페널티가 아닌 정보로 취급.

---

## 10. CLI 인터페이스

### 명령어 체계

```
ks ingest <pdf_path>          -- PDF → L0+L1 처리
ks ingest --batch <dir_path>  -- 디렉터리 내 PDF 일괄 처리

ks search <query>             -- 의미 검색
ks explore <ku_id>            -- 그래프 탐색

ks generate content           -- 콘텐츠 생성
ks generate idea              -- 아이디어 생성

ks crawl                      -- 웹 크롤링으로 KU 확장
ks sync                       -- 마크다운 ↔ DB 동기화

ks stats                      -- 시스템 통계 (KU 수, 도메인 분포, 생성 이력)
ks export                     -- JSON/CSV 내보내기
```

---

## 11. 마크다운 Vault 구조 (Obsidian 호환)

```
vault/
├── index.md                          — 전체 지식 맵
├── domains/
│   ├── 경제/
│   │   ├── _index.md                 — 도메인 개요 + KU 목록
│   │   ├── ku-econ-001-0001.md       — 개별 KU 노트
│   │   └── ...
│   ├── 기술/
│   ├── 경영/
│   ├── 역사/
│   ├── 사회/
│   ├── 과학/
│   └── 인문/
├── cross-domain/
│   ├── 경제-기술.md                   — Cross-domain 연결 요약
│   └── ...
├── disputes/
│   └── dispute-summaries.md          — 논쟁 축 요약 (자동 생성 + 수동 보강)
└── outputs/
    ├── content/                       — 생성된 콘텐츠
    └── ideas/                         — 생성된 아이디어
```

### KU 마크다운 노트 형식

```markdown
---
id: ku-econ-001-0042
book: 경제학자의 생각법
domain: 경제
subdomain: 행동경제학
confidence: 0.7
maturity: M1
tags: [매몰비용, 의사결정, 인지편향]
created: 2026-02-25
---

# 매몰비용 오류는 손실회피와 결합하여 비합리적 지속을 유발한다

## Claim
이미 투입된 비용(매몰비용)은 미래 의사결정에 영향을 주지 않아야 하지만,
손실회피 편향과 결합하면 실패한 프로젝트를 계속 유지하는 비합리적 행동을 유발한다.

## Evidence
- "콩코드 오류" 사례: 영불 정부의 초음속 여객기 개발 지속 (p.127)
- Arkes & Blumer(1985) 실험: 티켓 가격이 참석률에 영향 (p.130)

## Counter
- 매몰비용 고려가 합리적인 경우도 존재: 평판 비용, 학습 효과 (p.133)

## Connections
- [[ku-econ-001-0038]] — explains: 손실회피 편향의 일반 이론
- [[ku-mgmt-005-0012]] — analogous_to: 기업의 좀비 프로젝트 현상
```

---

## 12. 디렉터리 구조

```
knowledge-system/
├── src/
│   ├── __init__.py
│   ├── cli.py                  — CLI 진입점 (Click/Typer)
│   ├── ingest/
│   │   ├── pdf_parser.py       — PDF → raw_spans
│   │   └── ku_extractor.py     — raw_spans → KU (LLM API)
│   ├── graph/
│   │   ├── edge_builder.py     — KU → edges (LLM API)
│   │   └── traversal.py        — 그래프 탐색 로직
│   ├── search/
│   │   ├── vector.py           — ChromaDB 검색
│   │   └── hybrid.py           — Vector + Graph 복합 검색
│   ├── generation/
│   │   ├── content.py          — 콘텐츠 생성 파이프라인
│   │   ├── idea.py             — 아이디어 생성 파이프라인
│   │   └── templates/          — 프롬프트 템플릿
│   ├── evolution/
│   │   ├── crawler.py          — 웹 크롤링
│   │   └── sync.py             — 마크다운 ↔ DB 동기화
│   ├── db/
│   │   ├── models.py           — SQLite 스키마 + CRUD
│   │   └── vectors.py          — ChromaDB 래퍼
│   └── vault/
│       └── renderer.py         — KU → 마크다운 렌더링
│
├── data/
│   ├── knowledge.db            — SQLite 데이터베이스
│   ├── chroma/                 — ChromaDB 임베딩 데이터
│   └── raw/                    — 원본 PDF 또는 파싱 결과
│
├── vault/                      — Obsidian 호환 마크다운
│   └── (§11 구조 참조)
│
├── config.yaml                 — 설정 (API 키, 모델 선택, 경로 등)
├── pyproject.toml              — 패키지 설정
└── README.md
```

---

## 13. 비용 추정

### MVP (1권)

| 항목 | 비용 |
|------|------|
| KU 추출 (LLM API) | $2-5 |
| 임베딩 | < $0.01 |
| Edge 생성 | $1-3 |
| 생성 테스트 (10회) | $0.5-2 |
| **합계** | **$3-10** |

### Full Scale (87권)

| 항목 | 비용 |
|------|------|
| KU 추출 (GPT-4o mini 기준) | $100-200 |
| 임베딩 | $2-3 |
| Edge 생성 (책 내 + cross-domain) | $50-100 |
| 웹 크롤링 LLM 호출 | $20-50/월 |
| **초기 합계** | **$150-350** |
| **월간 운영** | **$20-50** |

> GPT-4o mini 사용 시 비용 대폭 절감. 품질 검증 후 필요한 부분만 GPT-4o/Claude로 재처리.

---

## 14. 실행 로드맵

### Phase 1: 1권 MVP (Week 1-2)

**목표:** 파이프라인 완성 + 생성 기능 가치 검증

| 작업 | 산출물 |
|------|--------|
| PDF 파싱 파이프라인 | `ingest/pdf_parser.py` |
| KU 추출 파이프라인 | `ingest/ku_extractor.py` + 100-200 KU |
| SQLite + ChromaDB 설정 | `db/models.py`, `db/vectors.py` |
| 의미 검색 | `search/vector.py` |
| 콘텐츠 생성 (기본) | `generation/content.py` + 템플릿 3종 |
| CLI (ingest, search, generate) | `cli.py` |
| 마크다운 출력 | `vault/renderer.py` |

**Phase 1 완료 기준:**
- [ ] `ks ingest book.pdf` → KU 추출 + DB 저장 + 마크다운 생성
- [ ] `ks search "매몰비용"` → 관련 KU 반환
- [ ] `ks generate content --topic "매몰비용" --format blog` → 블로그 초안 생성
- [ ] 생성된 콘텐츠가 실제 사용 가능한 품질인지 평가

### Phase 2: 그래프 + 아이디어 + 5권 확장 (Week 3-4)

**목표:** Cross-domain 연결의 가치 검증

| 작업 | 산출물 |
|------|--------|
| Edge 자동 생성 | `graph/edge_builder.py` |
| 그래프 탐색 | `graph/traversal.py` |
| 아이디어 생성 | `generation/idea.py` |
| 5권 배치 처리 | 500-1,000 KU + cross-domain edges |
| CLI (explore, generate idea) | CLI 확장 |

**Phase 2 완료 기준:**
- [ ] `ks explore ku-id --depth 2` → 연결된 KU 탐색
- [ ] `ks generate idea --mode business --domains 경제,기술` → 아이디어 후보 생성
- [ ] Cross-domain 연결에서 실제로 유용한 통찰이 나오는지 평가

### Phase 3: 87권 완료 + 진화 (Month 2-3)

**목표:** 전체 규모 달성 + 외부 지식 유입

| 작업 | 산출물 |
|------|--------|
| 87권 배치 처리 | 10,000-15,000 KU |
| Cross-domain edge 대규모 생성 | 수천 개 edges |
| 웹 크롤링 모듈 | `evolution/crawler.py` |
| Dispute 자동 요약 | `contradicts` edge 클러스터 분석 |
| 복합 검색 (Hybrid) | `search/hybrid.py` |
| 마크다운 ↔ DB 동기화 | `evolution/sync.py` |

**Phase 3 완료 기준:**
- [ ] 87권 전체 처리 완료
- [ ] `ks crawl --ku ku-id` → 웹에서 보강 정보 수집 + KU 업데이트 제안
- [ ] 7개 도메인 간 dispute 축 자동 식별

### Phase 4: 웹 UI (Month 3+, 선택)

**조건:** Phase 1-3의 가치 검증 결과 웹 UI가 필요하다고 판단될 때만

| 작업 | 산출물 |
|------|--------|
| FastAPI 엔드포인트 | `api/server.py` |
| 경량 프론트엔드 | 그래프 시각화 + 생성 UI |

---

## 15. 성공 기준

| 기준 | 측정 방법 |
|------|----------|
| **콘텐츠 생성 품질** | 생성 초안의 50% 이상이 경미한 편집만으로 게시 가능 |
| **아이디어 유용성** | 월 5개 이상의 실행 가능한 아이디어 산출 |
| **Cross-domain 가치** | 단일 도메인 검색 대비 cross-domain 검색에서 더 높은 rating |
| **환각 방지** | 생성 결과의 모든 주장이 KU source_spans로 추적 가능 |
| **파이프라인 안정성** | 새 책 1권 추가에 수동 개입 10분 이내 |

---

## 16. 리스크와 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| KU 추출 품질 저조 | 전체 시스템 품질 하락 | Phase 1에서 1권으로 프롬프트 최적화. 품질 안정 후 배치 확장 |
| Cross-domain edge 환각 | 잘못된 연결 → 잘못된 아이디어 | `auto` edge는 strength < 0.7이면 `proposed` 상태로 유지, 수동 확인 필요 |
| 87권 처리 시간 | 파이프라인 병목 | 비동기 배치 처리 + 도메인별 우선순위 지정 |
| 생성 콘텐츠의 균일성 | 템플릿 의존으로 다양성 부족 | 템플릿 다변화 + temperature 조정 + 랜덤 KU 조합 |
| 웹 크롤링 노이즈 | 저품질 외부 정보 유입 | 소스 화이트리스트 + LLM 품질 필터링 + 수동 승인 |

---

## 17. v1.0 자산 계승

v1.0의 다음 설계 요소는 v2.0에 계승됨:

| v1.0 요소 | v2.0에서의 위치 | 변경사항 |
|-----------|----------------|---------|
| KU 구조 (claim+evidence) | L1 핵심 모델 | `counterevidence_spans` → `counter_summary`로 간소화 |
| Edge 타입 체계 | L2 | `overlaps_with` 제거, `analogous_to` 추가 |
| Progressive Structuring (M0-M3) | L1 maturity | M3 제거 → M0/M1/M2만 유지 |
| Dispute Axis | L2 하위 기능 | 별도 레이어 → `contradicts` edge 클러스터 |
| Hybrid Search | Search 모듈 | 별도 레이어 → 기능 모듈 |
| PathScore | Search 모듈 | 수식 간소화 (contradiction_density 항 제거) |
| compose API 개념 | L3 Generation | CLI 기반으로 재구현, 아이디어 생성 추가 |
| PR 기반 Evolution | L4 Evolution | PR 모델 → 웹 크롤링 + 반자동 승인 |

---

## 18. 다음 단계

이 문서 승인 후 즉시 Phase 1 실행:

1. **프로젝트 초기화** — `pyproject.toml`, 디렉터리 구조, 의존성 설치
2. **DB 스키마 생성** — SQLite DDL + ChromaDB 컬렉션
3. **PDF 파싱** — 경제학자의 생각법 1권 L0 처리
4. **KU 추출** — 프롬프트 최적화 + L1 처리
5. **검색 + 생성** — 기본 기능 구현 및 가치 검증
