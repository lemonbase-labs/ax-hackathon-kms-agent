# KMS Agent

HR 콘텐츠 제작·발행 워크플로 자동화. 주제어 → RSS·Serper 검색 → 본문 추출 → 스코어링 → Notion 페이지 upsert(+초안 합성).

로컬 실행. Notion이 결과 저장소이자 주제 마스터 DB. Claude(사내 bifrost 게이트웨이) 사용.

---

## 빠른 시작 (비개발자용 — mac)

[처음 한 번만 — 1단계] 터미널에서 uv 설치:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치 후 터미널을 한 번 닫았다 다시 엽니다.

[처음 한 번만 — 2단계] 별도 전달받은 `.env` 파일을 이 폴더(README.md가 있는 폴더)에 그대로 둡니다. 파일 이름은 반드시 `.env`(앞에 점) 그대로여야 합니다.

[매번 실행할 때]

```sh
./start.sh
```

(또는 `start.sh`를 `start.command`로 이름 변경 시 Finder에서 더블클릭 실행 가능)

잠시 후 브라우저에 `http://127.0.0.1:8000` 화면이 자동으로 열립니다. 종료는 터미널에서 `Ctrl+C`.

문제가 생기면 터미널 출력을 그대로 공유해 주세요.

---

## 개발자용

### 요구사항

- Python ≥ 3.10, [uv](https://docs.astral.sh/uv/)
- Node.js LTS (대시보드 빌드)
- Notion integration 토큰 + DB ID
- bifrost(LLM) 키, Serper 키

### 설치

```sh
uv sync
(cd web && npm install)
```

### 환경변수 (`.env`)

```
BIFROST_URL=...
BIFROST_KEY=...
CAS_MODEL=claude-code-sonnet
NOTION_TOKEN=...
NOTION_DB_ID=...
SERPER_API_KEY=...
SLACK_WEBHOOK_URL=...                 # optional
PLAYWRIGHT_STORAGE_STATE=...          # optional, 로그인 쿠키 storage
```

### 실행 모드

| 용도 | 명령 |
|---|---|
| 단일 토픽 CLI | `uv run python run.py "성과관리"` |
| 주간 일괄 (Notion 활성 토픽 전부) | `uv run python weekly_run.py` |
| 대시보드 (빌드 + 정적 서빙) | `./start.sh` → http://127.0.0.1:8000 |
| 대시보드 (Vite HMR 개발) | `./start.sh --dev` → http://127.0.0.1:5173 |
| launchd 매주 월 09:00 자동화 | `scripts/launchd/install.sh` |

### 테스트

```sh
uv run --with pytest python -m pytest -q
```

---

## 디렉토리 구조

```
kms-agent/
├── run.py                  단일 토픽 CLI 엔트리
├── weekly_run.py           Notion 활성 토픽 전체 순회 (병렬)
├── config.py               KEYWORDS / BROAD_KEYWORDS 사전
├── start.sh                대시보드 부팅 스크립트
├── kms.db                  SQLite (런 이력 + seen_sources + topic_pages)
├── kms/                    파이프라인 패키지
│   ├── pipeline.py         6단계 파이프라인 + 게이팅
│   ├── web.py              FastAPI 대시보드 백엔드
│   ├── keyword_extract.py  주제 → en/ko 키워드 (LLM)
│   ├── search.py           Serper API
│   ├── sources.py          RSS + 섹션페이지 시드
│   ├── extract.py          requests/Playwright stealth 본문 추출
│   ├── filter.py           병렬 LLM 스코어링 (관련성+신뢰도)
│   ├── draft.py            소스 통합 → 한국어 초안
│   ├── notion_writer.py    upsert (Source append / Body replace)
│   ├── notion_topics.py    활성 토픽 조회 (weekly용)
│   ├── seen_store.py       (topic, url_canonical) 중복 추적
│   ├── url_canonical.py    URL 정규화
│   ├── tracker.py          phase context manager
│   ├── slack.py            webhook 알림
│   ├── db.py               sqlite 스키마 + CRUD
│   ├── _llm.py / _config.py / _feeds.py / _prompts.py   런타임 로더
│   ├── config.json         스코어 임계값 (대시보드에서 편집)
│   ├── feeds.txt           RSS 화이트리스트
│   └── prompts/            keyword_extract / filter / draft 프롬프트
├── web/                    React + Vite 대시보드
├── scripts/launchd/        매주 월요일 자동 실행 plist
├── tests/                  pytest 단위 테스트
└── docs/architecture.md    설계·데이터 모델·운영 wiki
```

자세한 동작 원리는 [docs/architecture.md](docs/architecture.md).
