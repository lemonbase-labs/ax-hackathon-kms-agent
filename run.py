"""Phase 1b CLI: topic → keywords → RSS+CSE → extract → score → draft → Notion."""
import argparse

from dotenv import load_dotenv

from kms.draft import synthesize
from kms.extract import extract
from kms.filter import score_and_select
from kms.keyword_extract import extract_keywords
from kms.notion_writer import write_draft
from kms.search import search as cse_search
from kms.sources import fetch_candidates


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


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="KMS draft generator (Phase 1b)")
    parser.add_argument("topic", help="주제어 (예: '수습 평가')")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    print(f"[1/6] Extracting keywords for: {args.topic!r}")
    kws = extract_keywords(args.topic)
    print(f"      en: {kws['en']}")
    print(f"      ko: {kws['ko']}")

    print("[2/6] Fetching candidates (RSS + Google CSE)")
    rss = fetch_candidates(kws["en"])
    cse_en = cse_search(kws["en"][0], lang="en") if kws["en"] else []
    cse_ko = cse_search(kws["ko"][0], lang="ko") if kws["ko"] else []
    candidates = _dedupe_by_url(rss, cse_en, cse_ko)
    print(
        f"      -> RSS={len(rss)}  CSE(en)={len(cse_en)}  CSE(ko)={len(cse_ko)}  "
        f"total(dedup)={len(candidates)}"
    )
    if not candidates:
        print("No candidates found from any source. Exit.")
        return
    for c in candidates[:15]:
        print(f"        [{c['source']:8s}] {c['title'][:75]}")

    print(f"[3/6] Extracting body from {len(candidates)} URLs")
    docs: list[dict] = []
    for c in candidates:
        d = extract(c["url"])
        if d:
            d["title"] = c["title"]
            d["source"] = c["source"]
            docs.append(d)
    print(f"      -> {len(docs)} extracted")
    if not docs:
        print("All extractions failed. Exit.")
        return

    print(f"[4/6] Scoring and selecting top {args.top_k}")
    top = score_and_select(args.topic, docs, top_k=args.top_k)
    print(f"      -> {len(top)} selected")
    for t in top:
        sd = t.get("score_detail", {})
        print(
            f"        score={t.get('score')}  "
            f"R={sd.get('relevance')} C={sd.get('credibility')}  {t['url']}"
        )
        print(f"          reason: {sd.get('reason')}")

    print("[5/6] Synthesizing draft")
    draft = synthesize(args.topic, top)
    print(f"      -> {len(draft)} chars")

    print("[6/6] Writing to Notion")
    page_url = write_draft(
        topic=args.topic,
        keywords=kws["en"] + kws["ko"],
        sources=[d["url"] for d in top],
        draft=draft,
    )
    print(f"\nDone. Notion page: {page_url}")


if __name__ == "__main__":
    main()
