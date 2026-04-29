"""Topic → en/ko keyword expansion via Claude."""
import json
import re

from kms._llm import client, model

SYSTEM_PROMPT = """\
당신은 HR/조직 도메인 리서치 어시스턴트다. 주어진 한국어 주제어에 대해
관련 검색용 키워드를 영문 3-5개, 한국어 3-5개 추출한다.

규칙:
- 주제의 동의어, 하위 개념, 인접 개념을 포함
- 너무 일반적인 단어(예: "회사", "직원")는 제외
- 영문은 lowercase, 따옴표 없는 단어/구
- 출력은 JSON만. 다른 설명 금지.
- 형식: {"en": ["...", ...], "ko": ["...", ...]}
"""


def extract_keywords(topic: str) -> dict[str, list[str]]:
    resp = client().chat.completions.create(
        model=model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": topic},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    data = _parse_json(text)
    return {
        "en": [s.strip().lower() for s in data.get("en", []) if s.strip()],
        "ko": [s.strip() for s in data.get("ko", []) if s.strip()],
    }


def _parse_json(text: str) -> dict:
    # 모델이 ```json ... ``` 로 감싸는 경우 대비
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in response: {text!r}")
    return json.loads(m.group(0))
