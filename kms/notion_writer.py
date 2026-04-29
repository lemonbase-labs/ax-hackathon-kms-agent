"""Notion writer — creates one row in Test DB with draft body."""
import os

from notion_client import Client

# Notion paragraph rich_text content limit is 2000 chars. Keep margin.
CHUNK = 1900


def write_draft(
    topic: str, keywords: list[str], sources: list[str], draft: str
) -> str:
    notion = Client(auth=os.environ["NOTION_TOKEN"])
    db = notion.databases.retrieve(database_id=os.environ["NOTION_DB_ID"])
    data_source_id = db["data_sources"][0]["id"]

    page = notion.pages.create(
        parent={"type": "data_source_id", "data_source_id": data_source_id},
        properties={
            "주제": {"title": [{"text": {"content": topic[:200]}}]},
            "키워드": {"multi_select": [{"name": kw[:100]} for kw in keywords]},
            "Source": {"rich_text": [{"text": {"content": "\n".join(sources)[:1900]}}]},
            "Status": {"status": {"name": "Draft"}},
        },
        children=_to_blocks(draft),
    )
    return page["url"]


def _to_blocks(text: str) -> list[dict]:
    """Split markdown text into paragraph blocks under Notion's 2000-char limit.

    Phase 1a: no markdown→blocks rendering. Headers/links remain as raw text.
    """
    if not text:
        return []
    chunks = [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            },
        }
        for chunk in chunks
    ]
