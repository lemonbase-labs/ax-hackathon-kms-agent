"""Serper API (serper.dev) — language-aware Google SERP search."""
import os

import requests

ENDPOINT = "https://google.serper.dev/search"


def search(query: str, lang: str, page: int = 1) -> list[dict]:
    """Run a single Serper query for one page (10 results).

    Returns list of {url, title, source, matched}. Empty on any failure.
    """
    if not query.strip():
        return []
    gl, hl = ("kr", "ko") if lang == "ko" else ("us", "en")
    body = {"q": query, "gl": gl, "hl": hl, "num": 10, "page": page}
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
        print(f"  ! Serper failed (q={query!r}, lang={lang}, page={page}): {e}")
        return []
    return [
        {
            "url": item["link"],
            "title": item.get("title", ""),
            "source": f"serper:{lang}",
            "matched": [query],
        }
        for item in r.json().get("organic", [])
    ]


def search_many(
    queries: list[str],
    lang: str,
    max_queries: int = 3,
    max_pages: int = 3,
    **_kwargs,  # domains/max_domains 등 구버전 인자 무시
) -> list[dict]:
    """Run Serper on multiple queries, paginating through results.

    max_queries × max_pages × 10 = 최대 결과 수 (예: 3×3×10 = 90개).
    """
    cleaned = [q.strip() for q in queries if q and q.strip()][:max_queries]
    if not cleaned:
        return []

    out: list[dict] = []
    seen: set[str] = set()

    for q in cleaned:
        for page in range(1, max_pages + 1):
            for item in search(q, lang=lang, page=page):
                u = item.get("url", "").strip()
                if not u or u in seen:
                    continue
                seen.add(u)
                out.append(item)
    return out
