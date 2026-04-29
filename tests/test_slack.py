import unittest
from unittest.mock import patch

import requests

from kms.slack import _build_weekly_text, notify_draft, notify_weekly_summary


class TestNotifyDraft(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    @patch("kms.slack.requests.post")
    def test_skip_when_webhook_unset(self, mock_post):
        notify_draft("성과관리", "created", "https://notion.so/x")
        mock_post.assert_not_called()

    @patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/x"})
    @patch("kms.slack.requests.post")
    def test_posts_created_payload(self, mock_post):
        mock_post.return_value.raise_for_status.return_value = None

        notify_draft("성과관리", "created", "https://notion.so/abc")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://hooks.slack.com/services/T/B/x")
        text = kwargs["json"]["text"]
        self.assertIn("성과관리", text)
        self.assertIn("작성됨", text)
        self.assertIn("https://notion.so/abc", text)

    @patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/x"})
    @patch("kms.slack.requests.post")
    def test_posts_updated_payload(self, mock_post):
        mock_post.return_value.raise_for_status.return_value = None

        notify_draft("성과관리", "updated", "https://notion.so/abc")

        text = mock_post.call_args.kwargs["json"]["text"]
        self.assertIn("업데이트됨", text)

    @patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/x"})
    @patch("kms.slack.requests.post")
    def test_swallows_http_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("boom")
        # Must not raise — pipeline should never die from a notify failure.
        notify_draft("성과관리", "created", "https://notion.so/abc")


class TestWeeklySummary(unittest.TestCase):
    def test_mixed_created_updated_with_errors(self):
        results = [
            {"topic": "성과관리", "status": "drafted", "notion_url": "https://notion.so/a", "notion_action": "created"},
            {"topic": "OKR", "status": "drafted", "notion_url": "https://notion.so/b", "notion_action": "created"},
            {"topic": "1on1", "status": "drafted", "notion_url": "https://notion.so/c", "notion_action": "updated"},
            {"topic": "평가제도", "status": "sources_only", "notion_url": "https://notion.so/d", "notion_action": None},
            {"topic": "보상", "status": "error", "error": "boom"},
        ]
        text = _build_weekly_text(results)

        self.assertIn("신규 2건", text)
        self.assertIn("갱신 1건", text)
        self.assertIn("*신규*", text)
        self.assertIn("성과관리 — https://notion.so/a", text)
        self.assertIn("OKR — https://notion.so/b", text)
        self.assertIn("*갱신*", text)
        self.assertIn("1on1 — https://notion.so/c", text)
        self.assertIn("처리 실패: 1건 (보상)", text)
        # sources_only 토픽은 어느 섹션에도 안 나온다
        self.assertNotIn("평가제도", text)

    def test_zero_changes_no_errors_still_posts(self):
        results = [
            {"topic": "A", "status": "no_change"},
            {"topic": "B", "status": "skipped", "reason": "no new candidates"},
        ]
        text = _build_weekly_text(results)
        self.assertIn("새로 추가되거나 갱신된 초안은 없습니다", text)
        self.assertNotIn("*신규*", text)
        self.assertNotIn("*갱신*", text)
        self.assertNotIn("처리 실패", text)

    def test_zero_changes_with_errors(self):
        results = [
            {"topic": "A", "status": "no_change"},
            {"topic": "B", "status": "error", "error": "boom"},
        ]
        text = _build_weekly_text(results)
        self.assertIn("새로 추가되거나 갱신된 초안은 없습니다", text)
        self.assertIn("처리 실패: 1건 (B)", text)

    @patch.dict("os.environ", {}, clear=True)
    @patch("kms.slack.requests.post")
    def test_summary_skip_when_webhook_unset(self, mock_post):
        notify_weekly_summary([])
        mock_post.assert_not_called()

    @patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/x"})
    @patch("kms.slack.requests.post")
    def test_summary_posts_with_zero_changes(self, mock_post):
        mock_post.return_value.raise_for_status.return_value = None
        notify_weekly_summary([{"topic": "A", "status": "no_change"}])
        mock_post.assert_called_once()
        text = mock_post.call_args.kwargs["json"]["text"]
        self.assertIn("새로 추가되거나 갱신된 초안은 없습니다", text)


if __name__ == "__main__":
    unittest.main()
