"""RSS-based article source. Phase 1a: HBR + HR Dive + HR Executive (English)."""
import re

import feedparser

FEEDS = {
    "hbr": "https://feeds.feedburner.com/harvardbusiness",
    "hrdive": "https://www.hrdive.com/feeds/news/",
    "hrexec": "https://hrexecutive.com/feed/",
}

# 단어 단위 매칭 시 너무 흔한 영단어는 제외 (전부 잡혀버려 Claude 스코어링 부담↑)
STOP_WORDS = {
    "the", "and", "for", "from", "with", "this", "that", "your", "their",
    "review", "process", "system", "people",
}
MIN_WORD_LEN = 4


def fetch_candidates(keywords_en: list[str]) -> list[dict]:
    """RSS entries whose title/summary contains any keyword *word* (substring).

    Multi-word keywords ('probation evaluation') are split into individual
    words; an entry matches if any non-stopword word (≥4 chars) is present.
    Returns list of {url, title, source, matched}.
    """
    if not keywords_en:
        return []
    needles = _tokenize(keywords_en)
    if not needles:
        return []
    seen_urls: set[str] = set()
    results: list[dict] = []

    for source_name, feed_url in FEEDS.items():
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
            matched = sorted({w for w in needles if w in haystack})
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


def _tokenize(keywords: list[str]) -> set[str]:
    out: set[str] = set()
    for kw in keywords:
        for w in re.split(r"[^a-zA-Z]+", kw.lower()):
            if len(w) >= MIN_WORD_LEN and w not in STOP_WORDS:
                out.add(w)
    return out
