"""Prompt loader — reads kms/prompts/<name>.md fresh on every call (no cache)."""
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def list_names() -> list[str]:
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.md"))


def save(name: str, content: str) -> None:
    if name not in list_names():
        raise ValueError(f"Unknown prompt: {name}")
    (PROMPTS_DIR / f"{name}.md").write_text(content, encoding="utf-8")
