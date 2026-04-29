import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import weekly_run
from kms import db


class TestWeeklyRunIsolation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self._orig_path = db.DB_PATH
        db.DB_PATH = Path(self._tmp.name)
        with db.connect():
            pass

    def tearDown(self):
        db.DB_PATH = self._orig_path
        Path(self._tmp.name).unlink(missing_ok=True)

    @patch("weekly_run.notify_weekly_summary")
    @patch("weekly_run.fetch_active_topics")
    @patch("weekly_run.run_pipeline")
    def test_one_failure_does_not_block_others(self, mock_run, mock_fetch, _mock_notify):
        mock_fetch.return_value = [
            {"topic": "A", "notion_page_id": "pA"},
            {"topic": "B", "notion_page_id": "pB"},
            {"topic": "C", "notion_page_id": "pC"},
        ]

        def side_effect(topic, **_):
            if topic == "B":
                raise RuntimeError("boom")
            return {"run_id": 1, "status": "drafted", "notion_url": f"u-{topic}"}

        mock_run.side_effect = side_effect

        summary = weekly_run.run_weekly()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["drafted"], 2)
        self.assertEqual(summary["error"], 1)
        # all 3 topics had pre-registered page mappings
        self.assertEqual(db.get_topic_page("A")["notion_page_id"], "pA")
        self.assertEqual(db.get_topic_page("B")["notion_page_id"], "pB")
        self.assertEqual(db.get_topic_page("C")["notion_page_id"], "pC")

    @patch("weekly_run.notify_weekly_summary")
    @patch("weekly_run.fetch_active_topics")
    @patch("weekly_run.run_pipeline")
    def test_status_aggregation(self, mock_run, mock_fetch, _mock_notify):
        mock_fetch.return_value = [
            {"topic": t, "notion_page_id": f"p{t}"} for t in "ABCD"
        ]
        statuses = {"A": "drafted", "B": "sources_only", "C": "skipped", "D": "no_change"}
        mock_run.side_effect = lambda topic, **_: {"run_id": 1, "status": statuses[topic]}

        summary = weekly_run.run_weekly()
        self.assertEqual(summary["drafted"], 1)
        self.assertEqual(summary["sources_only"], 1)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["no_change"], 1)
        self.assertEqual(summary["error"], 0)

    @patch("weekly_run.fetch_active_topics")
    def test_empty_topic_list(self, mock_fetch):
        mock_fetch.return_value = []
        summary = weekly_run.run_weekly()
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["results"], [])


if __name__ == "__main__":
    unittest.main()
