"""Propose content angles from selected documents — workflow.md Phase 3 품질 게이트 1."""
import json
import re

from kms._llm import client, model
from kms._prompts import load as load_prompt

PER_DOC_LEN = 4000


def propose_angles(topic: str, docs: list[dict]) -> list[dict]:
    """docs: top-k from filter.py. Returns list of angle dicts."""
    if not docs:
        return []
    sources_block = "\n\n".join(
        f"[자료 {i + 1}] {d['url']}\n{d['text'][:PER_DOC_LEN]}"
        for i, d in enumerate(docs)
    )
    user_msg = f"주제: {topic}\n\n자료들:\n\n{sources_block}"

    resp = client().chat.completions.create(
        model=model(),
        messages=[
            {"role": "system", "content": load_prompt("curate")},
            {"role": "user", "content": user_msg},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    parsed = _parse_json(text)
    return parsed.get("angles", [])


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in response: {text!r}")
    return json.loads(m.group(0))
