"""HTML extraction with requests first, Playwright-stealth fallback."""
import asyncio
import os
from html.parser import HTMLParser

import requests
import trafilatura

UA = "Mozilla/5.0 (kms-agent phase1)"
PLAYWRIGHT_TIMEOUT_MS = 30000
LOGIN_HINTS = (
    "sign in",
    "log in",
    "subscribe",
    "membership",
    "paywall",
    "구독",
    "로그인",
)


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.og_title = ""
        self.og_desc = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag != "meta":
            return
        d = dict(attrs)
        prop = d.get("property") or d.get("name") or ""
        content = d.get("content", "")
        if prop == "og:title" and not self.og_title:
            self.og_title = content
        elif prop in ("og:description", "description") and not self.og_desc:
            self.og_desc = content


def _extract_og_summary(html: str) -> str | None:
    """Return 'title\\n\\ndescription' from og meta tags, or None if unavailable."""
    p = _MetaParser()
    try:
        p.feed(html[:20000])
    except Exception:
        pass
    if not p.og_desc:
        return None
    return f"{p.og_title}\n\n{p.og_desc}".strip()


def extract(url: str, timeout: int = 30) -> dict | None:
    """Returns {url, text} on success; None on any failure.

    Strategy:
    1) requests + trafilatura (fast path)
    2) Playwright rendered HTML + trafilatura (fallback)
    """
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        print(f"  ! fetch failed: {url} ({e})")
        return _extract_with_playwright(url, timeout=timeout)
    text = trafilatura.extract(r.text)
    if text and text.strip() and not _looks_like_login_wall(text):
        return {"url": url, "text": text}
    og = _extract_og_summary(r.text)
    if og:
        print(f"  · og:description fallback: {url}")
        return {"url": url, "text": og}
    print(f"  ! empty/paywall body (requests): {url}")
    return _extract_with_playwright(url, timeout=timeout)


def _extract_with_playwright(url: str, timeout: int = 30) -> dict | None:
    """Fallback extraction via browser rendering.

    Optional env:
    - PLAYWRIGHT_STORAGE_STATE: path to storage_state.json for logged-in sessions.
    """
    try:
        html = asyncio.run(_extract_html_with_playwright(url, timeout))
    except Exception as e:
        print(f"  ! playwright failed: {url} ({e})")
        return None

    text = trafilatura.extract(html)
    if text and text.strip() and not _looks_like_login_wall(text):
        return {"url": url, "text": text}
    og = _extract_og_summary(html)
    if og:
        print(f"  · og:description fallback (playwright): {url}")
        return {"url": url, "text": og}
    print(f"  ! empty/paywall body (playwright): {url}")
    return None


def _looks_like_login_wall(text: str) -> bool:
    t = text.lower()
    return any(hint in t for hint in LOGIN_HINTS)


async def _extract_html_with_playwright(url: str, timeout: int = 30) -> str:
    """Render page using async Playwright + stealth and return HTML."""
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth

    storage_state = os.getenv("PLAYWRIGHT_STORAGE_STATE", "").strip() or None
    timeout_ms = max(timeout * 1000, PLAYWRIGHT_TIMEOUT_MS)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_kwargs = {
            "user_agent": UA,
            "viewport": {"width": 1366, "height": 900},
        }
        if storage_state:
            context_kwargs["storage_state"] = storage_state
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(1200)
        html = await page.content()
        await context.close()
        await browser.close()
        return html
