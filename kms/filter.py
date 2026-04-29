"""Score documents in parallel via Claude using v2 filter prompt."""
import json
from concurrent.futures import ThreadPoolExecutor
from json import JSONDecoder
from urllib.parse import urlparse

from kms._llm import client, model
from kms._prompts import load as load_prompt

BODY_LEN = 8000
MAX_WORKERS = 8


def score_and_select(topic: str, docs: list[dict], top_k: int = 5) -> list[dict]:
    """Score each doc per v2 prompt in parallel; return docs with score (=v2 total) sorted desc, capped to top_k.

    `topic` is unused by v2 prompt (kept for call-site compatibility).
    """
    if not docs:
        return []

    sys_prompt = load_prompt("filter")
    workers = min(MAX_WORKERS, len(docs))
    enriched: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for d, result in zip(docs, ex.map(lambda x: _score_one(sys_prompt, x), docs)):
            if result is None:
                continue
            total = int(result.get("total", 0))
            enriched.append({**d, "score": total, "score_detail": result})

    enriched.sort(key=lambda x: x["score"], reverse=True)
    return enriched[:top_k]


def _score_one(sys_prompt: str, d: dict) -> dict | None:
    url = d.get("url", "")
    user_payload = {
        "url": url,
        "domain": urlparse(url).netloc,
        "title": d.get("title", ""),
        "published_at": d.get("published_at"),
        "updated_at": d.get("updated_at"),
        "body": (d.get("text") or "")[:BODY_LEN],
        "db_context": d.get("db_context", []),
    }
    try:
        resp = client().chat.completions.create(
            model=model(),
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )
    except Exception:
        return None
    text = (resp.choices[0].message.content or "").strip()
    try:
        return _parse_json(text)
    except (ValueError, json.JSONDecodeError):
        return None


def _parse_json(text: str) -> dict:
    """Extract the first JSON object from text — tolerates code fences/prefixes/trailing junk."""
    start = text.find("{")
    if start < 0:
        raise ValueError(f"No JSON object found in response: {text!r}")
    obj, _ = JSONDecoder().raw_decode(text[start:])
    return obj
