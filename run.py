"""CLI: topic → keywords → RSS+Serper → extract → score → angle → draft → Notion."""
import argparse

from dotenv import load_dotenv

from kms.pipeline import run_pipeline


def cli_select_angle(angles: list[dict]) -> dict:
    """터미널에서 앵글 후보 보여주고 사용자가 1개 선택 (workflow.md 품질 게이트 1)."""
    print("\n  [앵글 후보]")
    for i, a in enumerate(angles, 1):
        print(f"  {i}) {a.get('title', '')}")
        print(f"     인사이트: {a.get('insight', '')}")
        print(f"     차별점: {a.get('differentiator', '')}")
        print(f"     한국 HR 적용: {a.get('korea_context', '')}")
    while True:
        raw = input(f"\n  Choose angle [1-{len(angles)}] (Enter=1): ").strip()
        if not raw:
            return angles[0]
        try:
            idx = int(raw)
            if 1 <= idx <= len(angles):
                return angles[idx - 1]
        except ValueError:
            pass
        print(f"  invalid input. enter 1-{len(angles)}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="KMS draft generator")
    parser.add_argument("topic", help="주제어 (예: '수습 평가')")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--auto-angle", action="store_true",
        help="앵글 첫 번째 자동 선택 (사람 개입 스킵)",
    )
    args = parser.parse_args()

    selector = None if args.auto_angle else cli_select_angle
    result = run_pipeline(args.topic, top_k=args.top_k, angle_selector=selector)
    if "error" in result:
        print(f"\nFailed (run #{result['run_id']}): {result['error']}")
    else:
        print(f"\nDone (run #{result['run_id']}). Notion page: {result['notion_url']}")


if __name__ == "__main__":
    main()
