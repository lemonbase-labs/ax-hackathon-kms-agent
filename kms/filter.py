"""Score documents by relevance/credibility and select top-k via Claude."""
import json
import re

from kms._llm import client, model

SYSTEM_PROMPT = """\
주어진 주제어와 문서 후보들을 평가한다. 각 문서에 대해:
- relevance: 1-10 (주제와의 관련도)
- credibility: 1-10 (출처 신뢰도, 본문 깊이)
- reason: 한 줄 평가

규칙:
- 출력은 JSON만. 다른 설명/코드블록 금지.
- 형식: {"scores": [{"index": 0, "relevance": 8, "credibility": 7, "reason": "..."}, ...]}
- index는 입력 배열의 0-based 인덱스
"""

# 본문은 너무 길면 토큰 폭증 → 첫 1500자만 평가에 사용
SNIPPET_LEN = 1500


def score_and_select(topic: str, docs: list[dict], top_k: int = 5) -> list[dict]:
    """docs: list of {url, text, ...}. Returns top_k docs with added 'score' field."""
    if not docs:
        return []

    user_payload = {
        "topic": topic,
        "documents": [
            {"index": i, "url": d["url"], "snippet": d["text"][:SNIPPET_LEN]}
            for i, d in enumerate(docs)
        ],
    }
    resp = client().chat.completions.create(
        model=model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    parsed = _parse_json(text)
    scores = parsed.get("scores", [])

    # 인덱스로 docs에 score 합치기
    by_index = {s["index"]: s for s in scores if "index" in s}
    enriched = []
    for i, d in enumerate(docs):
        s = by_index.get(i)
        if not s:
            continue
        total = int(s.get("relevance", 0)) + int(s.get("credibility", 0))
        enriched.append({**d, "score": total, "score_detail": s})

    enriched.sort(key=lambda x: x["score"], reverse=True)
    return enriched[:top_k]


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in response: {text!r}")
    return json.loads(m.group(0))
