"""Topic → Notion pipeline with cross-run dedupe + two-stage gates.

Score scale (filter.md): relevance(1-10) + credibility(1-10) = total 2-20.
SOURCE_THRESHOLD/DRAFT_THRESHOLD are placeholders — tune after observing real distribution.
"""
from kms import db, seen_store, tracker
from kms.draft import synthesize
from kms.extract import extract
from kms.filter import score_and_select
from kms.keyword_extract import extract_keywords
from kms.notion_writer import write_draft
from kms.search import search as web_search
from kms.sources import fetch_candidates

SOURCE_THRESHOLD = 3   # score≥ → Notion Source field
DRAFT_THRESHOLD = 4    # score≥ → eligible for draft synthesis
DRAFT_BATCH = 3        # draft regenerates when (eligible_total - last_drafted) ≥ this


def decide_action(
    scored: list[dict],
    prev_source_count: int,
    prev_draft_eligible: int,
    prev_last_drafted: int,
) -> dict:
    """Pure function: gate scored docs, compute counters, decide draft trigger."""
    new_for_source = [d for d in scored if d.get("score", 0) >= SOURCE_THRESHOLD]
    new_for_draft = [d for d in scored if d.get("score", 0) >= DRAFT_THRESHOLD]
    new_source_count = prev_source_count + len(new_for_source)
    new_draft_eligible = prev_draft_eligible + len(new_for_draft)
    delta_for_draft = new_draft_eligible - prev_last_drafted
    should_draft = delta_for_draft >= DRAFT_BATCH
    return {
        "new_for_source": new_for_source,
        "new_for_draft": new_for_draft,
        "should_draft": should_draft,
        "new_source_count": new_source_count,
        "new_draft_eligible": new_draft_eligible,
        "delta_for_draft": delta_for_draft,
    }


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


def run_pipeline(topic: str, top_k: int = 5) -> dict:
    """Execute pipeline. top_k is unused now (kept for CLI compatibility);
    all new candidates are scored. Returns {run_id, status, ...}.
    """
    t = tracker.start(topic)
    try:
        with t.phase(1, "Extracting keywords") as p:
            db.save_step_input(t.run_id, "keyword_extract", {"topic": topic})
            kws = extract_keywords(topic)
            p.payload({"en": kws["en"], "ko": kws["ko"]})

        with t.phase(2, "Fetching candidates") as p:
            rss = fetch_candidates(kws["en"])
            web_en = web_search(kws["en"][0], lang="en") if kws["en"] else []
            web_ko = web_search(kws["ko"][0], lang="ko") if kws["ko"] else []
            all_candidates = _dedupe_by_url(rss, web_en, web_ko)
            new_candidates = seen_store.filter_new(topic, all_candidates)
            for c in new_candidates:
                seen_store.insert_discovered(
                    topic=topic,
                    url=c["url"],
                    title=c.get("title"),
                    source=c.get("source"),
                    run_id=t.run_id,
                )
            p.payload({
                "rss_count": len(rss),
                "serper_en_count": len(web_en),
                "serper_ko_count": len(web_ko),
                "total_candidates": len(all_candidates),
                "new_count": len(new_candidates),
                "candidates": [
                    {"title": c.get("title", ""), "url": c["url"], "source": c.get("source", "")}
                    for c in new_candidates
                ],
            })
            if not new_candidates:
                t.finish()
                return {"run_id": t.run_id, "status": "skipped", "reason": "no new candidates"}

        with t.phase(3, "Extracting body") as p:
            docs: list[dict] = []
            total = len(new_candidates)
            for i, c in enumerate(new_candidates):
                p.progress(f"{i + 1}/{total}")
                d = extract(c["url"])
                if d:
                    d["title"] = c["title"]
                    d["source"] = c["source"]
                    docs.append(d)
                    seen_store.mark_status(topic, c["url"], "extracted")
                else:
                    seen_store.mark_status(topic, c["url"], "extract_failed")
            p.payload({"extracted": len(docs), "failed": total - len(docs)})
            if not docs:
                t.finish(error="All extractions failed")
                return {"run_id": t.run_id, "status": "error", "error": "All extractions failed"}

        with t.phase(4, "Scoring new candidates") as p:
            db.save_step_input(
                t.run_id, "filter", {"topic": topic, "docs": docs, "top_k": len(docs)}
            )
            scored = score_and_select(topic, docs, top_k=len(docs))
            for d in scored:
                seen_store.mark_status(topic, d["url"], "scored", score=d["score"])
            p.payload({
                "scored": [
                    {
                        "url": d["url"],
                        "title": d.get("title", ""),
                        "score": d.get("score"),
                        "score_detail": d.get("score_detail", {}),
                    }
                    for d in scored
                ],
            })

        tp = db.get_topic_page(topic)
        prev_source_count = tp["source_count"] if tp else 0
        prev_draft_eligible = tp["draft_eligible_count"] if tp else 0
        prev_last_drafted = tp["last_drafted_source_count"] if tp else 0
        action = decide_action(
            scored, prev_source_count, prev_draft_eligible, prev_last_drafted
        )
        new_for_source = action["new_for_source"]
        new_for_draft = action["new_for_draft"]
        new_source_count = action["new_source_count"]
        new_draft_eligible = action["new_draft_eligible"]
        delta_for_draft = action["delta_for_draft"]
        should_draft = action["should_draft"]

        if not new_for_source and not should_draft:
            t.finish()
            return {
                "run_id": t.run_id,
                "status": "no_change",
                "new_for_source": 0,
                "new_for_draft": len(new_for_draft),
                "draft_eligible_total": new_draft_eligible,
            }

        draft_text: str | None = None
        if should_draft:
            with t.phase(5, "Synthesizing draft") as p:
                eligible_rows = seen_store.list_by_min_score(topic, DRAFT_THRESHOLD)
                # Include this run's newly scored ≥4 docs (mark_status committed them already).
                docs_for_draft: list[dict] = []
                for r in eligible_rows:
                    extracted = extract(r["url_original"])
                    if extracted:
                        extracted["title"] = r.get("title") or ""
                        docs_for_draft.append(extracted)
                if docs_for_draft:
                    draft_text = synthesize(topic, docs_for_draft)
                    db.save_step_input(
                        t.run_id, "draft", {"topic": topic, "docs": docs_for_draft}
                    )
                p.payload({
                    "doc_count": len(docs_for_draft),
                    "chars": len(draft_text or ""),
                    "draft": draft_text or "",
                    "trigger": {
                        "delta": delta_for_draft,
                        "draft_eligible_total": new_draft_eligible,
                        "last_drafted": prev_last_drafted,
                    },
                })

        with t.phase(6, "Writing to Notion") as p:
            page_url, action = write_draft(
                topic=topic,
                keywords=kws["en"] + kws["ko"],
                sources=[d["url"] for d in new_for_source],
                draft=draft_text,
            )
            p.payload({"page_url": page_url, "draft_replaced": draft_text is not None})

        # update counters + attach notion page id to seen_sources of this run
        tp_after = db.get_topic_page(topic)
        page_id = tp_after["notion_page_id"] if tp_after else None
        if page_id:
            for d in new_for_source:
                seen_store.attach_notion_page(topic, d["url"], page_id)
        db.upsert_topic_page(
            topic=topic,
            notion_page_id=page_id or "",
            source_count=new_source_count,
            draft_eligible_count=new_draft_eligible,
            last_drafted_source_count=(
                new_draft_eligible if should_draft else prev_last_drafted
            ),
        )

        t.finish(notion_url=page_url)
        return {
            "run_id": t.run_id,
            "status": "drafted" if should_draft else "sources_only",
            "notion_url": page_url,
            "notion_action": action,
            "new_for_source": len(new_for_source),
            "new_for_draft": len(new_for_draft),
            "draft_eligible_total": new_draft_eligible,
        }
    except Exception as e:
        t.finish(error=str(e))
        raise
