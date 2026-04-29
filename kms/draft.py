"""Synthesize an integrated Korean draft from selected documents."""
from kms._llm import client, model
from kms._prompts import load as load_prompt

# 한 자료당 본문 컨텍스트 상한 (토큰 폭증 방지)
PER_DOC_LEN = 4000


def synthesize(topic: str, docs: list[dict], angle: dict | None = None) -> str:
    """docs: top-k from filter.py. angle: optional curate.propose_angles() item.
    Returns markdown draft string."""
    sources_block = "\n\n".join(
        f"[자료 {i + 1}] {d['url']}\n{d['text'][:PER_DOC_LEN]}"
        for i, d in enumerate(docs)
    )
    angle_block = ""
    if angle:
        angle_block = (
            "\n\n선택된 앵글 (글 전체에 관통시킬 것):\n"
            f"- 제목: {angle.get('title', '')}\n"
            f"- 인사이트: {angle.get('insight', '')}\n"
            f"- 차별점: {angle.get('differentiator', '')}\n"
            f"- 한국 HR 적용: {angle.get('korea_context', '')}"
        )
    user_msg = f"주제: {topic}{angle_block}\n\n자료들:\n\n{sources_block}"

    resp = client().chat.completions.create(
        model=model(),
        messages=[
            {"role": "system", "content": load_prompt("draft")},
            {"role": "user", "content": user_msg},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
