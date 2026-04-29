"""Synthesize an integrated Korean draft from selected documents."""
from kms._llm import client, model
from kms._prompts import load as load_prompt

# 한 자료당 본문 컨텍스트 상한 (토큰 폭증 방지)
PER_DOC_LEN = 4000


def synthesize(topic: str, docs: list[dict]) -> str:
    """docs: filter-passed docs. Returns markdown draft string."""
    sources_block = "\n\n".join(
        f"[자료 {i + 1}] {d['url']}\n{d['text'][:PER_DOC_LEN]}"
        for i, d in enumerate(docs)
    )
    user_msg = f"주제: {topic}\n\n자료들:\n\n{sources_block}"

    resp = client().chat.completions.create(
        model=model(),
        messages=[
            {"role": "system", "content": load_prompt("draft")},
            {"role": "user", "content": user_msg},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
