"""Pipeline thresholds — reads kms/config.json fresh on every call (no cache).

Schema:
  source_threshold: int  — score≥ for Notion Source field append
  draft_threshold:  int  — score≥ for draft synthesis eligibility
  draft_batch:      int  — draft regenerates when (eligible_total - last_drafted) ≥ this

Score scale: relevance(1-10) + credibility(1-10) → total 2-20.
"""
import json
from pathlib import Path
from typing import TypedDict

CONFIG_FILE = Path(__file__).parent / "config.json"

KEYS = ("source_threshold", "draft_threshold", "draft_batch")


class Config(TypedDict):
    source_threshold: int
    draft_threshold: int
    draft_batch: int


def _validate(data: dict) -> Config:
    """Return a normalized Config or raise ValueError with a clear message."""
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    out: dict = {}
    for k in KEYS:
        if k not in data:
            raise ValueError(f"missing key: {k!r}")
        v = data[k]
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError(f"{k!r} must be an integer (got {type(v).__name__})")
        out[k] = v
    if not (1 <= out["source_threshold"] <= 20):
        raise ValueError("source_threshold must be in [1, 20]")
    if not (1 <= out["draft_threshold"] <= 20):
        raise ValueError("draft_threshold must be in [1, 20]")
    if out["source_threshold"] > out["draft_threshold"]:
        raise ValueError("source_threshold must be ≤ draft_threshold")
    if out["draft_batch"] < 1:
        raise ValueError("draft_batch must be ≥ 1")
    return out  # type: ignore[return-value]


def load() -> Config:
    raw = CONFIG_FILE.read_text(encoding="utf-8")
    return _validate(json.loads(raw))


def load_raw() -> str:
    return CONFIG_FILE.read_text(encoding="utf-8")


def save(data: dict) -> Config:
    """Validate, then write pretty-printed JSON. Returns the saved Config."""
    cfg = _validate(data)
    CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return cfg
