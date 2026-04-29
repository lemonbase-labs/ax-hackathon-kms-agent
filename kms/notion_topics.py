"""Fetch active topic rows from the master Notion DB (same as the result DB).

Active = "주제" title is non-empty AND Status is not Approved/Rejected.
Returns rows for weekly_run to iterate.
"""
import os

from notion_client import Client

INACTIVE_STATUSES = {"Approved", "Rejected"}


def fetch_active_topics() -> list[dict]:
    """Returns list of {topic, notion_page_id} for active rows."""
    notion = Client(auth=os.environ["NOTION_TOKEN"])
    db_meta = notion.databases.retrieve(database_id=os.environ["NOTION_DB_ID"])
    data_source_id = db_meta["data_sources"][0]["id"]

    results: list[dict] = []
    cursor: str | None = None
    while True:
        kwargs = {"data_source_id": data_source_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.data_sources.query(**kwargs)
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    out: list[dict] = []
    for page in results:
        topic = _read_title(page, "주제")
        if not topic:
            continue
        if _read_status(page, "Status") in INACTIVE_STATUSES:
            continue
        out.append({"topic": topic, "notion_page_id": page["id"]})
    return out


def _read_title(page: dict, name: str) -> str:
    prop = page.get("properties", {}).get(name, {})
    return "".join(rt.get("plain_text", "") for rt in prop.get("title", [])).strip()


def _read_status(page: dict, name: str) -> str:
    prop = page.get("properties", {}).get(name, {})
    return (prop.get("status") or {}).get("name", "")
