"""Topic → en/ko keyword expansion via Claude."""
import json
import re

from kms._llm import client, model
from kms._prompts import load as load_prompt


def extract_keywords(topic: str) -> dict[str, list[str]]:
    resp = client().chat.completions.create(
        model=model(),
        messages=[
            {"role": "system", "content": load_prompt("keyword_extract")},
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
