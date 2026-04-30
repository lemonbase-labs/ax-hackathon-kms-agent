# KMS Agent — Architecture & Operations

이 문서는 **현재 구현된** 동작을 기준으로 한 wiki다. 과거 계획/페이즈 문서는 모두 정리됐고, 이 문서가 단일 출처(SoT).

---

## 1. 한 줄 요약

주제어를 받아 **여러 소스(RSS·웹 검색·섹션 페이지)에서 글을 모아 점수를 매기고**, 같은 주제의 노션 페이지 한 개에 **소스 목록을 누적**하다가 **고품질 자료가 일정 수 누적되면 한국어 초안을 합성해서 페이지 본문을 갱신**한다. 모든 파이프라인은 동일하며 단발 CLI / 주간 일괄 / 웹 대시보드 트리거의 차이만 있다.

---

## 2. 컴포넌트 지도

```
┌────────────────────────────────────────────────────────────────┐
│                         트리거 (3가지)                          │
│  run.py "주제"        weekly_run.py        대시보드 POST /runs  │
└─────────────┬───────────────┬───────────────────┬──────────────┘
              │               │                   │
              ▼               ▼                   ▼
       ┌───────────────────────────────────────────────────┐
       │           kms.pipeline.run_pipeline(topic)        │
       │  Phase 1  keyword_extract  (LLM)                  │
       │  Phase 2  RSS + Serper(EN/KO) + 섹션 시드 → 신규만 │
       │  Phase 3  본문 추출 (requests → Playwright fb)    │
       │  Phase 4  병렬 LLM 스코어링 (관련성+신뢰도)       │
       │  Phase 5  초안 합성 (게이트 통과 시만)            │
       │  Phase 6  Notion upsert + 카운터 갱신             │
       └─────┬───────────────────────┬─────────────────────┘
             │                       │
             ▼                       ▼
    ┌──────────────┐         ┌──────────────────────┐
    │ kms.db       │         │  Notion DB (외부)    │
    │ (sqlite)     │         │  주제 = 페이지 1개   │
    │  - runs      │         │  Source 누적 / Body  │
    │  - run_phases│         │  덮어쓰기 / Status   │
    │  - seen_     │         └──────────────────────┘
    │    sources   │
    │  - topic_    │         ┌──────────────────────┐
    │    pages     │         │  Slack webhook (선택)│
    └──────────────┘         └──────────────────────┘
```

---

## 3. 파이프라인 상세 (`kms/pipeline.py`)

| Phase | 모듈 | 입력 | 출력 | 비고 |
|---|---|---|---|---|
| 1 | `keyword_extract` | topic | `{en:[...], ko:[...]}` | LLM. `config.py:BROAD_KEYWORDS`에서 토픽/카테고리 매칭되는 항목이 있으면 검색 시드는 그쪽 우선. |
| 2 | `sources.fetch_candidates` + `search.search_many` | EN/KO 키워드 | 후보 URL `[{url,title,source,...}]` | RSS(whitelist) + Serper EN×3페이지 + Serper KO×3페이지 + 섹션 페이지 시드. URL canonicalize 후 `seen_sources`에 없는 것만 통과. **신규 0개면 즉시 SKIP**. |
| 3 | `extract.extract` | URL | `{url, text, title, ...}` | trafilatura → 실패 시 Playwright stealth 폴백 → 그래도 실패 시 og 메타 폴백. 결과는 `seen_sources.status`에 `extracted` / `extract_failed`로 기록. |
| 4 | `filter.score_and_select` | docs | docs + `score`(2~20) | ThreadPool 8병렬. 프롬프트 v2(`prompts/filter.md`): 관련성(1-10) + 신뢰도(1-10) = total. 스코어를 `seen_sources.score`에 저장. |
| 5 | `draft.synthesize` | 누적 score≥`draft_threshold` 자료 전체 | 한국어 초안 마크다운 | **게이트 통과 시에만 호출**. 매 회 신규 자료뿐 아니라 과거 누적 적격 자료도 다시 가져와 통째로 합성. |
| 6 | `notion_writer.write_draft` | topic, sources, draft | (page_url, action) | Upsert. 첫 호출은 페이지 생성, 이후는 Source/Keywords union + 본문 통째 교체. `topic_pages.notion_page_id` 매핑 갱신. |

### 게이트 로직 (`pipeline.decide_action`)

세 임계값(`kms/config.json`):
- `source_threshold` (기본 3): 이 점수 이상이면 **노션 Source 필드에 누적**.
- `draft_threshold` (기본 4): 이 점수 이상이면 **초안 합성 후보**(드래프트 풀에 들어감).
- `draft_batch` (기본 3): 마지막 초안 갱신 이후 새로 누적된 적격(score≥draft_threshold) 자료 수가 이 값 이상이면 **초안 재합성 트리거**.

```
delta = topic_pages.draft_eligible_count - topic_pages.last_drafted_source_count
if delta >= draft_batch:   초안 재생성 + last_drafted_source_count = draft_eligible_count
```

응답 status:
- `skipped` — 신규 후보 없음 (Phase 2에서 컷)
- `error` — 본문 추출 0건 등 치명 실패
- `no_change` — 신규 있지만 source/draft 게이트 모두 미통과
- `sources_only` — Source 필드만 갱신 (초안 미트리거)
- `drafted` — 초안까지 갱신

---

## 4. 데이터 모델

### 4.1 `kms.db` (sqlite, 자동 생성)

```sql
runs                  실행 1건 = 1 row. id, topic, status, current_phase, notion_url, error,
                      started_at, finished_at
run_phases            실행 × phase 단위. payload_json에 단계 결과 스냅샷
run_step_inputs       단계별 입력 스냅샷 (대시보드 "rerun step" 기능 의존)
seen_sources          (topic, url_canonical) PK. 모든 발견 URL — 평가 통과/탈락 무관 보관.
                      필드: url_original, title, source, first_seen_at, status, score,
                            notion_page_id, run_id
topic_pages           topic PK ↔ Notion page_id 매핑 + 카운터 3종
                      (source_count, draft_eligible_count, last_drafted_source_count)
```

`status` 전이: `discovered` → (`extracted` | `extract_failed`) → `scored`.

### 4.2 Notion DB 스키마 (사용자가 노션 UI에서 미리 생성)

| 필드 | 타입 | 용도 |
|---|---|---|
| 주제 | title | 페이지 제목 (= 파이프라인 topic) |
| 키워드 | multi_select | en/ko 키워드 union 누적 |
| Source | rich_text | URL bullet list 누적 (2000자 한도, 넘치면 최신 tail 유지) |
| Status | status | Draft / In Review / Approved / Rejected. **Approved/Rejected는 weekly에서 비활성으로 처리** |
| (페이지 본문) | blocks | 초안 마크다운. 갱신 시 기존 블록 모두 삭제 후 새로 append |

> **Notion API 주의 (2025 Data Sources 모델)**: `pages.create`의 parent는 `database_id`가 아닌 `data_source_id`다. 코드는 `databases.retrieve` 후 `data_sources[0].id`를 추출해 사용. (이 동작은 `notion_writer.py`, `notion_topics.py`에서 동일.)

### 4.3 URL 정규화 (`url_canonical.canonicalize`)

- scheme http→https, lowercase
- host lowercase, leading `www.` 제거
- 쿼리에서 `utm_*`, `gclid`, `fbclid`, `mc_cid`, `mc_eid` 드롭
- fragment 드롭
- path는 보존 (case-sensitive, trailing `/`도 보존)
- redirect는 따라가지 않음

복합 PK `(topic, url_canonical)`로 같은 주제 내 dedupe만 보장. 다른 주제는 같은 URL을 독립적으로 추적.

---

## 5. 실행 모드

### 5.1 단일 토픽 CLI (`run.py`)

```sh
uv run python run.py "성과관리" [--top-k 5]
```

`run_pipeline` 1회 + slack(설정된 경우) 알림 + stdout 결과 라인.

### 5.2 주간 일괄 (`weekly_run.py`)

1. `notion_topics.fetch_active_topics` — Notion 마스터 DB에서 Status가 Approved/Rejected가 **아닌** 모든 row.
2. `db.upsert_topic_page`로 매핑을 직렬 사전 등록 (sqlite 단일 라이터 가정).
3. `ThreadPoolExecutor(max_workers=3)`로 토픽별 병렬 실행. 한 토픽 실패해도 다른 토픽은 진행.
4. 종료 후 통합 요약을 stdout + Slack(설정된 경우)으로.

### 5.3 대시보드 (`kms/web.py` + `web/`)

- 백엔드: FastAPI on `127.0.0.1:8000`. 정적 빌드(`web/dist`)가 있으면 같은 포트에서 서빙. dev 모드는 Vite `:5173` + CORS.
- 단일 동시성: 모듈 레벨 `_run_lock` + DB의 `runs.status='running'` 이중 가드. 동시 실행 시 409.
- 주요 엔드포인트:
  - `POST /api/runs {topic, top_k}` — 백그라운드 스레드로 파이프라인 시작
  - `GET /api/runs?limit=` / `GET /api/runs/active` / `GET /api/runs/{id}` / `DELETE /api/runs/{id}`
  - `POST /api/runs/{id}/cancel` — running을 강제 종료 표시 (in-flight 작업은 자연 종료)
  - `POST /api/runs/{id}/steps/{step}/rerun` — `keyword_extract|filter|draft` 한 단계만 재실행 (저장된 input snapshot 사용)
  - `GET/PUT /api/prompts/{name}` — `kms/prompts/*.md` CRUD
  - `GET/PUT /api/feeds` — `kms/feeds.txt` CRUD
  - `GET/PUT /api/config` — `kms/config.json` 임계값 CRUD

### 5.4 launchd 자동화 (`scripts/launchd/`)

`install.sh` 실행 시:
- `~/Library/LaunchAgents/com.kms-agent.weekly.plist` 생성 (매주 월 09:00, `RunAtLoad=false`)
- `__REPO__` 자리표시자를 절대경로로 치환
- 로그: `~/Library/Logs/kms-agent/weekly.{log,err}`
- 실행 entry: `$REPO/.venv/bin/python $REPO/weekly_run.py`

`uninstall.sh`로 제거.

---

## 6. 외부 의존성

| 외부 | 용도 | 환경변수 | 실패 시 동작 |
|---|---|---|---|
| bifrost (사내 OpenAI 호환 게이트웨이) | LLM (keyword/filter/draft) | `BIFROST_URL`, `BIFROST_KEY`, `CAS_MODEL` | 필터는 doc별 swallow → null 결과. keyword/draft는 raise. |
| Serper (`google.serper.dev`) | 검색 | `SERPER_API_KEY` | 쿼리별 swallow → 빈 리스트. |
| Notion | 결과 저장 + 활성 토픽 마스터 DB | `NOTION_TOKEN`, `NOTION_DB_ID` | raise. weekly_run은 토픽별 swallow. |
| Slack incoming webhook | 알림 | `SLACK_WEBHOOK_URL` (선택) | unset이면 silent skip. HTTP 실패도 stderr만 찍고 swallow. |
| Playwright + stealth | requests 차단 시 본문 추출 폴백 | `PLAYWRIGHT_STORAGE_STATE`(선택, 로그인 쿠키) | 실패 시 og:meta 폴백 또는 None 반환. |

---

## 7. 설정·튜닝 포인트

운영 중 자주 손대게 되는 것:

| 항목 | 위치 | 어디서 편집 |
|---|---|---|
| 점수 임계값 / 초안 트리거 배치 | `kms/config.json` | 대시보드 Settings 또는 직접 편집 |
| RSS 피드 화이트리스트 | `kms/feeds.txt` | 대시보드 Feeds 또는 직접 편집 |
| 필터/초안/키워드 프롬프트 | `kms/prompts/*.md` | 대시보드 Prompts 또는 직접 편집 |
| 카테고리별 검색 키워드 사전 | `config.py:KEYWORDS` | 코드 직접 편집 |
| 섹션 페이지 시드 | `kms/sources.py:SECTION_URLS` | 코드 직접 편집 |
| 주간 실행 시간 | `scripts/launchd/com.kms-agent.weekly.plist.template` | 템플릿 편집 후 `install.sh` 재실행 |
| 동시 토픽 워커 수 | `weekly_run.py:MAX_WORKERS` | 코드 (기본 3) |

---

## 8. 운영 시나리오

### "같은 주제를 여러 번 실행해도 중복이 안 쌓이는지?"

`seen_sources (topic, url_canonical)` PK로 dedupe. Phase 2에서 이미 본 URL은 후보에서 제외되며, 신규 0건이면 phase 3-7 전체가 SKIP된다. 노션 페이지의 Source 필드도 `_union_preserving_order`로 union 처리.

### "초안이 매번 새로 쓰여지는지?"

아니다. `draft_eligible_count - last_drafted_source_count >= draft_batch`(기본 3)일 때만 합성·교체. 그 사이 실행은 Source 필드만 union으로 늘어난다. 페이지 본문은 갱신 시 **이전 블록 전부 archive 후 새 블록 append** — 노션 자체 버전 히스토리에 의존.

### "활성 토픽이란?"

Notion 마스터 DB(= 결과 DB와 동일)의 row 중 Status가 `Approved`/`Rejected`가 아닌 것. 새 주제를 늘리려면 Notion에서 row 추가만 하면 된다.

### "특정 단계만 다시 돌리고 싶을 때"

대시보드에서 `keyword_extract` / `filter` / `draft` 세 단계는 저장된 input으로 단독 재실행 가능. 단, **그 기능이 들어온 이후 시작된 run에만 snapshot이 있다.**

### "한 번에 한 run만?"

웹 트리거는 모듈 lock + DB `runs.status='running'` 검사. CLI/launchd는 별도 프로세스이므로 lock이 안 걸린다 — 동시에 두 개를 돌리고 싶지 않다면 각자 호출 시점에 주의해야 한다.

---

## 9. 테스트

`tests/`는 단위 위주. LLM/HTTP는 모킹.

```sh
uv run --with pytest python -m pytest -q
```

커버 범위:
- 게이트 로직 (`test_pipeline_gates`)
- URL 정규화 (`test_url_canonical`)
- seen_store 멱등성 (`test_seen_store`)
- 노션 writer upsert (`test_notion_writer`)
- 활성 토픽 조회 (`test_notion_topics`)
- 필터 파싱 (`test_filter`)
- 설정/피드 로더 (`test_config`, `test_feeds`)
- weekly 병렬 동작 (`test_weekly_run`)
- slack 메시지 (`test_slack`)

---

## 10. 알려진 한계 / 비범위

- **저작권**: 본문 추출·합성 시 모든 소스 URL을 인용. 직접 발췌 최소화는 프롬프트 책임.
- **로그인 필요 매체**: Playwright `storage_state`(쿠키)가 있어야 통과. 없으면 og:meta 폴백 또는 실패.
- **redirect 추적**: URL canonicalize는 HEAD 요청 없음. 다른 URL이지만 같은 글이면 중복 통과 가능.
- **Notion Source 필드 2000자 한도**: 넘치면 최신 항목 우선으로 tail 유지. 실제 누적은 `topic_pages.source_count`로 추적되므로 카운터 자체는 정확.
- **자동 발행**: Ghost 등 외부 발행은 범위 밖. Notion `Status=Approved` 이후는 사람이 수동 발행.
