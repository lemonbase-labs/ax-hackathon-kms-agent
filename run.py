"""CLI: topic → keywords → RSS+Serper → extract → score → draft → Notion."""
import argparse

from dotenv import load_dotenv

from kms.pipeline import run_pipeline


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="KMS draft generator")
    parser.add_argument("topic", help="주제어 (예: '수습 평가')")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    result = run_pipeline(args.topic, top_k=args.top_k)
    status = result.get("status", "ok")
    if status == "error":
        print(f"\nFailed (run #{result['run_id']}): {result.get('error', '')}")
    elif status == "skipped":
        print(f"\nSkipped (run #{result['run_id']}): {result.get('reason', '')}")
    elif status == "no_change":
        print(
            f"\nNo change (run #{result['run_id']}): "
            f"new_for_source={result.get('new_for_source')}, "
            f"draft_eligible_total={result.get('draft_eligible_total')}"
        )
    else:
        url = result.get("notion_url", "")
        print(
            f"\nDone (run #{result['run_id']}, {status}). Notion page: {url} "
            f"[+source={result.get('new_for_source')}, +draft_eligible={result.get('new_for_draft')}]"
        )


if __name__ == "__main__":
    main()
