"""HTML fetch + body extraction via trafilatura."""
import requests
import trafilatura

UA = "Mozilla/5.0 (kms-agent phase1)"


def extract(url: str, timeout: int = 30) -> dict | None:
    """Returns {url, text} on success; None on any failure."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        print(f"  ! fetch failed: {url} ({e})")
        return None
    text = trafilatura.extract(r.text)
    if not text:
        print(f"  ! empty body: {url}")
        return None
    return {"url": url, "text": text}
