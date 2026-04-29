"""Topic → Notion pipeline. Callable from CLI and FastAPI; records phases to SQLite."""
from typing import Callable

from kms import tracker
from kms.curate import propose_angles
from kms.draft import synthesize
from kms.extract import extract
from kms.filter import score_and_select
from kms.keyword_extract import extract_keywords
from kms.notion_writer import write_draft
from kms.search import search as web_search
from kms.sources import fetch_candidates

AngleSelector = Callable[[list[dict]], dict]


def _dedupe_by_url(*lists: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for lst in lists:
        for item in lst:
            url = item.get("url", "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            out.append(item)
    return out


def run_pipeline(
    topic: str,
    top_k: int = 5,
    angle_selector: AngleSelector | None = None,
) -> dict:
    """Execute the full pipeline. Returns {run_id, notion_url} on success.

    angle_selector: 앵글 후보 list → 선택된 1개 dict. None이면 첫 번째 자동 선택.
    """
    t = tracker.start(topic)
    try:
        with t.phase(1, "Extracting keywords") as p:
            kws = extract_keywords(topic)
            p.payload({"en": kws["en"], "ko": kws["ko"]})

        with t.phase(2, "Fetching candidates") as p:
            rss = fetch_candidates(kws["en"])
            web_en = web_search(kws["en"][0], lang="en") if kws["en"] else []
            web_ko = web_search(kws["ko"][0], lang="ko") if kws["ko"] else []
            candidates = _dedupe_by_url(rss, web_en, web_ko)
            p.payload({
                "rss_count": len(rss),
                "serper_en_count": len(web_en),
                "serper_ko_count": len(web_ko),
                "total": len(candidates),
                "candidates": [
                    {"title": c.get("title", ""), "url": c["url"], "source": c.get("source", "")}
                    for c in candidates
                ],
            })
            if not candidates:
                t.finish(error="No candidates found")
                return {"run_id": t.run_id, "error": "No candidates found"}

        with t.phase(3, "Extracting body") as p:
            docs: list[dict] = []
            total = len(candidates)
            for i, c in enumerate(candidates):
                p.progress(f"{i + 1}/{total}")
                d = extract(c["url"])
                if d:
                    d["title"] = c["title"]
                    d["source"] = c["source"]
                    docs.append(d)
            p.payload({"extracted": len(docs), "failed": total - len(docs)})
            if not docs:
                t.finish(error="All extractions failed")
                return {"run_id": t.run_id, "error": "All extractions failed"}

        with t.phase(4, f"Scoring top {top_k}") as p:
            top = score_and_select(topic, docs, top_k=top_k)
            p.payload({
                "selected": [
                    {
                        "url": d["url"],
                        "title": d.get("title", ""),
                        "score": d.get("score"),
                        "score_detail": d.get("score_detail", {}),
                    }
                    for d in top
                ],
            })

        with t.phase(5, "Proposing angles") as p:
            angles = propose_angles(topic, top)
            p.payload({"count": len(angles), "angles": angles})
            if angles:
                angle = angle_selector(angles) if angle_selector else angles[0]
            else:
                angle = None

        with t.phase(6, "Synthesizing draft") as p:
            draft = synthesize(topic, top, angle=angle)
            p.payload({"chars": len(draft), "draft": draft, "angle": angle})

        with t.phase(7, "Writing to Notion") as p:
            page_url = write_draft(
                topic=topic,
                keywords=kws["en"] + kws["ko"],
                sources=[d["url"] for d in top],
                draft=draft,
            )
            p.payload({"page_url": page_url})

        t.finish(notion_url=page_url)
        return {"run_id": t.run_id, "notion_url": page_url}
    except Exception as e:
        t.finish(error=str(e))
        raise
