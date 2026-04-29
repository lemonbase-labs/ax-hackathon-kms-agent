import json
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from kms import filter as flt


def _llm_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _v2(total: int, decision: str = "synthesis_candidate") -> dict:
    return {
        "scores": {
            "topic_fit": 1 if total > 0 else 0,
            "authority_expertise": 1 if total >= 2 else 0,
            "recency_uniqueness": 1 if total >= 3 else 0,
            "demand": 1 if total >= 4 else 0,
            "practical_fit": 1 if total >= 5 else 0,
        },
        "total": total,
        "gate_passed": total > 0,
        "matched_topic": "성과평가" if total > 0 else None,
        "decision": decision,
        "reasons": {k: "ok" for k in
                    ["topic_fit", "authority_expertise", "recency_uniqueness", "demand", "practical_fit"]},
    }


def _by_url_responder(url_to_response: dict, hook=None):
    """Make a side_effect that routes responses by the user-message url field.

    Optional `hook(url)` runs inside the call (before returning) — useful for
    asserting concurrent in-flight execution.
    """
    def fn(model, messages, **kw):
        payload = json.loads(messages[1]["content"])
        if hook is not None:
            hook(payload["url"])
        if payload["url"] == "__raise__":
            raise RuntimeError("simulated transport error")
        body = url_to_response[payload["url"]]
        return _llm_response("garbage" if body is None else json.dumps(body))
    return fn


class TestParseJson(unittest.TestCase):
    def test_extracts_first_object_with_trailing_data(self):
        # Reproduces the original "Extra data: line 22 column 4 (char 843)" failure mode:
        # LLM returns multiple JSON objects concatenated.
        text = json.dumps(_v2(5)) + "\n" + json.dumps(_v2(3))
        out = flt._parse_json(text)
        self.assertEqual(out["total"], 5)

    def test_strips_code_fence_prefix(self):
        text = "```json\n" + json.dumps(_v2(4)) + "\n```"
        out = flt._parse_json(text)
        self.assertEqual(out["total"], 4)

    def test_no_object_raises(self):
        with self.assertRaises(ValueError):
            flt._parse_json("no json here")


class TestScoreAndSelect(unittest.TestCase):
    def setUp(self):
        self._patches = [
            patch("kms.filter.load_prompt", return_value="SYS"),
            patch("kms.filter.model", return_value="m"),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def _run(self, docs, url_to_response, hook=None):
        client_mock = MagicMock()
        client_mock.chat.completions.create.side_effect = _by_url_responder(
            url_to_response, hook=hook
        )
        with patch("kms.filter.client", return_value=client_mock):
            return flt.score_and_select("성과평가", docs, top_k=10)

    def test_maps_total_to_score_and_sorts_desc(self):
        docs = [
            {"url": "u-a", "text": "a"},
            {"url": "u-b", "text": "b"},
            {"url": "u-c", "text": "c"},
        ]
        out = self._run(docs, {"u-a": _v2(3), "u-b": _v2(5), "u-c": _v2(4)})
        self.assertEqual([d["score"] for d in out], [5, 4, 3])
        self.assertEqual([d["url"] for d in out], ["u-b", "u-c", "u-a"])
        self.assertEqual(out[0]["score_detail"]["decision"], "synthesis_candidate")

    def test_topic_fit_zero_yields_score_zero(self):
        docs = [{"url": "u-x", "text": "off-topic"}]
        out = self._run(docs, {"u-x": _v2(0, decision="exclude")})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["score"], 0)
        self.assertIsNone(out[0]["score_detail"]["matched_topic"])

    def test_unparseable_response_skipped(self):
        docs = [{"url": "u-a", "text": "a"}, {"url": "u-b", "text": "b"}]
        out = self._run(docs, {"u-a": None, "u-b": _v2(4)})  # None → garbage response
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["url"], "u-b")

    def test_transport_exception_skipped(self):
        docs = [{"url": "__raise__", "text": "a"}, {"url": "u-b", "text": "b"}]
        out = self._run(docs, {"u-b": _v2(4)})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["url"], "u-b")

    def test_top_k_caps_results(self):
        docs = [{"url": f"u-{i}", "text": "x"} for i in range(4)]
        out = self._run(
            docs,
            {f"u-{i}": _v2(t) for i, t in enumerate([2, 5, 3, 4])},
        )
        # 위 셋업으로 top_k 미지정시 전부 반환되지만, 별도 호출로 cap 검증
        client_mock = MagicMock()
        client_mock.chat.completions.create.side_effect = _by_url_responder(
            {f"u-{i}": _v2(t) for i, t in enumerate([2, 5, 3, 4])}
        )
        with patch("kms.filter.client", return_value=client_mock):
            capped = flt.score_and_select("t", docs, top_k=2)
        self.assertEqual([d["score"] for d in capped], [5, 4])

    def test_runs_in_parallel(self):
        # Latch verifies multiple calls are in-flight simultaneously.
        n_docs = 4
        in_flight = 0
        peak = 0
        lock = threading.Lock()
        latch = threading.Event()

        def hook(url):
            nonlocal in_flight, peak
            with lock:
                in_flight += 1
                peak = max(peak, in_flight)
                if in_flight >= n_docs:
                    latch.set()
            # Block until all docs have entered — proves concurrency.
            latch.wait(timeout=2.0)
            with lock:
                in_flight -= 1

        docs = [{"url": f"u-{i}", "text": "x"} for i in range(n_docs)]
        responses = {f"u-{i}": _v2(3) for i in range(n_docs)}

        t0 = time.monotonic()
        out = self._run(docs, responses, hook=hook)
        elapsed = time.monotonic() - t0

        self.assertEqual(len(out), n_docs)
        self.assertEqual(peak, n_docs, f"expected {n_docs} concurrent calls, got peak={peak}")
        # Sanity: serial would take > n_docs * latch_wait; parallel finishes in ~one wait.
        self.assertLess(elapsed, 2.0 * 1.5)


if __name__ == "__main__":
    unittest.main()
