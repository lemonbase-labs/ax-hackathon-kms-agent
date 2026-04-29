"""Synthesize an integrated Korean draft from selected documents."""
from kms._llm import client, model

SYSTEM_PROMPT = """\
당신은 레몬베이스 HR 콘텐츠 에디터다. 주어진 주제어와 영문 자료들을 바탕으로
한국어 콘텐츠 초안을 작성한다.

작성 규칙:
- 한국어로 작성. 영문 자료는 재해석/번역하여 사용.
- 직접 인용 최소화. 통합·재구성 위주.
- markdown 형식. 구조: # 제목 → ## 도입 → ## 핵심 개념 → ## 실무 적용 → ## 마무리
- 각 자료의 핵심 인사이트를 비교하거나 통합. 자료가 충돌하면 양쪽 입장 모두 언급.
- 마지막에 "## 참고 자료" 섹션에 URL 목록을 markdown 링크로 나열.
- 분량: 1500-2500자 한국어 본문 (참고 자료 제외).
"""

# 한 자료당 본문 컨텍스트 상한 (토큰 폭증 방지)
PER_DOC_LEN = 4000


def synthesize(topic: str, docs: list[dict]) -> str:
    """docs: top-k from filter.py. Returns markdown draft string."""
    sources_block = "\n\n".join(
        f"[자료 {i + 1}] {d['url']}\n{d['text'][:PER_DOC_LEN]}"
        for i, d in enumerate(docs)
    )
    user_msg = f"주제: {topic}\n\n자료들:\n\n{sources_block}"

    resp = client().chat.completions.create(
        model=model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
