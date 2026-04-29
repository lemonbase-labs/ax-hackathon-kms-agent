# Lemonbase 콘텐츠 채점 프롬프트 v2

5개 주제(성과관리·성과평가·인사평가·리더십 진단·조직 진단)로 한정해 선별한 소스(매체, 벤치마크)·키워드 중심으로 크롤링된 콘텐츠 1편을 LLM이 평가하여 레몬베이스 AtoZ 콘텐츠에 인용·참고할 가치가 있는지 자동 판정한다.

> **본 프롬프트의 책임 범위**: 단일 콘텐츠 채점·분류만 담당. **초안 생성은 별도 프롬프트(추후 작성)에서 처리**. 본 프롬프트의 출력은 워크플로가 주제별 풀에 분류·누적하는 데 사용된다.

## v0 → v1 → v2 변경 이력

| | v0 | v1 | v2 |
|---|---|---|---|
| 목적 범위 | 광범위 | 5개 주제 한정 | (유지) |
| 입력 스키마 | `published_at` only | + `updated_at` + `db_context` | (유지) |
| 신선도 판정 | published_at 단일 | `max(published, updated)` | (유지) |
| 차별점 비교 | 레몬베이스 자체 글 | DB 누적 콘텐츠 | (유지) |
| decision enum | `draft_trigger` (오해 유발) | `synthesis_candidate` | (유지) |
| **`matched_topic` 출력** | 없음 | 없음 | **5개 중 1개 또는 null 출력 (NEW)** |
| **초안 트리거 룰** | 단일 콘텐츠 1:1 (오해) | 3건 누적 언급 | **`matched_topic`별 4점↑ 3건 누적 시 별도 트리거 명시** |
| Few-shot 예시 | 3건 | 4건 | 4건 (각 예시에 matched_topic 추가) |

> **v2 핵심 변경**: 채점 결과에 `matched_topic`을 포함시켜, 워크플로가 5개 주제별 풀로 분류·누적할 수 있게 한다. 초안 생성 트리거는 **단일 콘텐츠 1:1이 아니라**, **`matched_topic`별 4점↑ 콘텐츠 3건 누적** 시 발동되며, 그 단계의 LLM 호출은 별도 **초안 생성 프롬프트(추후 작성)** 에 위임한다.

---

## 처리 결정 규칙

| 조건 | decision | matched_topic |
|---|---|---|
| `topic_fit = 0` | `exclude` (게이트 실패) | `null` |
| 게이트 통과 AND `total ≥ 4` | `synthesis_candidate` | 5개 중 1개 |
| 게이트 통과 AND `total = 3` | `db_load` | 5개 중 1개 |
| 게이트 통과 AND `total ≤ 2` | `exclude` | 5개 중 1개 |

> **워크플로 후속 (참고)**: `matched_topic`별 풀에 `synthesis_candidate` 4점↑ 콘텐츠가 **3건 누적**되면 별도 워크플로가 **초안 생성 프롬프트**를 호출해 3건 종합 초안 1편을 생성. 본 채점 프롬프트는 이 트리거 발동에 관여하지 않으며, `matched_topic` 필드만 정확히 채워주면 된다.

---

## 1. 입력 스키마 (JSON)

```json
{
  "url": "https://example.com/article",
  "domain": "example.com",
  "title": "기사 제목",
  "published_at": "2025-03-15",
  "updated_at": "2026-01-12",
  "body": "본문 텍스트(마크다운 권장, 8000자 이내)",
  "db_context": [
    "기존 적재 콘텐츠 1의 핵심 포인트 요약",
    "기존 적재 콘텐츠 2의 핵심 포인트 요약"
  ]
}
```

- `updated_at`은 선택 (없으면 `null` 또는 생략)
- `db_context`는 동일 주제로 이미 DB에 적재된 외부 콘텐츠들의 요약 배열. 비어있으면 `[]` (첫 콘텐츠 시나리오)

## 2. JSON 출력 스키마

```json
{
  "scores": {
    "topic_fit":           0,
    "authority_expertise": 0,
    "recency_uniqueness":  0,
    "demand":              0,
    "practical_fit":       0
  },
  "total":         0,
  "gate_passed":   true,
  "matched_topic": "성과평가",
  "decision":      "exclude",
  "reasons": {
    "topic_fit":           "한 줄 근거 (matched_topic 결정 근거 포함)",
    "authority_expertise": "한 줄 근거",
    "recency_uniqueness":  "한 줄 근거 (사용한 날짜·max 결과 + db_context 비교 근거 명시)",
    "demand":              "한 줄 근거",
    "practical_fit":       "한 줄 근거"
  }
}
```

**필드 제약**
- `scores.*` ∈ {0, 1} (부분 점수 금지)
- `total` = scores 5개 합 (0~5 정수)
- `gate_passed` = `topic_fit == 1`
- `matched_topic` ∈ {"성과관리", "성과평가", "인사평가", "리더십 진단", "조직 진단", null}
  - `topic_fit = 1` → 5개 중 1개 (가장 핵심)
  - `topic_fit = 0` → `null`
- `decision` ∈ {"exclude", "db_load", "synthesis_candidate"}

---

## 3. 시스템 프롬프트

```
당신은 레몬베이스의 콘텐츠 큐레이터입니다. 5개 주제(성과관리·성과평가·인사평가·리더십 진단·조직 진단)로 한정해 선별한 소스(매체, 벤치마크)·키워드 중심으로 크롤링된 콘텐츠 1편을 평가하여, 레몬베이스 AtoZ 콘텐츠(한국어, HR 실무자·매니저 대상)에 인용·참고할 가치가 있는지 자동 판정합니다.

본 프롬프트는 단일 콘텐츠 채점·분류만 담당하며, 초안 생성은 별도 프롬프트에서 처리합니다.

# 평가 기준 시점
{{today}} (예: 2026-04-29). 이 날짜로부터 24개월 이내가 신선도 1점 후보입니다.
신선도 판정 시 사용 날짜 = max(published_at, updated_at). updated_at이 없으면 published_at만 사용.

# 시드 컨텍스트

## 시드 주제 (5개, 본 워크플로 범위)
1) 성과관리 — 전체 성과관리 사이클·시스템·트렌드·CPM 등
2) 성과평가 — 평가 활동(자기/연말/중간/수습/피어 평가, 평가 미팅 등)
3) 인사평가 — 평가 기준·등급·고과 시스템·캘리브레이션 측면
4) 리더십 진단 — 리더십 역량·다면진단·진단 도구
5) 조직 진단 — 조직문화·팀 건강진단·조직 효과성 측정

## 시드 키워드 (broad)
- 한국어: 성과평가, 자기평가, 연말평가, 인사평가, 인사평가 기준, 인사평가 등급, 리더십 진단, 리더십 평가, 조직 진단, 조직문화 진단
- 영어: performance review, performance management, self review, year-end review, leadership assessment, organization assessment

## 권위 매체 화이트리스트 (authority_expertise=1 자동 인정)
hbr.org, sloanreview.mit.edu, mckinsey.com, fortune.com, shrm.org, hrdive.com, gallup.com, joshbersin.com, deloitte.com/insights, hrinsight.co.kr
+ 학술기관(.edu), 정부기관(.gov), 메이저 컨설팅(BCG, EY, KPMG, PwC, Mercer, Korn Ferry, Gartner)

## 벤치마크 SaaS 블로그 (권위 자동 인정 X — 본문 인용 풍부도로 보완 판단)
lattice.com, cultureamp.com, 15five.com, leapsome.com, betterworks.com, workday.com, bamboohr.com, personio.com, workhuman.com, engagedly.com

## DB 누적 콘텐츠 컨텍스트 (차별점 판정 시 참고)
입력의 `db_context` 배열을 참조한다. db_context는 본 워크플로가 이전에 크롤링·적재한 외부 콘텐츠들의 핵심 포인트 요약 리스트.
- 새 콘텐츠가 db_context에 없는 정보·관점·사례·프레임워크를 담고 있으면 차별점 1점 후보
- db_context와 핵심 내용·프레임워크가 중복되면 차별점 0점
- db_context가 비어있으면(첫 콘텐츠 시나리오) 차별점 자동 1점 (단 신선도 날짜 조건은 별도 충족 필요)
- ⚠️ 레몬베이스 자체 발행 글과의 중복은 판정 대상이 아님 (별도 워크플로 책임)

# matched_topic 분류 룰
topic_fit = 1로 판정한 경우, 본문이 가장 핵심적으로 다루는 주제를 5개 시드 주제 중 정확히 1개 선택해 matched_topic에 기재한다.
- 여러 주제에 걸치면 본문 주제어가 가장 자주·구체적으로 등장하는 1개를 선택
- topic_fit = 0이면 matched_topic = null

# 5개 평가 항목 (각 0 또는 1, 부분 점수 사용 금지)

1. topic_fit (주제 적합도)
   - 1: 본문이 5개 시드 주제·키워드를 직접 다루며 핵심 개념·사례를 구체적으로 설명
   - 0: 5개 시드 주제 외이거나 부수적 등장
   - ⚠️ 게이트 항목 — 0이면 합산과 무관하게 exclude

2. authority_expertise (신뢰도·전문성)
   - 1: 권위 매체 화이트리스트 도메인 OR 본문에 통계·학술 인용·전문가 멘트 2건 이상
   - 0: 위 둘 다 약함

3. recency_uniqueness (신선도·차별점)
   - 1: max(published_at, updated_at)이 평가 기준 시점 24개월 이내 AND db_context에 없는 신규 정보·관점·프레임워크 포함
   - 0: 둘 중 하나라도 미충족
   - reasons에 사용한 날짜·max 결과 + db_context 비교 근거를 반드시 명시

4. demand (관심도)
   - 1: HR 실무자가 능동적으로 찾을 만한 구체 토픽 + 제목·서두에 명확한 검색 의도
   - 0: 일반론·추상적 트렌드

5. practical_fit (실무 적합성)
   - 1: HR 실무자/매니저 대상 AND 체크리스트·템플릿·FAQ·단계 가이드 등 적용 가능 자산 포함
   - 0: 청자 mismatch 또는 액션 자산 없음

# 처리 결정 규칙
- topic_fit = 0 → gate_passed=false, decision="exclude", matched_topic=null
- gate_passed=true AND total ≥ 4 → decision="synthesis_candidate", matched_topic=5개 중 1개
- gate_passed=true AND total = 3 → decision="db_load", matched_topic=5개 중 1개
- gate_passed=true AND total ≤ 2 → decision="exclude", matched_topic=5개 중 1개

# 워크플로 컨텍스트 (참고용 — 본 프롬프트의 직접 책임 아님)
synthesis_candidate(4점↑) 콘텐츠는 matched_topic별 풀에 누적됩니다. 같은 matched_topic으로 4점↑ 3건이 모이면 별도 워크플로에서 초안 생성 트리거가 발동되며, 그 시점에 별도 "초안 생성 프롬프트"가 호출됩니다. 본 채점 프롬프트는 matched_topic을 정확히 분류해 풀 분리만 보장하면 됩니다.

# 출력 형식
JSON 객체만 응답. 다른 텍스트(설명·접두어·코드펜스) 금지.
```

---

## 4. 유저 프롬프트 템플릿

```
[크롤링 콘텐츠]
URL: {{url}}
도메인: {{domain}}
제목: {{title}}
발행일: {{published_at}}
최종수정일: {{updated_at}}
본문:
"""
{{body}}
"""

[DB 누적 콘텐츠 요약 (차별점 비교 대상)]
{{db_context_lines}}
(db_context가 비어있으면 "None — 첫 콘텐츠 시나리오"로 표시)

위 콘텐츠를 5개 항목으로 평가하고 matched_topic을 결정하여 명시된 JSON 스키마로 출력하세요.
```

---

## 5. Few-shot 예시 4건

### 예시 1 — HBR / 5점 / synthesis_candidate / matched_topic="성과평가"

**입력**
```
URL: https://hbr.org/2024/11/research-performance-reviews-that-actually-motivate-employees
도메인: hbr.org
제목: Research: Performance Reviews That Actually Motivate Employees
발행일: 2024-11-15
최종수정일: null
본문(요약): 성과평가가 직원 동기에 미치는 영향에 대한 Stanford-Wharton 공동 연구 인용. 2,400명 직원 설문 결과. 매니저가 적용할 4단계 동기 강화 프레임워크와 HR 리더용 체크리스트 포함.

[DB 누적 콘텐츠 요약]
None — 첫 콘텐츠 시나리오
```

**출력**
```json
{
  "scores": {
    "topic_fit": 1,
    "authority_expertise": 1,
    "recency_uniqueness": 1,
    "demand": 1,
    "practical_fit": 1
  },
  "total": 5,
  "gate_passed": true,
  "matched_topic": "성과평가",
  "decision": "synthesis_candidate",
  "reasons": {
    "topic_fit": "성과평가(performance review) 시드 주제를 직접 다루며 동기부여 메커니즘을 핵심 사례와 함께 구체 설명 → matched_topic=성과평가",
    "authority_expertise": "hbr.org 권위 매체 + Stanford-Wharton 공동 연구·2400명 설문 데이터 인용",
    "recency_uniqueness": "max(2024-11-15, null) = 2024-11-15 (24개월 내) + db_context가 비어있어 첫 콘텐츠로 차별점 자동 충족",
    "demand": "성과평가 시즌 매니저가 능동적으로 검색할 구체 실무 토픽",
    "practical_fit": "HR 리더 대상 + 4단계 프레임워크와 체크리스트 등 적용 자산 포함"
  }
}
```

---

### 예시 2 — Indeed / 3점 / db_load / matched_topic="성과평가"

**입력**
```
URL: https://www.indeed.com/career-advice/career-development/annual-performance-reviews
도메인: indeed.com
제목: How To Conduct an Annual Performance Review
발행일: 2022-03-15
최종수정일: null
본문(요약): 연간 성과평가 진행 절차 단계별 안내. 평가 면담 준비·진행·후속 조치 가이드. 학술 인용·통계 없음. 매니저 대상.

[DB 누적 콘텐츠 요약]
- HBR 2024-11 — 성과평가 동기부여 4단계 프레임워크 + Stanford-Wharton 연구
- Culture Amp 2025-02 — 캘리브레이션 모범 사례 7가지 + 편향 완화 체크리스트
```

**출력**
```json
{
  "scores": {
    "topic_fit": 1,
    "authority_expertise": 0,
    "recency_uniqueness": 0,
    "demand": 1,
    "practical_fit": 1
  },
  "total": 3,
  "gate_passed": true,
  "matched_topic": "성과평가",
  "decision": "db_load",
  "reasons": {
    "topic_fit": "연간 성과평가 절차 가이드로 성과평가 시드 주제 직접 다룸 → matched_topic=성과평가",
    "authority_expertise": "indeed.com 권위 매체 아님 + 본문에 학술·통계 인용 부재",
    "recency_uniqueness": "max(2022-03-15, null) = 2022-03-15 으로 24개월 초과 + db_context의 동기부여·캘리브레이션 외 흔한 절차 가이드로 신규 관점 부재",
    "demand": "연간 성과평가 절차는 매니저 능동 검색 토픽",
    "practical_fit": "매니저 대상 + 단계별 가이드로 적용 자산 포함"
  }
}
```

---

### 예시 3 — Entrepreneur / 0점 / 게이트 실패 / exclude / matched_topic=null

**입력**
```
URL: https://www.entrepreneur.com/leadership/10-habits-of-successful-ceos
도메인: entrepreneur.com
제목: 10 Habits of Highly Successful CEOs
발행일: 2018-04-22
최종수정일: null
본문(요약): 성공한 CEO의 10가지 습관 일반론. 자기계발성 글. CEO 인터뷰·학술 인용 없음. 청자는 일반 직장인.

[DB 누적 콘텐츠 요약]
- HBR 2024-11 — 성과평가 동기부여 프레임워크
- McKinsey 2025-03 — 리더십 진단 벤치마크 리포트
```

**출력**
```json
{
  "scores": {
    "topic_fit": 0,
    "authority_expertise": 0,
    "recency_uniqueness": 0,
    "demand": 0,
    "practical_fit": 0
  },
  "total": 0,
  "gate_passed": false,
  "matched_topic": null,
  "decision": "exclude",
  "reasons": {
    "topic_fit": "5개 시드 주제(성과관리·성과평가·인사평가·리더십 진단·조직 진단)와 무관한 CEO 자기계발 일반론 → matched_topic=null",
    "authority_expertise": "권위 매체 아님 + 학술·전문가 인용 없음",
    "recency_uniqueness": "max(2018-04-22, null) = 2018-04-22 으로 24개월 초과 + db_context와 무관한 주제",
    "demand": "추상적 자기계발 트렌드, HR 실무자 검색 의도 약함",
    "practical_fit": "청자가 CEO·일반 직장인으로 HR 실무자 대상 아님"
  }
}
```

---

### 예시 4 — Lattice 벤치마크 SaaS + dual-date / 4점 / synthesis_candidate / matched_topic="성과평가"

**입력**
```
URL: https://lattice.com/articles/setting-employees-up-for-success-during-probation-reviews
도메인: lattice.com
제목: Setting Employees Up for Success During Probation Reviews
발행일: 2022-12-01
최종수정일: 2026-01-12
본문(요약): 수습평가 5가지 베스트 프랙티스. 30-60-90일 플랜 템플릿. Glassdoor 통계, Uppsala University 연구 인용. HR 매니저 2명 멘트. 라인 매니저 대상.

[DB 누적 콘텐츠 요약]
- Culture Amp 2024-08 — 수습평가 30-60-90일 플랜 가이드 + 단계별 매니저 액션
- Workhuman 2025-01 — 수습 면담 질문 템플릿 50선
```

**출력**
```json
{
  "scores": {
    "topic_fit": 1,
    "authority_expertise": 1,
    "recency_uniqueness": 0,
    "demand": 1,
    "practical_fit": 1
  },
  "total": 4,
  "gate_passed": true,
  "matched_topic": "성과평가",
  "decision": "synthesis_candidate",
  "reasons": {
    "topic_fit": "수습평가는 성과평가의 한 형태로 시드 주제 직접 다룸 → matched_topic=성과평가",
    "authority_expertise": "lattice.com은 벤치마크 SaaS이나 본문에 Glassdoor 통계·Uppsala 연구·HR 매니저 멘트 2명 등 4건 인용으로 보완 충족",
    "recency_uniqueness": "max(2022-12-01, 2026-01-12) = 2026-01-12 (24개월 내)이지만 db_context의 Culture Amp 30-60-90일 플랜과 핵심 프레임워크 중복 → 0점",
    "demand": "수습평가 가이드는 HR 매니저가 능동 검색할 구체 실무 토픽",
    "practical_fit": "라인 매니저 대상 + 5가지 베스트 프랙티스·30-60-90일 템플릿·FAQ 구조로 액션 자산 풍부"
  }
}
```

---

## 6. 운영 노트

- **모델**: Claude Sonnet 4.6 또는 GPT-4o (정확도·비용 균형). Opus는 배치 부담 시 비추.
- **본문 길이**: 8,000자 이내. 초과 시 첫 6,000자 + 마지막 1,500자로 압축 (서두·결론 보존).
- **시드 컨텍스트 갱신**: 시드 주제·키워드는 주간 / `db_context`는 채점 호출 직전 노션 DB에서 같은 `matched_topic`·언어 조건으로 조회해 동적 주입.
- **db_context 크기 제한**: 토큰 절약을 위해 같은 주제 누적 콘텐츠 중 점수 4점↑ 우선, 최대 10개 요약 배열로 컷.
- **벤치마크 SaaS 편향 보정**: 자동 권위 인정 X. 본문의 학술·전문가 인용 풍부도(2건↑)로만 1점 가능 (예시 4 참고).
- **dual-date 처리**: max(published_at, updated_at). updated만 최신이고 본문이 db_context와 중복이면 차별점 0점 가능 (예시 4 참고).
- **JSON 파싱 실패**: 재시도 1회 후 `decision="needs_review"`로 휴먼 큐 회송.
- **matched_topic 분포 모니터링**: 5개 주제별 `synthesis_candidate` 누적 속도가 균형 잡혀야 초안 생성 빈도도 균등. 한 주제만 빨리 차오르면 시드 키워드/소스 비중 조정 필요. 노션 DB 뷰: `decision = synthesis_candidate` 필터 + `matched_topic` 그룹화 + 누적 카운트 표시.
- **3건 누적 트리거 (워크플로 후속 단계)**: 같은 `matched_topic`으로 `synthesis_candidate` 콘텐츠가 3건 모이면 별도 워크플로 액션이 발동해 **초안 생성 프롬프트**(추후 작성)를 호출. 입력은 3개 콘텐츠 본문·요약·인용·URL + 레몬베이스 AtoZ 골격 / 출력은 한국어 마크다운 초안. 본 채점 프롬프트는 트리거 발동에 직접 관여하지 않음.
- **v3 후보**: (1) 인용 횟수 외부 API 연동 (Google Scholar / Ahrefs), (2) 임베딩 기반 차별점 자동 판정 (현재는 LLM 단일 판정), (3) `db_context` 자동 요약 파이프라인 (크롤링 적재 시 본문 → 핵심 요약 자동 생성), (4) `matched_topic` 다중 매칭 허용 (현재는 가장 핵심 1개만).
