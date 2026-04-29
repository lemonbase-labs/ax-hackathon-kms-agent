"""Slack incoming webhook notifier.

Silent skip when SLACK_WEBHOOK_URL is unset; logs and swallows on HTTP failure
so the pipeline never dies due to a notification problem.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

TIMEOUT_S = 5


def notify_draft(topic: str, action: str, page_url: str) -> None:
    """Post a single-topic draft notification. action: 'created' | 'updated'."""
    verb = "작성되었습니다" if action == "created" else "갱신되었습니다"
    text = f"KMS 초안이 {verb}.\n • {topic} — {page_url}"
    _post(text)


def notify_weekly_summary(results: list[dict]) -> None:
    """Post a single rolled-up message for the weekly batch run.

    `results` items expect: topic, status, notion_url, notion_action.
    Always posts (even with zero changes) so the channel sees a heartbeat.
    """
    text = _build_weekly_text(results)
    _post(text)


def _build_weekly_text(results: list[dict]) -> str:
    created = [r for r in results if r.get("notion_action") == "created"]
    updated = [r for r in results if r.get("notion_action") == "updated"]
    errors = [r for r in results if r.get("status") == "error"]

    lines: list[str] = []
    if not created and not updated:
        lines.append(
            "이번 주 KMS 초안 정리 완료했습니다. 새로 추가되거나 갱신된 초안은 없습니다."
        )
    else:
        bits = []
        if created:
            bits.append(f"신규 {len(created)}건")
        if updated:
            bits.append(f"갱신 {len(updated)}건")
        lines.append(
            f"이번 주 KMS 초안 정리 완료했습니다. {', '.join(bits)}입니다."
        )

    if created:
        lines.append("")
        lines.append("*신규*")
        for r in created:
            lines.append(f" • {r['topic']} — {r.get('notion_url', '')}")

    if updated:
        lines.append("")
        lines.append("*갱신*")
        for r in updated:
            lines.append(f" • {r['topic']} — {r.get('notion_url', '')}")

    if errors:
        lines.append("")
        topics_str = ", ".join(r["topic"] for r in errors)
        lines.append(f"처리 실패: {len(errors)}건 ({topics_str})")

    return "\n".join(lines)


def _post(text: str) -> None:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    try:
        resp = requests.post(webhook, json={"text": text}, timeout=TIMEOUT_S)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Slack notify failed: %s", e)
