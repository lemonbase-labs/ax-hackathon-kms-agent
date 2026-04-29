"""Weekly batch entrypoint: fetch active topics from Notion, run pipeline for each.

Topics are processed in parallel via ThreadPoolExecutor. A failure in one topic
does not block the others. Output may interleave across topics.
"""
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

from kms import db
from kms.notion_topics import fetch_active_topics
from kms.pipeline import run_pipeline

MAX_WORKERS = 3
_print_lock = threading.Lock()


def _log(msg: str, *, err: bool = False) -> None:
    with _print_lock:
        print(msg, file=sys.stderr if err else sys.stdout, flush=True)


def _process(topic: str) -> dict:
    try:
        r = run_pipeline(topic)
        return {"topic": topic, **r}
    except Exception as e:
        _log(f"  ! {topic} crashed: {e}", err=True)
        traceback.print_exc(file=sys.stderr)
        return {"topic": topic, "status": "error", "error": str(e)}


def run_weekly() -> dict:
    topics = fetch_active_topics()
    _log(f"Found {len(topics)} active topic(s). Workers: {MAX_WORKERS}")

    # Pre-register all page mappings serially (fast, single sqlite writer).
    for t in topics:
        db.upsert_topic_page(topic=t["topic"], notion_page_id=t["notion_page_id"])

    summary = {
        "total": len(topics),
        "drafted": 0,
        "sources_only": 0,
        "no_change": 0,
        "skipped": 0,
        "error": 0,
        "results": [],
    }

    if not topics:
        _log("No active topics. Done.")
        return summary

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_process, t["topic"]): t["topic"] for t in topics}
        done_count = 0
        for fut in as_completed(futures):
            r = fut.result()
            done_count += 1
            status = r.get("status", "ok")
            summary[status] = summary.get(status, 0) + 1
            summary["results"].append(r)
            _log(f"[{done_count}/{len(topics)}] {r['topic']} → {status} | {_brief(r)}")

    _log("\n=== Weekly run summary ===")
    _log(
        f"total={summary['total']} drafted={summary['drafted']} "
        f"sources_only={summary['sources_only']} no_change={summary['no_change']} "
        f"skipped={summary['skipped']} error={summary['error']}"
    )
    return summary


def _brief(r: dict) -> str:
    parts = []
    if "new_for_source" in r:
        parts.append(f"+source={r['new_for_source']}")
    if "new_for_draft" in r:
        parts.append(f"+draft_elig={r['new_for_draft']}")
    if "draft_eligible_total" in r:
        parts.append(f"total_elig={r['draft_eligible_total']}")
    if "reason" in r:
        parts.append(f"reason={r['reason']}")
    if "error" in r:
        parts.append(f"error={r['error']}")
    return " ".join(parts)


if __name__ == "__main__":
    load_dotenv()
    run_weekly()
