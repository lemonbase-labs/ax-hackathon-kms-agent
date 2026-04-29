"""URL canonicalization for cross-run dedupe.

Rules (decided minimal):
- scheme: http→https, lowercase
- host: lowercase, strip leading "www."
- query: drop utm_*, gclid, fbclid; keep order of remaining params
- fragment: drop
- path: keep as-is (case sensitive). trailing "/" preserved unless path is just "/"

Redirects are NOT followed (no HEAD request) — out of scope.
"""
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_DROP_PARAM_PREFIXES = ("utm_",)
_DROP_PARAMS = {"gclid", "fbclid", "mc_cid", "mc_eid"}


def canonicalize(url: str) -> str:
    if not url or not url.strip():
        return ""
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip().lower()

    scheme = "https" if parsed.scheme in ("http", "https") else parsed.scheme.lower()
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    kept = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.startswith(_DROP_PARAM_PREFIXES) and k not in _DROP_PARAMS
    ]
    query = urlencode(kept)

    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    return urlunparse((scheme, host, path, parsed.params, query, ""))
