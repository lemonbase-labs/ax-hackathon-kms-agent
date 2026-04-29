"""Notion writer — upsert mode.

Same topic → single Notion page (lookup by db.topic_pages).
First call creates the page; subsequent calls union sources/keywords
and replace the page body with the new draft.
"""
import os

from notion_client import Client

from kms import db

# Notion paragraph rich_text content limit is 2000 chars. Keep margin.
CHUNK = 1900
SOURCE_FIELD_MAX = 1900


def write_draft(
    topic: str,
    keywords: list[str],
    sources: list[str],
    draft: str | None,
) -> tuple[str, str | None]:
    """Upsert: same topic always lands in the same Notion row.

    draft=None: properties (Source/Keywords) only — body untouched.
    draft=str: properties + body fully replaced with the new draft.

    Returns (page_url, action) where action is 'created' / 'updated' / None.
    action is None when the draft body did not change (sources-only writes).
    """
    notion = Client(auth=os.environ["NOTION_TOKEN"])
    db_meta = notion.databases.retrieve(database_id=os.environ["NOTION_DB_ID"])
    data_source_id = db_meta["data_sources"][0]["id"]

    existing = db.get_topic_page(topic)
    if existing:
        page_id = existing["notion_page_id"]
        page = notion.pages.retrieve(page_id=page_id)
        merged_sources = _union_preserving_order(
            _read_source_field(page), sources
        )
        merged_keywords = _union_preserving_order(
            _read_multi_select(page, "키워드"), keywords
        )
        notion.pages.update(
            page_id=page_id,
            properties={
                "키워드": {
                    "multi_select": [{"name": kw[:100]} for kw in merged_keywords]
                },
                "Source": {
                    "rich_text": [
                        {"text": {"content": _truncate_sources(merged_sources)}}
                    ]
                },
            },
        )
        if draft is not None:
            _replace_page_body(notion, page_id, _to_blocks(draft))
        db.upsert_topic_page(topic, page_id)
        action = "updated" if draft is not None else None
        return page["url"], action

    page = notion.pages.create(
        parent={"type": "data_source_id", "data_source_id": data_source_id},
        properties={
            "주제": {"title": [{"text": {"content": topic[:200]}}]},
            "키워드": {"multi_select": [{"name": kw[:100]} for kw in keywords]},
            "Source": {
                "rich_text": [{"text": {"content": _truncate_sources(sources)}}]
            },
            "Status": {"status": {"name": "Draft"}},
        },
        children=_to_blocks(draft) if draft else [],
    )
    db.upsert_topic_page(topic, page["id"])
    action = "created" if draft else None
    return page["url"], action


def _to_blocks(text: str) -> list[dict]:
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


def _union_preserving_order(existing: list[str], new: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in [*existing, *new]:
        s = item.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _read_source_field(page: dict) -> list[str]:
    prop = page.get("properties", {}).get("Source", {})
    rich = prop.get("rich_text", [])
    text = "".join(rt.get("plain_text", "") for rt in rich)
    return [line for line in text.split("\n") if line.strip()]


def _read_multi_select(page: dict, name: str) -> list[str]:
    prop = page.get("properties", {}).get(name, {})
    return [opt.get("name", "") for opt in prop.get("multi_select", [])]


def _truncate_sources(sources: list[str]) -> str:
    """Join with newlines; if total exceeds limit, keep most recent (tail)."""
    if not sources:
        return ""
    joined = "\n".join(sources)
    if len(joined) <= SOURCE_FIELD_MAX:
        return joined
    kept: list[str] = []
    running = 0
    for s in reversed(sources):
        add = len(s) + (1 if kept else 0)
        if running + add > SOURCE_FIELD_MAX:
            break
        kept.append(s)
        running += add
    return "\n".join(reversed(kept))


def _replace_page_body(notion: Client, page_id: str, new_blocks: list[dict]) -> None:
    """Archive existing top-level blocks, then append new ones."""
    cursor: str | None = None
    while True:
        kwargs = {"block_id": page_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.blocks.children.list(**kwargs)
        for b in resp.get("results", []):
            notion.blocks.delete(block_id=b["id"])
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    if new_blocks:
        notion.blocks.children.append(block_id=page_id, children=new_blocks)
