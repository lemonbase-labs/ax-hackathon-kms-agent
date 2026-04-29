"""Feed whitelist loader — reads kms/feeds.txt fresh on every call (no cache).

Format per line: '<name> <url>'. Lines starting with '#' or empty are skipped.
"""
from pathlib import Path

FEEDS_FILE = Path(__file__).parent / "feeds.txt"


def _parse(content: str) -> tuple[dict[str, str], list[tuple[int, str]]]:
    """Return (enabled_feeds, errors). errors is [(line_no, message), ...]."""
    feeds: dict[str, str] = {}
    errors: list[tuple[int, str]] = []
    for i, raw in enumerate(content.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            errors.append((i, "expected '<name> <url>'"))
            continue
        name, url = parts[0], parts[1].strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            errors.append((i, f"URL must start with http(s)://: {url!r}"))
            continue
        if name in feeds:
            errors.append((i, f"duplicate feed name: {name!r}"))
            continue
        feeds[name] = url
    return feeds, errors


def load() -> dict[str, str]:
    """Return enabled feeds as {name: url}. Skips malformed lines silently
    (validation happens at save time)."""
    content = FEEDS_FILE.read_text(encoding="utf-8")
    feeds, _ = _parse(content)
    return feeds


def load_raw() -> str:
    return FEEDS_FILE.read_text(encoding="utf-8")


def save(content: str) -> None:
    """Validate and write. Raises ValueError with line number on parse errors."""
    _, errors = _parse(content)
    if errors:
        msg = "; ".join(f"line {n}: {m}" for n, m in errors)
        raise ValueError(msg)
    FEEDS_FILE.write_text(content, encoding="utf-8")
