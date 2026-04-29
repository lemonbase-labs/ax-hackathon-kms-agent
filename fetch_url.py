"""Phase 0: Verify integration line — URL → extract → bifrost summary → Notion row."""
import os

import requests
import trafilatura
from dotenv import load_dotenv
from notion_client import Client as NotionClient
from openai import OpenAI

load_dotenv()

URL = "https://www.library.hbs.edu/working-knowledge/want-better-performance-reviews-change-this-one-word"


def fetch_html(url: str) -> str:
    print(f"[1/4] Fetching {url}")
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (kms-agent phase0)"},
        timeout=30,
    )
    r.raise_for_status()
    return r.text


def extract_text(html: str) -> str:
    print("[2/4] Extracting body with trafilatura")
    text = trafilatura.extract(html)
    if not text:
        raise RuntimeError("trafilatura extracted empty body")
    print(f"      -> {len(text)} chars")
    return text


def summarize(text: str) -> str:
    print("[3/4] Calling bifrost for summary")
    base = os.environ["BIFROST_URL"].rstrip("/").removesuffix("/chat/completions")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    client = OpenAI(base_url=base, api_key=os.environ["BIFROST_KEY"])
    resp = client.chat.completions.create(
        model=os.environ["CAS_MODEL"],
        messages=[
            {
                "role": "system",
                "content": "다음 글을 한국어 한 문장(60자 이내)으로 요약해.",
            },
            {"role": "user", "content": text[:8000]},
        ],
    )
    summary = (resp.choices[0].message.content or "").strip()
    print(f"      -> {summary!r}")
    return summary


def write_notion(summary: str, url: str) -> str:
    print("[4/4] Writing to Notion")
    notion = NotionClient(auth=os.environ["NOTION_TOKEN"])
    db = notion.databases.retrieve(database_id=os.environ["NOTION_DB_ID"])
    data_source_id = db["data_sources"][0]["id"]
    page = notion.pages.create(
        parent={"type": "data_source_id", "data_source_id": data_source_id},
        properties={
            "주제": {"title": [{"text": {"content": summary[:200] or "(empty)"}}]},
            "키워드": {"multi_select": [{"name": "phase0-test"}]},
            "Source": {"rich_text": [{"text": {"content": url}}]},
            "Status": {"status": {"name": "Draft"}},
        },
    )
    print(f"      -> page id: {page['id']}")
    return page["url"]


def main() -> None:
    html = fetch_html(URL)
    text = extract_text(html)
    summary = summarize(text)
    page_url = write_notion(summary, URL)
    print(f"\nDone. Notion page: {page_url}")


if __name__ == "__main__":
    main()
