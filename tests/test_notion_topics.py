import unittest
from unittest.mock import MagicMock, patch

from kms.notion_topics import fetch_active_topics


def _row(page_id: str, title: str, status: str | None = None) -> dict:
    props: dict = {
        "주제": {"title": [{"plain_text": title}] if title else []}
    }
    if status is not None:
        props["Status"] = {"status": {"name": status}}
    return {"id": page_id, "properties": props}


class TestFetchActiveTopics(unittest.TestCase):
    @patch.dict("os.environ", {"NOTION_TOKEN": "x", "NOTION_DB_ID": "y"})
    @patch("kms.notion_topics.Client")
    def test_filters_inactive_and_empty(self, MockClient):
        notion = MockClient.return_value
        notion.databases.retrieve.return_value = {"data_sources": [{"id": "ds-1"}]}
        notion.data_sources.query.return_value = {
            "results": [
                _row("p1", "성과관리", "Draft"),
                _row("p2", "수습평가", None),  # no status field
                _row("p3", "", "Draft"),  # empty title
                _row("p4", "발행됨", "Approved"),
                _row("p5", "거절됨", "Rejected"),
                _row("p6", "리뷰중", "In Review"),
            ],
            "has_more": False,
        }
        out = fetch_active_topics()
        self.assertEqual(
            [(r["topic"], r["notion_page_id"]) for r in out],
            [("성과관리", "p1"), ("수습평가", "p2"), ("리뷰중", "p6")],
        )

    @patch.dict("os.environ", {"NOTION_TOKEN": "x", "NOTION_DB_ID": "y"})
    @patch("kms.notion_topics.Client")
    def test_pagination(self, MockClient):
        notion = MockClient.return_value
        notion.databases.retrieve.return_value = {"data_sources": [{"id": "ds-1"}]}
        notion.data_sources.query.side_effect = [
            {
                "results": [_row("p1", "A", "Draft")],
                "has_more": True,
                "next_cursor": "cur1",
            },
            {
                "results": [_row("p2", "B", "Draft")],
                "has_more": False,
            },
        ]
        out = fetch_active_topics()
        self.assertEqual([r["topic"] for r in out], ["A", "B"])
        # second call uses start_cursor
        second_call = notion.data_sources.query.call_args_list[1]
        self.assertEqual(second_call.kwargs.get("start_cursor"), "cur1")


if __name__ == "__main__":
    unittest.main()
