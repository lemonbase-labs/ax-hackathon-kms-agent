import tempfile
import unittest
from pathlib import Path

from kms import db, seen_store


class TestSeenStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self._orig_path = db.DB_PATH
        db.DB_PATH = Path(self._tmp.name)
        # initialize schema
        with db.connect():
            pass

    def tearDown(self):
        db.DB_PATH = self._orig_path
        Path(self._tmp.name).unlink(missing_ok=True)

    def test_insert_discovered_idempotent(self):
        first = seen_store.insert_discovered(
            "성과관리", "https://example.com/a", "Title", "rss:hbr", run_id=1
        )
        self.assertTrue(first)
        # same canonical → no insert
        again = seen_store.insert_discovered(
            "성과관리", "https://www.example.com/a/?utm_source=x", "Title", "rss:hbr", run_id=2
        )
        self.assertFalse(again)

    def test_filter_new_dedupes_against_existing_and_within_batch(self):
        seen_store.insert_discovered(
            "성과관리", "https://example.com/a", "T", "rss", run_id=1
        )
        candidates = [
            {"url": "https://www.example.com/a", "title": "dup-existing"},
            {"url": "https://example.com/b", "title": "new-1"},
            {"url": "https://example.com/b?utm_source=x", "title": "dup-in-batch"},
            {"url": "https://example.com/c", "title": "new-2"},
        ]
        out = seen_store.filter_new("성과관리", candidates)
        urls = [c["url"] for c in out]
        self.assertEqual(urls, ["https://example.com/b", "https://example.com/c"])

    def test_filter_new_isolates_topic(self):
        seen_store.insert_discovered(
            "topicA", "https://example.com/a", None, None, run_id=1
        )
        out = seen_store.filter_new(
            "topicB", [{"url": "https://example.com/a"}]
        )
        self.assertEqual(len(out), 1)

    def test_mark_status_with_score(self):
        seen_store.insert_discovered(
            "t", "https://example.com/a", None, None, run_id=1
        )
        seen_store.mark_status("t", "https://example.com/a", "scored", score=5)
        rows = seen_store.list_by_min_score("t", 4)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["score"], 5)
        self.assertEqual(rows[0]["status"], "scored")

    def test_list_by_min_score_filters_below(self):
        for url, score in [
            ("https://example.com/a", 2),
            ("https://example.com/b", 3),
            ("https://example.com/c", 4),
        ]:
            seen_store.insert_discovered("t", url, None, None, run_id=1)
            seen_store.mark_status("t", url, "scored", score=score)
        urls_3 = [r["url_original"] for r in seen_store.list_by_min_score("t", 3)]
        urls_4 = [r["url_original"] for r in seen_store.list_by_min_score("t", 4)]
        self.assertEqual(set(urls_3), {"https://example.com/b", "https://example.com/c"})
        self.assertEqual(urls_4, ["https://example.com/c"])

    def test_attach_notion_page(self):
        seen_store.insert_discovered(
            "t", "https://example.com/a", None, None, run_id=1
        )
        seen_store.attach_notion_page("t", "https://example.com/a", "page-123")
        rows = seen_store.list_by_min_score("t", -1)
        # no score set → not returned by list_by_min_score; verify directly
        with db.connect() as c:
            row = c.execute(
                "SELECT notion_page_id FROM seen_sources WHERE topic='t'"
            ).fetchone()
        self.assertEqual(row["notion_page_id"], "page-123")
        self.assertEqual(rows, [])  # no score yet


if __name__ == "__main__":
    unittest.main()
