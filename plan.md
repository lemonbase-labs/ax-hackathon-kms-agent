# KMS Agent — 콘텐츠 제작·발행 워크플로 자동화

> AX 해커톤 1차 산출물. 로컬 실행, Notion 연동, Claude 활용.

## 1. 해결하려는 문제

- **소스 분산**: #bot-hr-article, #knowledge 슬랙 채널, HR Dive·HBR 뉴스레터 등 여러 매체에 정보가 흩어져 있어 주기적으로 챙기지 않으면 누락됨.
- **수동 가공**: 정보 → 지식 → 콘텐츠 변환이 모두 수동.
- **KMS 부재**: HR 도메인은 지식 니즈가 상시 있으나 KMS 운영이 지속되지 못함.

## 2. 페르소나별 고충

- **콘텐츠 발행 담당자**: HR 트렌드를 놓침. 주제어를 매번 검색해야 글감을 얻음.
- **내부 크루**: 양질의 글을 큐레이션 받고 싶음.

## 3. 목표 (1차 범위)

키워드 입력 → 검색·선별 → 비교·통합 → 레몬베이스 양식의 초안을 Notion에 저장.
**슬랙 공유, Ghost 자동 배포는 후순위.**

## 4. 확정된 결정사항

| 항목 | 결정 |
|---|---|
| 결과물 기대치 | **(c) 일단 동작만 — 분량/구조는 나중** |
| 키워드 입력 방식 | **(a) CLI 인자로 매번 입력** (`python run.py "수습 평가"`) |
| 콘텐츠 양식 | **AtoZ 1종**만 1차 타깃 (뉴스레터 양식은 제외) |
| 언어/런타임 | Python 3.10+ |
| AI | Claude (사내 **bifrost** 게이트웨이 경유 — Anthropic API 직접 호출 X) |
| 본문 추출 | trafilatura |
| 검색 (능동형) | **Serper API** (CSE 발급 막힘. 무료 2,500/월, Google 결과 그대로) |
| 수집 (수동형) | **RSS** — 우선순위 매체 직접 구독 + Google Alerts의 RSS 출력 활용 (Gmail 폴링 X) |
| Notion | notion-client (공식 Python SDK) |
| 에이전트 형태 | 1차는 순차 파이프라인 스크립트 → 필요 시 Claude Agent SDK로 승급 |

## 5. 명시적 가정

- 저작권: 모든 소스 URL을 인용으로 명시. 본문은 재해석/통합 위주, 직접 발췌 최소화.
- 실행 환경: 로컬 CLI. 데몬/스케줄링 없음.
- 비용: 1회 실행당 Claude 호출 5-10회 수준 가정 (필터링 N회 + 드래프트 1-2회).
- 슬랙 채널 메시지 수집은 1차 범위 밖.

## 6. Phase별 계획

### Phase 0 — 통합 라인 검증 (반나절)
**목표**: 3개 API 통합이 한 번에 살아있는지 확인. 품질 무시.
- `fetch_url.py`: 하드코딩 URL 1개 → trafilatura 본문 추출 → Claude로 한 줄 요약 → Notion DB row 생성
- 검증: Notion에 row가 보이고 / Title에 요약 / Sources에 URL이 있는지 육안 확인
- **산출물**: 동작하는 단일 스크립트 + `.env.example`

### Phase 1 — 단일 키워드 end-to-end (1-2일)
**목표**: 한 주제로 처음부터 끝까지 굴려보고 결과물을 눈으로 보기. **가장 중요한 단계.**
- CLI: `python run.py "수습 평가"`
- 흐름:
  1. **시드 URL 파일** (`seeds/<keyword>.txt`, 수동 입력 5-10개) + **Serper 검색** 결과 합쳐 후보 URL 풀 형성
  2. 본문 추출 (trafilatura)
  3. Claude로 관련성·신빙성 스코어링 → 상위 3-5개 선별
  4. 선별된 소스를 Claude에 한 번에 전달 → 비교·통합 드래프트 생성
  5. Notion DB에 row 생성 (드래프트 + 소스 링크 + Status=Draft)
- 검증: 결과물이 "AtoZ 비슷한가?" 사람 눈으로 평가. 안 비슷해도 OK — Phase 2에서 보정.
- **시드 파일을 두는 이유**: Serper로 신규 결과는 잡히지만 키워드별 "알려진 명문"(과거 HBR 등)을 안정적으로 포함시키려면 수동 시드가 가장 확실. 데모 신뢰도 확보용.

### Phase 2 — 스타일 정합성 (1일)
**목표**: 결과물을 레몬베이스 톤·구조에 맞춤.
- 기존 AtoZ 글 5-10개 수집 → 구조 추출 (도입 → 정의 → 본문 섹션 → FAQ → 마무리 등)
- 시스템 프롬프트에 구조 가이드 + few-shot 1-2개 첨부
- 검증: 5번 돌려서 출력 구조가 일관되게 나오는지

### Phase 3 — 우선순위 소스 (1일)
**목표**: 신뢰도 높은 매체의 결과를 우선 활용.
- 우선순위 도메인 리스트 정의 (HBR, HR Dive, SHRM, Gallup 등)
- Serper 검색 결과 스코어링에 도메인 가중치 +α
- **RSS 수집 트랙** (능동형 검색의 보완재):
  - 우선순위 매체 직접 RSS 구독
  - Google Alerts의 RSS 출력(Alerts 생성 시 "Deliver to: RSS feed" 선택)을 동일 코드 패스로 흡수
  - 누적된 후보 URL은 Phase 1과 동일한 후반 파이프라인(필터→드래프트→Notion) 재사용

### Phase 4 — 휴먼 검토 루프 (반나절)
**목표**: 드래프트 검토를 슬랙·Notion으로 운영화.
- Notion 드래프트 생성 시 Slack webhook으로 링크 + 핵심 요약 발송
- Status 필드 활용: Draft / In Review / Approved / Rejected

### Phase 5 — 자동 배포 (해커톤 시간 남으면)
- n8n으로 Notion `Status=Approved` → Ghost 발행
- 또는 Python에서 Ghost API 직접 호출

## 7. Notion DB 스키마 (`Test DB`, Phase 0 검증 완료)

| 필드 | 타입 | 용도 |
|---|---|---|
| 주제 | title | 콘텐츠 제목 (Phase 0에선 요약 텍스트) |
| 키워드 | multi_select | 입력 키워드 (태그 형태) |
| Source | rich_text | 참고 URL 리스트 (줄바꿈 구분) |
| Draft | (페이지 본문) | 초안 본문 — page body에 저장 |
| Status | status | Draft / In Review / Approved / Rejected |
| 생성일 | created_time | 자동 |

> **Notion API 주의 (2025 Data Sources 모델)**: `pages.create`의 parent는 `database_id`가 아닌 `data_source_id`를 사용해야 한다. 코드에서는 `databases.retrieve`로 DB를 가져와 `data_sources[0].id`를 추출 후 전달한다.

## 8. Phase 0 사전 결정사항 (확정)

- **AI 호출**: 사내 bifrost 키 사용. Anthropic 직접 호출 X.
- **Notion 토큰**: 사용자 보유. Integration 토큰 + DB ID를 `.env`로 주입.
- **Notion DB 생성**: 사용자가 Notion UI에서 직접 생성 → integration 연결 → DB ID 전달 (방식 a). 코드는 DB ID에서 data_source_id를 동적 조회.
- **Phase 0 테스트 URL**:
  - https://www.indeed.com/career-advice/career-development/performance-review-phrases
  - https://www.library.hbs.edu/working-knowledge/want-better-performance-reviews-change-this-one-word

## 8-1. bifrost API 스펙 (lemonbase-tech/cas 분석)

- **호환성**: OpenAI 호환. `POST /v1/chat/completions`
- **base_url**: `$BIFROST_URL/v1` (OpenAI Python SDK에 그대로 주입)
- **인증**: `Authorization: Bearer $BIFROST_KEY` 가정 (CAS 자체는 무인증, bifrost 상위 레이어가 처리. 401시 헤더 형식 재확인 필요)
- **CAS_MODEL 후보**: `claude-code` (기본) / `claude-code-opus` / `claude-code-sonnet` / `claude-code-haiku`
- **요청 예시**:
  ```python
  from openai import OpenAI
  client = OpenAI(base_url=f"{BIFROST_URL}/v1", api_key=BIFROST_KEY)
  resp = client.chat.completions.create(
      model=CAS_MODEL,
      messages=[{"role": "user", "content": "..."}]
  )
  text = resp.choices[0].message.content
  ```
- **스트리밍**: 지원하나 Phase 0에선 불필요

## 8-2. 확정된 환경변수

```
BIFROST_URL=...
BIFROST_KEY=...
CAS_MODEL=claude-code-sonnet  # Phase 0 권장. 비용/속도 균형
NOTION_TOKEN=...
NOTION_DB_ID=350e2421b7c08028950ad0f7f0957a5c
```

## 9. Phase 1-2 진입 전 미해결 질문

- 우선순위 소스 도메인 리스트
- HBR 등 유료 콘텐츠 접근 가능 여부
- AtoZ 양식 학습용 글 URL 5-10개 (또는 lemonbase.com/blog 직접 크롤링 OK 여부)
- 별도 톤앤매너 가이드 문서 존재 여부

## 10. 디렉토리 구조 (예정)

```
kms-agent/
├── plan.md                # 이 문서
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py                 # Phase 1+ CLI 엔트리
├── fetch_url.py           # Phase 0 단일 스크립트
├── seeds/                 # Phase 1: 키워드별 시드 URL (수동 입력)
│   └── <keyword>.txt
└── kms/                   # Phase 1부터 모듈화
    ├── search.py          # Serper 호출
    ├── extract.py         # trafilatura 본문 추출
    ├── filter.py          # Claude 스코어링·선별
    ├── draft.py           # Claude 비교·통합 드래프트
    ├── notion_writer.py
    └── collectors/        # Phase 3: RSS 수집 (우선순위 매체 + Alerts RSS)
        └── rss.py
```
