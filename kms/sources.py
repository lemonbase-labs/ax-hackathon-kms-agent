"""RSS-based article source. Feed whitelist is loaded from kms/feeds.txt."""

import feedparser

from kms import _feeds


def fetch_candidates(keywords_en: list[str]) -> list[dict]:
    """RSS entries whose title/summary contains a keyword *phrase*.

    Phrase matching: 'performance management' must appear as-is (lowercased).
    Word-level tokenizing was abandoned — single common words like 'performance'
    matched almost every entry, exploding RSS hits to 200+.
    Returns list of {url, title, source, matched}.
    """
    if not keywords_en:
        return []
    needles = [k.lower().strip() for k in keywords_en if k.strip()]
    if not needles:
        return []
    seen_urls: set[str] = set()
    results: list[dict] = []

    for source_name, feed_url in _feeds.load().items():
        feed = feedparser.parse(feed_url)
        if feed.bozo and not feed.entries:
            print(f"  ! RSS unavailable ({source_name}): {feed.bozo_exception}")
            continue
        for entry in feed.entries:
            url = entry.get("link", "").strip()
            if not url or url in seen_urls:
                continue
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            haystack = f"{title} {summary}".lower()
            matched = sorted({n for n in needles if n in haystack})
            if not matched:
                continue
            seen_urls.add(url)
            results.append(
                {
                    "url": url,
                    "title": title,
                    "source": source_name,
                    "matched": matched,
                }
            )
    return results
