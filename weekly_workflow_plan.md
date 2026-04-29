# 주간 자동 실행 워크플로우 — 작업 계획

> 매주 월요일 자동 실행으로 주제 리스트 일괄 처리, 신규 소스만 평가, 노션 주제 row를 upsert.

## 결정사항 (확정)

| 항목 | 결정 |
|---|---|
| 노션 DB 구조 | 주제 마스터 = 결과 적재 (단일 DB). 주제 row 1개에 Source/Draft 누적 |
| 주제어 입력 | Notion DB에서 활성 주제 조회 (CLI 인자 X) |
| 신규/중복 판정 | `seen_sources` 테이블 (kms.db). `(topic, url_canonical)` 복합 PK |
| URL 정규화 | utm/fragment 제거 + host lowercase. redirect는 따라가지 않음 |
| 점수 게이트 | `SOURCE_THRESHOLD=3` (노션 Source 적재) / `DRAFT_THRESHOLD=4` (초안 합성). 코드 상수 |
| 초안 트리거 | 마지막 갱신 이후 score≥4 신규 누적이 **3개 이상** 도달했을 때 |
| 초안 갱신 방식 | 페이지 본문 통째로 덮어쓰기 (Notion 자체 버전 히스토리에 의존) |
| 사람 개입 | 없음. 앵글 단계 제거. 노션에서 사후 검토 |
| 동시성 | `ThreadPoolExecutor(max_workers=3)`. 주제별 병렬 |
| 스케줄러 | macOS launchd |
| 실행 리포트 | stdout 로그 (Slack webhook은 후순위) |

## 데이터 모델 변경

### `kms.db` 신규 테이블 2개

```sql
-- 모든 탐색 이력. 평가 통과/탈락 무관 보관. dedupe의 진실 소스.
CREATE TABLE seen_sources (
  topic           TEXT NOT NULL,
  url_canonical   TEXT NOT NULL,
  url_original    TEXT NOT NULL,
  title           TEXT,
  source          TEXT,            -- rss:hbr / serper:en 등
  first_seen_at   TEXT NOT NULL,
  status          TEXT NOT NULL,   -- discovered / extracted / scored / extract_failed
  score           INTEGER,         -- 게이트는 score만 보고 코드 상수로 판정
  notion_page_id  TEXT,            -- score≥3로 노션에 첨부된 경우
  run_id          INTEGER,
  PRIMARY KEY (topic, url_canonical)
);

-- 주제 ↔ 노션 페이지 매핑 + 초안 트리거 카운터
CREATE TABLE topic_pages (
  topic                       TEXT PRIMARY KEY,
  notion_page_id              TEXT NOT NULL,
  last_updated_at             TEXT NOT NULL,
  source_count                INTEGER NOT NULL DEFAULT 0,  -- 누적 score≥3 개수
  draft_eligible_count        INTEGER NOT NULL DEFAULT 0,  -- 누적 score≥4 개수
  last_drafted_source_count   INTEGER NOT NULL DEFAULT 0   -- 마지막 초안 갱신 시점의 draft_eligible_count
);
```

### 초안 트리거 로직

```
delta = topic_pages.draft_eligible_count - topic_pages.last_drafted_source_count
if delta >= 3:
    초안 재생성 → topic_pages.last_drafted_source_count = draft_eligible_count
```

## 파이프라인 변경 (주제 1개 단위)

```
1. RSS + Serper로 후보 수집                                   (변경 없음)
2. URL canonicalize → seen_sources LEFT JOIN
   - 신규 URL만 추출. 모두 status='discovered'로 INSERT
3. 신규 0개? → 이 주제 SKIP (phase 3-7 건너뜀)
4. 신규 후보 본문 추출 → status='extracted' or 'extract_failed'
5. 스코어링 → status='scored', score 기록
6. 게이트 1: score≥3 신규를 노션 페이지의 Source 필드에 append
   - topic_pages.source_count += N3, draft_eligible_count += N4
7. 게이트 2: 마지막 갱신 이후 score≥4 누적이 3개 이상이면 → 초안 재생성
   - 누적 score≥4 URL 전체로 draft.synthesize 호출
   - 페이지 본문 덮어쓰기, last_drafted_source_count 갱신
```

## 파일 변경 맵

```
신규
  kms/url_canonical.py          URL 정규화 단일 함수
  kms/seen_store.py             seen_sources CRUD
  kms/notion_topics.py          주제 마스터 DB에서 활성 주제 조회
  weekly_run.py                 주간 엔트리포인트 (전 주제 순회 + 병렬)
  scripts/launchd/              plist + 설치 스크립트

수정
  kms/db.py                     seen_sources / topic_pages 스키마 추가
  kms/notion_writer.py          upsert (Source append / Draft replace 분리)
  kms/pipeline.py               두 단계 게이트, 조기 스킵, 신규 후보만 평가
  kms/draft.py                  angle 파라미터 제거
  kms/web.py                    curate 분기 제거
  run.py                        cli_select_angle / --auto-angle 제거

삭제
  kms/curate.py
  kms/prompts/curate.txt
```

## PR 순서

| # | 범위 | 검증 |
|---|---|---|
| PR1 | `seen_sources` 테이블 + url_canonical + seen_store 모듈 (미연결) | 단위 테스트 |
| PR2-1 | 앵글 단계 제거 (백엔드) | `python run.py "주제"` end-to-end |
| PR2-2 | 앵글 단계 제거 (프론트엔드) | 대시보드 빌드/실행 |
| PR3 | `topic_pages` + `notion_writer.upsert_page` (Source append / Draft replace 분리) | 같은 주제 두 번 실행해서 row 1개 유지 확인 |
| PR4 | 파이프라인에 두 단계 게이트 + 신규 3개 트리거 + 조기 스킵 | 같은 주제 재실행 시 SKIP, 누적 카운터 정확성 |
| PR5 | Notion 주제 마스터 DB 연동 + `weekly_run.py` | 활성 주제 N개를 직렬로 순회 |
| PR6 | 병렬화 + 실행 리포트 | 3주제 병렬, 한 주제 실패해도 전체 진행 |
| PR7 | launchd plist + 설치 스크립트 | 다음 월요일 자동 실행 검증 |

## 미정 (우선순위 낮음)

- Slack webhook 알림 (초안 갱신 시)
- 주제별 score 분포 리포트 (필터 튜닝용)
- 아웃라인 단계 (workflow.md Phase 4 SEO 분석) — 별도 프로젝트
