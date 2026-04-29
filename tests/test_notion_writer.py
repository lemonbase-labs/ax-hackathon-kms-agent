import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kms import db
from kms.notion_writer import (
    _read_multi_select,
    _read_source_field,
    _truncate_sources,
    _union_preserving_order,
    write_draft,
)


class TestHelpers(unittest.TestCase):
    def test_union_preserves_order_and_dedupes(self):
        self.assertEqual(
            _union_preserving_order(["a", "b"], ["b", "c"]),
            ["a", "b", "c"],
        )

    def test_union_strips_empty(self):
        self.assertEqual(
            _union_preserving_order(["a", "  "], [" b ", ""]),
            ["a", "b"],
        )

    def test_read_source_field_splits_lines(self):
        page = {
            "properties": {
                "Source": {
                    "rich_text": [{"plain_text": "https://a\nhttps://b\n"}]
                }
            }
        }
        self.assertEqual(
            _read_source_field(page), ["https://a", "https://b"]
        )

    def test_read_source_field_concatenates_chunks(self):
        page = {
            "properties": {
                "Source": {
                    "rich_text": [
                        {"plain_text": "https://a\nhttps://"},
                        {"plain_text": "b"},
                    ]
                }
            }
        }
        self.assertEqual(
            _read_source_field(page), ["https://a", "https://b"]
        )

    def test_read_multi_select(self):
        page = {
            "properties": {
                "키워드": {"multi_select": [{"name": "x"}, {"name": "y"}]}
            }
        }
        self.assertEqual(_read_multi_select(page, "키워드"), ["x", "y"])

    def test_truncate_sources_within_limit(self):
        out = _truncate_sources(["https://a", "https://b"])
        self.assertEqual(out, "https://a\nhttps://b")

    def test_truncate_sources_keeps_recent_when_overflow(self):
        # 800-char items: two fit (≈1601 chars w/ newline), three don't (≈2403)
        long = "x" * 800
        sources = [f"{long}-1", f"{long}-2", f"{long}-3"]
        out = _truncate_sources(sources)
        # most recent (-3, -2) should fit; -1 dropped
        self.assertIn(f"{long}-3", out)
        self.assertIn(f"{long}-2", out)
        self.assertNotIn(f"{long}-1", out)
        self.assertLessEqual(len(out), 1900)


class TestUpsertFlow(unittest.TestCase):
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

    @patch.dict("os.environ", {"NOTION_TOKEN": "x", "NOTION_DB_ID": "y"})
    @patch("kms.notion_writer.Client")
    def test_first_call_creates_page_and_registers(self, MockClient):
        notion = MockClient.return_value
        notion.databases.retrieve.return_value = {
            "data_sources": [{"id": "ds-1"}]
        }
        notion.pages.create.return_value = {
            "id": "page-abc",
            "url": "https://notion.so/page-abc",
        }

        url = write_draft(
            topic="성과관리",
            keywords=["evaluation"],
            sources=["https://a", "https://b"],
            draft="hello",
        )
        self.assertEqual(url, "https://notion.so/page-abc")
        # topic_pages registered
        row = db.get_topic_page("성과관리")
        self.assertIsNotNone(row)
        self.assertEqual(row["notion_page_id"], "page-abc")
        # only create called, not retrieve/update/delete
        notion.pages.create.assert_called_once()
        notion.pages.retrieve.assert_not_called()
        notion.pages.update.assert_not_called()

    @patch.dict("os.environ", {"NOTION_TOKEN": "x", "NOTION_DB_ID": "y"})
    @patch("kms.notion_writer.Client")
    def test_second_call_reuses_page_and_unions_sources(self, MockClient):
        notion = MockClient.return_value
        notion.databases.retrieve.return_value = {
            "data_sources": [{"id": "ds-1"}]
        }
        # seed: pretend first call already happened
        db.upsert_topic_page("성과관리", "page-abc")

        notion.pages.retrieve.return_value = {
            "id": "page-abc",
            "url": "https://notion.so/page-abc",
            "properties": {
                "Source": {
                    "rich_text": [{"plain_text": "https://a\nhttps://b"}]
                },
                "키워드": {"multi_select": [{"name": "evaluation"}]},
            },
        }
        notion.blocks.children.list.return_value = {
            "results": [{"id": "block-1"}, {"id": "block-2"}],
            "has_more": False,
        }

        url = write_draft(
            topic="성과관리",
            keywords=["evaluation", "review"],
            sources=["https://b", "https://c"],  # b is dup, c is new
            draft="updated draft",
        )
        self.assertEqual(url, "https://notion.so/page-abc")

        # no new page created
        notion.pages.create.assert_not_called()
        # update called once with merged Source containing a/b/c
        notion.pages.update.assert_called_once()
        args = notion.pages.update.call_args
        sources_text = args.kwargs["properties"]["Source"]["rich_text"][0]["text"]["content"]
        self.assertIn("https://a", sources_text)
        self.assertIn("https://b", sources_text)
        self.assertIn("https://c", sources_text)
        keywords = [
            kw["name"] for kw in args.kwargs["properties"]["키워드"]["multi_select"]
        ]
        self.assertEqual(keywords, ["evaluation", "review"])

        # body replaced: 2 blocks deleted, then appended with new draft
        self.assertEqual(notion.blocks.delete.call_count, 2)
        notion.blocks.children.append.assert_called_once()


if __name__ == "__main__":
    unittest.main()
