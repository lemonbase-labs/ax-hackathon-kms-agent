import unittest

from kms.url_canonical import canonicalize


class TestCanonicalize(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(canonicalize(""), "")
        self.assertEqual(canonicalize("   "), "")

    def test_http_to_https(self):
        self.assertEqual(
            canonicalize("http://example.com/foo"),
            "https://example.com/foo",
        )

    def test_host_lowercase_and_www_strip(self):
        self.assertEqual(
            canonicalize("https://WWW.Example.COM/foo"),
            "https://example.com/foo",
        )

    def test_drop_utm_and_trackers(self):
        self.assertEqual(
            canonicalize("https://example.com/a?utm_source=x&utm_medium=y&id=42"),
            "https://example.com/a?id=42",
        )
        self.assertEqual(
            canonicalize("https://example.com/a?gclid=abc&fbclid=xyz"),
            "https://example.com/a",
        )

    def test_drop_fragment(self):
        self.assertEqual(
            canonicalize("https://example.com/a#section"),
            "https://example.com/a",
        )

    def test_strip_trailing_slash_except_root(self):
        self.assertEqual(
            canonicalize("https://example.com/a/"),
            "https://example.com/a",
        )
        self.assertEqual(
            canonicalize("https://example.com/"),
            "https://example.com/",
        )

    def test_path_case_preserved(self):
        # path can be case-sensitive (e.g. some CDNs); only host is normalized
        self.assertEqual(
            canonicalize("https://example.com/CaseSensitive"),
            "https://example.com/CaseSensitive",
        )

    def test_idempotent(self):
        url = "https://example.com/a?id=42"
        self.assertEqual(canonicalize(canonicalize(url)), canonicalize(url))


if __name__ == "__main__":
    unittest.main()
