"""Unit tests for kms._feeds (file-based feed whitelist)."""
import unittest
from pathlib import Path
from unittest.mock import patch

from kms import _feeds


class TestParse(unittest.TestCase):
    def test_basic_parse(self):
        content = "hbr https://feeds.feedburner.com/harvardbusiness\n"
        feeds, errs = _feeds._parse(content)
        self.assertEqual(feeds, {"hbr": "https://feeds.feedburner.com/harvardbusiness"})
        self.assertEqual(errs, [])

    def test_comments_and_blank_lines_skipped(self):
        content = "\n# comment\n\nhbr https://example.com/feed\n# bersin https://x\n"
        feeds, errs = _feeds._parse(content)
        self.assertEqual(feeds, {"hbr": "https://example.com/feed"})
        self.assertEqual(errs, [])

    def test_extra_whitespace_in_url_stripped(self):
        content = "hbr   https://example.com/feed   \n"
        feeds, _ = _feeds._parse(content)
        self.assertEqual(feeds["hbr"], "https://example.com/feed")

    def test_missing_url_is_error(self):
        content = "hbr\n"
        _, errs = _feeds._parse(content)
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], 1)

    def test_invalid_url_scheme_is_error(self):
        content = "hbr ftp://example.com/feed\n"
        _, errs = _feeds._parse(content)
        self.assertEqual(len(errs), 1)
        self.assertIn("http(s)", errs[0][1])

    def test_duplicate_name_is_error(self):
        content = "hbr https://a.com\nhbr https://b.com\n"
        _, errs = _feeds._parse(content)
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], 2)
        self.assertIn("duplicate", errs[0][1])

    def test_multiple_errors_collected(self):
        content = "bad\nhbr ftp://x\nhbr https://a.com\nhbr https://b.com\n"
        _, errs = _feeds._parse(content)
        # line 1: missing url, line 2: bad scheme, line 4: duplicate (line 3 valid)
        self.assertEqual(len(errs), 3)


class TestLoadSave(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("/tmp/_feeds_test_kms.txt")
        self.tmp.write_text("a https://a.com\nb https://b.com\n", encoding="utf-8")
        self._patcher = patch.object(_feeds, "FEEDS_FILE", self.tmp)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        if self.tmp.exists():
            self.tmp.unlink()

    def test_load_returns_enabled_only(self):
        self.tmp.write_text(
            "a https://a.com\n# b https://b.com\nc https://c.com\n",
            encoding="utf-8",
        )
        feeds = _feeds.load()
        self.assertEqual(feeds, {"a": "https://a.com", "c": "https://c.com"})

    def test_load_raw_returns_full_text(self):
        text = "# header\na https://a.com\n"
        self.tmp.write_text(text, encoding="utf-8")
        self.assertEqual(_feeds.load_raw(), text)

    def test_save_validates_and_writes(self):
        new = "x https://x.com\ny https://y.com\n"
        _feeds.save(new)
        self.assertEqual(self.tmp.read_text(encoding="utf-8"), new)
        self.assertEqual(_feeds.load(), {"x": "https://x.com", "y": "https://y.com"})

    def test_save_rejects_invalid_and_keeps_old_content(self):
        original = self.tmp.read_text(encoding="utf-8")
        with self.assertRaises(ValueError) as cm:
            _feeds.save("bad\n")
        self.assertIn("line 1", str(cm.exception))
        self.assertEqual(self.tmp.read_text(encoding="utf-8"), original)

    def test_save_rejects_duplicate(self):
        with self.assertRaises(ValueError) as cm:
            _feeds.save("a https://a.com\na https://a2.com\n")
        self.assertIn("duplicate", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
