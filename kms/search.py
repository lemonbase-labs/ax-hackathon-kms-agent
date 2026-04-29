"""Google Programmable Search Engine (CSE) — language-aware web search."""
import os

import requests

CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def search(query: str, lang: str, num: int = 10) -> list[dict]:
    """Run a CSE query restricted to lang ('en' or 'ko').

    Returns list of {url, title, source, matched}. Empty on any failure
    (network, quota, missing config) — caller proceeds with other sources.
    """
    if not query.strip():
        return []
    params = {
        "key": os.environ["GOOGLE_CSE_KEY"],
        "cx": os.environ["GOOGLE_CSE_ID"],
        "q": query,
        "num": min(max(num, 1), 10),
        "lr": f"lang_{lang}",
    }
    try:
        r = requests.get(CSE_ENDPOINT, params=params, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  ! CSE failed (q={query!r}, lang={lang}): {e}")
        return []
    items = r.json().get("items", [])
    return [
        {
            "url": item["link"],
            "title": item.get("title", ""),
            "source": f"cse:{lang}",
            "matched": [query],
        }
        for item in items
    ]
