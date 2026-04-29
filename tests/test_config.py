"""Unit tests for kms._config (file-based threshold config)."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from kms import _config


class TestValidate(unittest.TestCase):
    def test_valid_config_passes(self):
        out = _config._validate({
            "source_threshold": 3,
            "draft_threshold": 4,
            "draft_batch": 3,
        })
        self.assertEqual(out["source_threshold"], 3)
        self.assertEqual(out["draft_threshold"], 4)
        self.assertEqual(out["draft_batch"], 3)

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError) as cm:
            _config._validate({"source_threshold": 3, "draft_threshold": 4})
        self.assertIn("draft_batch", str(cm.exception))

    def test_non_integer_rejected(self):
        with self.assertRaises(ValueError) as cm:
            _config._validate({
                "source_threshold": 3.5,
                "draft_threshold": 4,
                "draft_batch": 3,
            })
        self.assertIn("integer", str(cm.exception))

    def test_bool_rejected_even_though_python_treats_as_int(self):
        # True == 1 in Python, but we don't want to silently accept booleans.
        with self.assertRaises(ValueError):
            _config._validate({
                "source_threshold": True,
                "draft_threshold": 4,
                "draft_batch": 3,
            })

    def test_out_of_range_rejected(self):
        with self.assertRaises(ValueError) as cm:
            _config._validate({
                "source_threshold": 0,
                "draft_threshold": 4,
                "draft_batch": 3,
            })
        self.assertIn("[1, 20]", str(cm.exception))

    def test_source_greater_than_draft_rejected(self):
        with self.assertRaises(ValueError) as cm:
            _config._validate({
                "source_threshold": 5,
                "draft_threshold": 4,
                "draft_batch": 3,
            })
        self.assertIn("≤", str(cm.exception))

    def test_source_equal_to_draft_allowed(self):
        # source == draft is the current default; must remain valid.
        _config._validate({
            "source_threshold": 3,
            "draft_threshold": 3,
            "draft_batch": 3,
        })

    def test_draft_batch_must_be_positive(self):
        with self.assertRaises(ValueError):
            _config._validate({
                "source_threshold": 3,
                "draft_threshold": 4,
                "draft_batch": 0,
            })

    def test_non_dict_rejected(self):
        with self.assertRaises(ValueError):
            _config._validate([1, 2, 3])  # type: ignore[arg-type]


class TestLoadSave(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("/tmp/_config_test_kms.json")
        self.tmp.write_text(
            json.dumps({"source_threshold": 3, "draft_threshold": 4, "draft_batch": 3}),
            encoding="utf-8",
        )
        self._patcher = patch.object(_config, "CONFIG_FILE", self.tmp)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        if self.tmp.exists():
            self.tmp.unlink()

    def test_load_returns_validated_config(self):
        cfg = _config.load()
        self.assertEqual(cfg["source_threshold"], 3)
        self.assertEqual(cfg["draft_threshold"], 4)
        self.assertEqual(cfg["draft_batch"], 3)

    def test_load_raw_returns_file_text(self):
        text = _config.load_raw()
        self.assertIn("source_threshold", text)

    def test_save_validates_and_writes(self):
        new = {"source_threshold": 5, "draft_threshold": 7, "draft_batch": 2}
        _config.save(new)
        self.assertEqual(_config.load(), new)

    def test_save_rejects_invalid_and_keeps_old_content(self):
        original = self.tmp.read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            _config.save({"source_threshold": 99, "draft_threshold": 4, "draft_batch": 3})
        self.assertEqual(self.tmp.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
