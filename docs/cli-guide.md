# CLI 사용 가이드

> `ks` — Knowledge System CLI

## 사전 요구사항

- Python 3.12+
- `.env` 파일에 `OPENAI_API_KEY` 설정
- 의존성 설치: `pip install -e .` 또는 `pip install typer rich pyyaml python-dotenv openai chromadb`

## 실행 방법

```bash
# 프로젝트 루트에서 실행
python -m src.cli <command> [options]
```

---

## 명령어

### 1. `ingest` — 데이터 수집 + KU 추출

JSON 파일을 파싱하여 raw_spans → KU 추출 → 임베딩 → Vault 마크다운 생성까지 전체 파이프라인을 실행합니다.

```bash
# 전체 파이프라인 실행
python -m src.cli ingest data/raw/55bbe4_경제학자의_생각법_text.json

# 미리보기 (DB 저장 없이)
python -m src.cli ingest data/raw/55bbe4_경제학자의_생각법_text.json --dry-run

# 책 ID 지정
python -m src.cli ingest input.json --book-id econ-thinking-002
```

**옵션:**
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--book-id` | 책 ID | config.yaml 첫 번째 책 |
| `--dry-run` | DB 저장 없이 미리보기 | False |
| `-v`, `--verbose` | 상세 로그 | False |

**출력:**
- `data/knowledge.db` — raw_spans + knowledge_units 테이블
- `data/chroma/` — 벡터 임베딩
- `vault/domains/{도메인}/` — KU 마크다운 파일

---

### 2. `search` — 벡터 검색

자연어 쿼리로 유사한 KU를 검색합니다.

```bash
# 기본 검색
python -m src.cli search "매몰비용"

# 결과 수 제한
python -m src.cli search "인플레이션" --top-k 5

# 도메인 필터
python -m src.cli search "경쟁의 효과" --domain 경제

# 임계값 조정 (낮을수록 엄격)
python -m src.cli search "기회비용" --threshold 0.5
```

**옵션:**
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `-k`, `--top-k` | 최대 결과 수 | 10 |
| `-t`, `--threshold` | cosine distance 임계값 | 0.6 |
| `-d`, `--domain` | 도메인 필터 | 전체 |

**출력 예시:**
```
┌──────────────────────── 검색 결과 ─────────────────────────┐
│ #  │ 유사도  │ 신뢰도 │ 도메인 │ KU ID              │ Claim │
├────┼─────────┼────────┼────────┼─────────────────────┼───────┤
│ 1  │  60.4%  │   0.5  │ 경제   │ ku-econ-001-0042    │ ...   │
│ 2  │  58.1%  │   0.5  │ 경제   │ ku-econ-001-0156    │ ...   │
└────┴─────────┴────────┴────────┴─────────────────────┴───────┘
총 2건
```

---

### 3. `generate content` — 콘텐츠 생성

토픽 기반으로 KU를 검색하고, LLM으로 콘텐츠를 생성합니다.

```bash
# 블로그 포스트 (기본)
python -m src.cli generate content --topic "매몰비용" --format blog

# 요약
python -m src.cli generate content --topic "인플레이션" --format summary

# 소셜미디어 스레드
python -m src.cli generate content --topic "경쟁의 효과" --format thread

# DB 저장 없이 생성
python -m src.cli generate content --topic "기회비용" --format blog --no-save
```

**옵션:**
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--topic` | 생성 주제 (필수) | — |
| `-f`, `--format` | 출력 형식: blog, summary, thread | blog |
| `-k`, `--top-k` | 참조할 KU 수 | 5 |
| `--no-save` | generations 테이블에 저장하지 않음 | False |

**포맷별 특징:**
- **blog**: 1,500~3,000자 블로그 글 (서론-본론-결론)
- **summary**: 300~500자 핵심 요약 (3~5개 포인트)
- **thread**: 5~10개 항목 소셜미디어 스레드

---

### 4. `stats` — 통계 확인

DB와 ChromaDB 현황을 확인합니다.

```bash
python -m src.cli stats
```

**출력 예시:**
```
┌─── Knowledge System 통계 ───┐
│ 항목             │     건수  │
├──────────────────┼──────────┤
│ Books            │        1 │
│ Raw Spans        │      341 │
│ Knowledge Units  │      997 │
│ Edges            │        0 │
│ Generations      │        2 │
└──────────────────┴──────────┘

┌─── 도메인 분포 ───┐
│ 도메인  │  KU 수  │
├─────────┼─────────┤
│ 경제    │     997 │
└─────────┴─────────┘

ChromaDB 임베딩: 997건
```

---

## 출력 파일 구조

```
vault/
└── domains/
    └── 경제/
        ├── ku-econ-001-0001.md
        ├── ku-econ-001-0002.md
        └── ... (KU별 마크다운)
```

각 마크다운 파일 구조:
```yaml
---
id: ku-econ-001-0042
book: econ-thinking-001
domain: 경제
subdomain: 행동경제학
confidence: 0.5
maturity: M0
tags: ["매몰비용", "의사결정"]
created: 2026-02-27
---

## Claim
핵심 주장 내용...

## Evidence
근거 요약...

## Counter
반론/한계...

## Connections
(Phase 3에서 자동 생성)
```

---

## 트러블슈팅

### API 키 오류
```
openai.AuthenticationError: ...
```
→ `.env` 파일에 `OPENAI_API_KEY=sk-...` 확인

### ChromaDB 오류
```
chromadb.errors.NoIndexException: ...
```
→ `data/chroma/` 디렉터리 존재 여부 확인. `ingest` 명령으로 임베딩 생성 필요.

### 검색 결과 0건
→ threshold 값을 높여보세요: `--threshold 0.8`
→ 도메인 필터 제거: `--domain` 옵션 없이 실행

### 인코딩 오류 (Windows)
→ 환경변수 설정: `set PYTHONUTF8=1`
