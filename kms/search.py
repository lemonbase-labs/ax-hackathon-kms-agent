"""Serper API (serper.dev) — language-aware Google SERP search."""
import os

import requests

ENDPOINT = "https://google.serper.dev/search"


def search(query: str, lang: str, num: int = 10) -> list[dict]:
    """Run a Serper query restricted to lang ('en' or 'ko').

    Returns list of {url, title, source, matched}. Empty on any failure
    (network, quota, missing config) — caller proceeds with other sources.
    """
    if not query.strip():
        return []
    gl, hl = ("kr", "ko") if lang == "ko" else ("us", "en")
    body = {
        "q": query,
        "gl": gl,
        "hl": hl,
        "num": min(max(num, 1), 10),
    }
    try:
        r = requests.post(
            ENDPOINT,
            headers={
                "X-API-KEY": os.environ["SERPER_API_KEY"],
                "Content-Type": "application/json",
            },
            json=body,
            timeout=15,
        )
        r.raise_for_status()
    except Exception as e:
        print(f"  ! Serper failed (q={query!r}, lang={lang}): {e}")
        return []
    items = r.json().get("organic", [])
    return [
        {
            "url": item["link"],
            "title": item.get("title", ""),
            "source": f"serper:{lang}",
            "matched": [query],
        }
        for item in items
    ]
