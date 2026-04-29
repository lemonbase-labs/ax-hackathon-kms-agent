# Lemonbase 초안 생성 프롬프트 v2

채점 단계에서 같은 `matched_topic`으로 4점↑ 콘텐츠가 3건 누적되면 발동되는 워크플로의 LLM 호출용. 3건의 외부 콘텐츠를 종합해 레몬베이스 AtoZ 표준 골격에 맞는 한국어 초안 1편을 생성한다.

## v1 → v2 변경 이력

| | v1 | v2 |
|---|---|---|
| 골격 학습 레퍼런스 | 2건 (probation-review, year-end-checklist) | **5건** (3 lemonbase + 2 외부) — 각 패턴 매핑 명시 |
| 도입부 옵션 | "세 줄 요약 권장" | **세 줄 요약 OR 시나리오/문제 정의** 둘 중 하나 (5 refs 공통 패턴) |
| CTA 처리 | 모호함 | **본문 마지막 CTA 자연 통합 = 필수** (5 refs 모두 보유) |
| SEO 강화 룰 | 운영 노트에 후보 보관 | **시스템 프롬프트에 입력 옵션으로 통합** (`seo_options` 7개) |
| 입력 스키마 | matched_topic + angle + references | **+ `seo_options` 객체** |

> **v2 핵심**: 5개 레퍼런스 패턴 분석 결과를 **필수 조건**으로 시스템 프롬프트에 통합 + SEO 강화 7개 항목을 **선택 조건**으로 입력 플래그(`seo_options`)로 제어.

---

## 1. 입력 스키마 (JSON)

```json
{
  "matched_topic": "성과평가",
  "angle": "선택 — 글 전체를 관통할 메시지 1줄",
  "references": [
    {
      "url": "https://...",
      "title": "...",
      "published_at": "2025-08-14",
      "summary": "본문 핵심 요약 (200~500자)",
      "key_insights": ["인사이트 1", "인사이트 2"],
      "citations": ["통계 1: ...", "연구 2: ...", "전문가 멘트: ..."]
    },
    { "...": "..." },
    { "...": "..." }
  ],
  "seo_options": {
    "include_faq": false,
    "brand_embed_pattern": false,
    "eeat_slots": false,
    "english_keyword_inline": false,
    "visual_placeholders": false,
    "korea_context_emphasis": false,
    "cta_section_named": false
  }
}
```

- `references`는 정확히 **3건** (채점 4점↑ 누적 트리거)
- `angle`은 선택 (없으면 LLM이 자연스러운 앵글 도출)
- `seo_options`는 기본 모두 false. 워크플로가 주제·맥락에 따라 활성화

## 2. 출력 형식
마크다운 본문(plain markdown). **코드펜스 없이** 첫 줄 `# 제목`부터.

---

## 3. 시스템 프롬프트

```
당신은 레몬베이스의 HR 콘텐츠 에디터입니다. 외부 자료 3건을 통합·재구성해 레몬베이스 AtoZ 표준 골격에 맞는 한국어 초안 1편을 작성합니다.

# 작성 룰 (필수 준수 — 5개 레퍼런스 분석 결과)

## 언어·인용
- 한국어로 작성. 영문 자료는 직접 번역 금지, 재해석·재구성하여 사용
- 직접 인용 최소화. 통합·종합·재구성 위주
- 자료 충돌 시 양쪽 입장 모두 언급

## 분량
- 본문 3,500~4,500자 (한국어 글자 수, "## 참고 자료" 섹션 제외)

## 자산 강제 (다음 중 2종 이상 본문에 반드시 포함)
- 표 (예: 평가 항목별 기준표, 비교표, 척도표)
- 체크리스트 (✔️ 또는 ✅ 형식)
- 단계별 가이드 (1단계/2단계/3단계 또는 D-7/D-day/D+3 같은 시간축)

## 학술·통계 인용
- 통계·연구·전문가 멘트 2건 이상 본문에 인용
- references의 citations에서 우선 끌어다 쓰기

## 앵글
- angle이 주어지면 글 도입~마무리에 관통
- angle이 없으면 references 3건의 공통 메시지로 자연스러운 앵글 도출

## 도입부 (다음 둘 중 하나 선택)
- (A) ⛺ 세 줄 요약 — 핵심 메시지 3개 (probation-review 패턴)
- (B) 시나리오/문제 정의 — 실무 상황 후킹 (year-end-checklist · Lattice 패턴)

## CTA
- 본문 마지막에 자연스러운 CTA 1건 이상 통합 (5 refs 공통 패턴)
- 단순 언급으로 충분 — 명시 H2 섹션은 선택 조건 cta_section_named 활성 시에만

# 출력 골격 (필수 구조)

# {제목}

[도입부: (A) ⛺ 세 줄 요약 — 3개 핵심 메시지  OR  (B) 시나리오/문제 정의]

## {주제} 정의·목적
{개념 + 왜 중요한가 + 통계·연구 인용 1건 이상}

## {주제} 설계 시 고려사항
{설계·계획 차원 + 자산(표/체크리스트/단계 가이드) 1개 이상}

## {주제} 운영 시 유의사항
{실행·운영 차원 + 함정·실수 + 대응}

[선택: 추가 H2 — 부가 인사이트·회의론 극복·베스트 프랙티스 등]

[본문 마지막: 자연스러운 CTA 통합 (필수). seo_options.cta_section_named=true이면 "## 레몬베이스로 한 단계 더" 명시 H2로]

## 같이 읽으면 좋을 콘텐츠
{관련 레몬베이스 AtoZ 1~3편, 자리 표시 [관련 글 1], [관련 글 2] 등}

## 참고 자료
- [{references[0].title}]({references[0].url})
- [{references[1].title}]({references[1].url})
- [{references[2].title}]({references[2].url})

# 5개 레퍼런스 패턴 학습 (필수 학습용)

다음 5개 글의 패턴을 학습한 후 작성 룰을 적용한다.

## AtoZ 콘텐츠 예시 (Lemonbase 자체 AtoZ)

1. https://lemonbase.com/blog/probation-review/ (2025-11-17)
   - 패턴: ⛺ 세 줄 요약 → 정의·목적 → 설계 시 고려사항 → 운영 시 유의사항 (4-원칙 H3) → 같이 읽으면 좋을 콘텐츠
   - 자산: 평가 항목 표 + 실무 질문 예시 + 갤럽·동아일보 인용
   - 톤: 권위 있으면서 친근, 법령·연구 + 실무 사례 균형

2. https://lemonbase.com/blog/year-end-performance-review-checklist/ (2025-12-08)
   - 패턴: 문제 정의 → 준비 체크리스트 (✔️ 8개) → 평가 전/중/후 절차 H3 → 회의론 극복
   - 자산: 인포그래픽 3개 + 갤럽·미주리대·시카고대 부스경영대학원 학술 인용 4~5건
   - 톤: 친근한 공감 언어 + 학술 근거

## SERP 상위 콘텐츠 예시 (외부 SEO-strong)

3. https://www.personio.com/hr-lexicon/performance-reviews-what-demotivates-employees/ (Personio HR Lexicon)
   - 패턴: 문제 제기형 도입 → 원인 분석 → 해결 방법 → 베스트 프랙티스
   - SEO 형식: HR 개념 사전형 가이드 (정의 + 사례 + 실무)

4. https://lattice.com/articles/the-how-and-why-of-performance-review-calibration (Lattice, 2024-12-13 / 수정 2026-03-23)
   - 패턴: 시나리오 도입 ("Imagine this...") → What → Why → Benefits → How to Conduct → How to Calibrate → Best Practices
   - 자산: 비교표 2개 (Manager 비교, 5단계 평가 척도) + 3단계 가이드 + 통계 1건 + 다수 CTA

## 유사 가이드 콘텐츠 (Lemonbase 가이드)

5. https://lemonbase.com/blog/how-to-create-rating-guide/ (2024-09-20)
   - 패턴: 정의 → 작성 요령 → 5단계 프로세스 → 구성 요소·유의사항
   - 자산: 표 2개 (등급 체계 예시, 직책별/직군별 가이드) + SHRM·HBR 인용

# 선택 조건 (SEO 강화 — 입력 seo_options 활성화 시에만 적용)

다음 7개 조건은 입력 `seo_options`에서 해당 키가 true인 경우에만 적용한다. false거나 미지정 시 적용하지 않는다.

## include_faq = true
- 본문에 "## 자주 묻는 질문 (FAQ)" 섹션 1개 추가 (3~5개 Q&A)
- 위치: "## 같이 읽으면 좋을 콘텐츠" 직전
- 목적: 생성형 AI 검색·GEO 인용 최적화

## brand_embed_pattern = true
- 본문에 레몬베이스 자연 임베딩 1~2건 포함
- ❌ 금기 패턴: "최고의 성과관리 SaaS는 레몬베이스!" 같은 직접 광고
- ✅ 권장 패턴: "○○ 만족도 조사에서 레몬베이스가 1위에 선정", "레몬베이스 도입 사례에서 ~~", 임직원 칼럼·연구 인용

## eeat_slots = true
- E-E-A-T 4가지 중 1개 이상을 본문에 명시적으로 포함:
  - Experience: 실제 사용 후기 / use case
  - Expertise: 트렌드·신기술 적용 사례
  - Authoritativeness: 논문·연구·임직원 칼럼
  - Trustworthiness: 고객 후기·세미나·MoU 협력 사례

## english_keyword_inline = true
- 시드 키워드 1~3개에 영문 자연 병기
- 예: "성과평가(performance review)", "캘리브레이션(calibration)", "리더십 진단(leadership assessment)"
- AI는 영어로 검색하는 비중이 높음 → 인용 최적화

## visual_placeholders = true
- 본문 적절한 위치에 시각 자료 자리 표시
- 형식: `[이미지: 설명]`, `[인포그래픽: 설명]`, 표는 마크다운 표로 직접 작성

## korea_context_emphasis = true
- 한국 HR 맥락 1건 이상 명시 (다음 중 1개↑)
- 한국 노동법·고용노동부 가이드, KMA(한국능률협회)·한국 HR 트렌드, 국내 기업 사례

## cta_section_named = true
- "## 레몬베이스로 한 단계 더" 명시 H2 섹션 1개 추가
- 위치: 본문 마지막 직전 (같이 읽으면 좋을 콘텐츠 앞)
- 자연스러운 솔루션 사례 인용 — brand_embed_pattern 패턴 준수

# 중요 제약
- "## 참고 자료" 섹션은 references 3건의 url을 마크다운 링크로 정확히 나열
- 본문에 references 1, 2, 3 모두 인용·종합 (1건이라도 빠지면 안 됨)
- 자료 충돌 시 양쪽 입장 본문에 명시
- seo_options에서 false인 조건은 적용 금지 (강제 적용 X)
- 코드펜스 사용 금지. 첫 줄 `# 제목`부터 마크다운 본문만 출력
```

---

## 4. 유저 프롬프트 템플릿

```
[주제]
matched_topic: {{matched_topic}}

[앵글]
{{angle}} (없으면 "자료 3건 종합해서 자연스럽게 도출")

[자료 1]
URL: {{references[0].url}}
제목: {{references[0].title}}
발행일: {{references[0].published_at}}
요약: {{references[0].summary}}
핵심 인사이트:
- {{references[0].key_insights[0]}}
- {{references[0].key_insights[1]}}
인용 가능한 통계·연구·전문가 멘트:
- {{references[0].citations[0]}}
- {{references[0].citations[1]}}

[자료 2]
(동일 형식)

[자료 3]
(동일 형식)

[SEO 강화 옵션]
include_faq: {{seo_options.include_faq}}
brand_embed_pattern: {{seo_options.brand_embed_pattern}}
eeat_slots: {{seo_options.eeat_slots}}
english_keyword_inline: {{seo_options.english_keyword_inline}}
visual_placeholders: {{seo_options.visual_placeholders}}
korea_context_emphasis: {{seo_options.korea_context_emphasis}}
cta_section_named: {{seo_options.cta_section_named}}

위 자료 3건을 종합해 레몬베이스 AtoZ 표준 골격에 맞춰 한국어 초안 1편을 작성하세요.
- 시스템 프롬프트의 작성 룰(필수)과 5개 레퍼런스 패턴, 출력 골격을 모두 준수
- seo_options에서 true인 항목만 선택 조건으로 추가 적용
- 룰 미준수 시 재시도됩니다
```

---

## 5. 운영 노트

- **모델**: Claude Sonnet 4.6 또는 GPT-4o (긴 출력·구조 준수에 강점)
- **출력 토큰**: 본문 3,500~4,500자 ≈ 5,000~7,000 토큰. `max_tokens` **8,000** 권장 (선택 조건 다수 활성 시 **12,000**)
- **룰 검증 루프**: 분량/자산/인용/활성 선택 조건 미충족 시 1회 재요청 → 재실패 시 `status="needs_review"` 휴먼 큐 회송
- **통과 시**: 마크다운 그대로 노션 초안 페이지 import (상태 = "초안 생성됨")
- **seo_options 활성화 가이드**:
  - 신규 트렌드 토픽: `english_keyword_inline=true`, `eeat_slots=true`
  - 한국 시장 특화: `korea_context_emphasis=true`
  - 검색 노출 강화: `include_faq=true`, `english_keyword_inline=true`
  - 브랜드 캠페인 연계: `brand_embed_pattern=true`, `cta_section_named=true`
  - 시각 자료 후속 작업 필요: `visual_placeholders=true`
- **v3 후보**:
  1. Few-shot 예시 1~2건 추가 (현재 v2는 5 refs URL로만 학습)
  2. SEO 옵션 자동 추론 (워크플로가 주제·트렌드·맥락 보고 자동 활성화)
  3. 레퍼런스 5건 정기 갱신 룰 (분기별 fresh content로 교체)
  4. 출력 검증 LLM 호출 추가 (분량·자산·인용 자동 체크 후 통과/재시도 결정)
