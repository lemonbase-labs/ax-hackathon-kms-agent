"""RSS feeds + hardcoded section URLs for non-RSS sources."""

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import feedparser
import requests

FEEDS = {
    "hbr":     "https://feeds.feedburner.com/harvardbusiness",
    "hrdive":  "https://www.hrdive.com/feeds/news/",
    "hrexec":  "https://hrexecutive.com/feed/",
    "bersin":  "https://joshbersin.com/feed/",
    "mitsmr":  "https://sloanreview.mit.edu/feed/",
    "mckinsey": "https://www.mckinsey.com/rss",
}

# 우선순위 순으로 정렬 — 앞에서부터 MAX_SECTION_SOURCES개만 크롤링
SECTION_URLS: dict[str, str] = {
    "fortune":     "https://fortune.com/section/leadership/",
    "shrm":        "https://www.shrm.org/topics-tools/news",
    "gallup":      "https://www.gallup.com/workplace/",
    "culture_amp": "https://www.cultureamp.com/blog",
    "lattice":     "https://lattice.com/library",
    "workhuman":   "https://www.workhuman.com/blog/",
    "hr_insight":  "https://www.hrinsight.co.kr/",
}
MAX_SECTION_SOURCES = 5

def fetch_candidates(keywords_en: list[str]) -> list[dict]:
    """RSS entries matching a keyword phrase + section-page article seeds."""
    if not keywords_en:
        return []
    needles = [k.lower().strip() for k in keywords_en if k.strip()]
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
            matched = sorted({n for n in needles if n in haystack})
            if not matched:
                continue
            seen_urls.add(url)
            results.append({"url": url, "title": title, "source": source_name, "matched": matched})

    results.extend(_seed_urls_from_sections(seen_urls))
    return results


def preferred_domains(max_domains: int = 30) -> list[str]:
    """Preferred domains for Serper site: queries — RSS feeds + section URL domains."""
    raw = [_normalize_domain(url) for url in FEEDS.values()]
    raw += [_normalize_domain(url) for url in SECTION_URLS.values()]
    out: list[str] = []
    seen: set[str] = set()
    for d in raw:
        if not d or d in seen:
            continue
        seen.add(d)
        out.append(d)
        if len(out) >= max_domains:
            break
    return out


def filter_to_easy_domains(candidates: list[dict]) -> list[dict]:
    """Pass-through — no CSV filter anymore."""
    return candidates


def apply_media_labels(candidates: list[dict]) -> list[dict]:
    """Attach media_type / media_domain / media_label to each candidate."""
    domain_to_name = {_normalize_domain(url): name for name, url in {**SECTION_URLS}.items()}
    domain_to_name.update({_normalize_domain(url): name for name, url in FEEDS.items()})

    out: list[dict] = []
    for c in candidates:
        item = dict(c)
        domain = _normalize_domain(item.get("url", ""))
        source = str(item.get("source", ""))
        item["media_type"] = _media_type_from_source(source)
        item["media_domain"] = domain
        item["media_label"] = domain_to_name.get(domain) or source or "미분류"
        out.append(item)
    return out


def _title_from_url(url: str) -> str:
    """Best-effort title from URL slug (used before full extraction)."""
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else ""
    slug = slug.rsplit(".", 1)[0] if "." in slug else slug
    return slug.replace("-", " ").replace("_", " ").title() if slug else url


def _seed_urls_from_sections(seen_urls: set[str]) -> list[dict]:
    """Crawl top SECTION_URLS (by priority) and return article links found within each."""
    out: list[dict] = []
    for name, section_url in list(SECTION_URLS.items())[:MAX_SECTION_SOURCES]:
        print(f"  · scraping section: {name} ({section_url})")
        for url in _article_links_from_section(section_url):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            out.append({
                "url": url,
                "title": _title_from_url(url),
                "source": name,
                "matched": ["seed"],
            })
    return out


_SKIP_SEGMENTS = {
    "tag", "tags", "author", "authors", "category", "categories",
    "page", "search", "about", "contact", "subscribe", "signup", "login",
}

_CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "a":
            for name, val in attrs:
                if name == "href" and val:
                    self.hrefs.append(val)


def _article_links_from_section(section_url: str, max_articles: int = 8) -> list[str]:
    """Crawl a section page and return article URLs within it."""
    try:
        r = requests.get(section_url, headers={"User-Agent": _CHROME_UA}, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  ! section fetch failed ({section_url}): {e}")
        return []

    base = _normalize_domain(section_url)
    section_path = urlparse(section_url).path.rstrip("/")

    parser = _LinkParser()
    parser.feed(r.text)

    def _is_article(path: str) -> bool:
        path = path.rstrip("/")
        if not path or path == section_path:
            return False
        segments = [s for s in path.split("/") if s]
        if len(segments) < 2:
            return False
        return not any(s in _SKIP_SEGMENTS for s in segments)

    def _has_year(path: str) -> bool:
        return any(s.isdigit() and len(s) == 4 and 2000 <= int(s) <= 2100 for s in path.split("/"))

    candidate_hrefs = [
        urljoin(section_url, href)
        for href in parser.hrefs
        if _normalize_domain(urljoin(section_url, href)) == base
    ]
    in_section = [f for f in candidate_hrefs if urlparse(f).path.rstrip("/").startswith(section_path + "/")]
    year_based = [f for f in candidate_hrefs if _has_year(urlparse(f).path)]
    valid_in_section = [f for f in in_section if _is_article(urlparse(f).path)]
    pool = valid_in_section or year_based or candidate_hrefs

    seen: set[str] = set()
    results: list[str] = []
    for full in pool:
        p = urlparse(full)
        path = p.path.rstrip("/")
        if not _is_article(path):
            continue
        clean = f"{p.scheme}://{p.netloc}{path}"
        if clean in seen:
            continue
        seen.add(clean)
        results.append(clean)
        if len(results) >= max_articles:
            break

    if not results:
        results = _article_links_playwright(section_url, max_articles)
    return results


def _article_links_playwright(section_url: str, max_articles: int = 8) -> list[str]:
    """Playwright fallback for JS-rendered section pages."""
    import asyncio
    try:
        return asyncio.run(_async_article_links(section_url, max_articles))
    except Exception as e:
        print(f"  ! playwright section fetch failed ({section_url}): {e}")
        return []


async def _async_article_links(section_url: str, max_articles: int) -> list[str]:
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth

    base = _normalize_domain(section_url)
    section_path = urlparse(section_url).path.rstrip("/")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=_CHROME_UA, viewport={"width": 1366, "height": 900})
        page = await ctx.new_page()
        await Stealth().apply_stealth_async(page)
        await page.goto(section_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        await browser.close()

    seen: set[str] = set()
    results: list[str] = []
    for full in hrefs:
        if _normalize_domain(full) != base:
            continue
        p = urlparse(full)
        path = p.path.rstrip("/")
        if not path or path == section_path:
            continue
        segments = [s for s in path.split("/") if s]
        if len(segments) < 2 or any(s in _SKIP_SEGMENTS for s in segments):
            continue
        clean = f"{p.scheme}://{p.netloc}{path}"
        if clean in seen:
            continue
        seen.add(clean)
        results.append(clean)
        if len(results) >= max_articles:
            break
    return results


def _normalize_domain(url_or_domain: str) -> str:
    raw = url_or_domain.strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"https://{raw}"
    try:
        return urlparse(raw).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _media_type_from_source(source: str) -> str:
    if source.startswith("serper:"):
        return "serper"
    if source in SECTION_URLS:
        return "section_seed"
    if source in FEEDS:
        return "rss"
    return "unknown"
