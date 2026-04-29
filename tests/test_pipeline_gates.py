import unittest

from kms.pipeline import decide_action

# Test fixtures (independent of runtime config.json).
SOURCE_THRESHOLD = 3
DRAFT_THRESHOLD = 4
DRAFT_BATCH = 3

GATES = {
    "source_threshold": SOURCE_THRESHOLD,
    "draft_threshold": DRAFT_THRESHOLD,
    "draft_batch": DRAFT_BATCH,
}


def s(score: int, url: str = "u") -> dict:
    return {"url": url, "score": score}


class TestDecideAction(unittest.TestCase):
    def test_below_source_threshold_dropped(self):
        scored = [s(SOURCE_THRESHOLD - 1, "a"), s(SOURCE_THRESHOLD, "b")]
        out = decide_action(scored, 0, 0, 0, **GATES)
        self.assertEqual([d["url"] for d in out["new_for_source"]], ["b"])
        self.assertEqual(out["new_for_draft"], [])

    def test_draft_threshold_subset_of_source(self):
        scored = [s(DRAFT_THRESHOLD, "x"), s(SOURCE_THRESHOLD, "y")]
        out = decide_action(scored, 0, 0, 0, **GATES)
        # x meets both, y meets only source
        self.assertEqual({d["url"] for d in out["new_for_source"]}, {"x", "y"})
        self.assertEqual([d["url"] for d in out["new_for_draft"]], ["x"])

    def test_first_run_draft_triggers_at_batch(self):
        # 3 new ≥4 → eligible_total=3, last_drafted=0, delta=3 → trigger
        scored = [s(DRAFT_THRESHOLD, f"u{i}") for i in range(3)]
        out = decide_action(scored, 0, 0, 0, **GATES)
        self.assertTrue(out["should_draft"])
        self.assertEqual(out["new_draft_eligible"], 3)

    def test_first_run_below_batch_no_draft(self):
        scored = [s(DRAFT_THRESHOLD, f"u{i}") for i in range(2)]
        out = decide_action(scored, 0, 0, 0, **GATES)
        self.assertFalse(out["should_draft"])
        self.assertEqual(out["new_draft_eligible"], 2)

    def test_existing_5_then_3_new_triggers(self):
        # 사용자 시나리오: 기존 5개 → 신규 3개 통과 → 누적 8 → delta=8-5=3 → 트리거
        scored = [s(DRAFT_THRESHOLD, f"u{i}") for i in range(3)]
        out = decide_action(
            scored,
            prev_source_count=5,
            prev_draft_eligible=5,
            prev_last_drafted=5,
            **GATES,
        )
        self.assertTrue(out["should_draft"])
        self.assertEqual(out["new_draft_eligible"], 8)
        self.assertEqual(out["delta_for_draft"], 3)

    def test_existing_5_then_2_new_no_trigger(self):
        scored = [s(DRAFT_THRESHOLD, f"u{i}") for i in range(2)]
        out = decide_action(
            scored,
            prev_source_count=5,
            prev_draft_eligible=5,
            prev_last_drafted=5,
            **GATES,
        )
        self.assertFalse(out["should_draft"])
        self.assertEqual(out["delta_for_draft"], 2)

    def test_after_draft_counter_resets_via_last_drafted(self):
        # 갱신 직후: last_drafted=eligible. 다음 회차에 신규 1개만 들어오면 트리거 X
        scored = [s(DRAFT_THRESHOLD, "new")]
        out = decide_action(
            scored,
            prev_source_count=8,
            prev_draft_eligible=8,
            prev_last_drafted=8,
            **GATES,
        )
        self.assertFalse(out["should_draft"])
        # 그 다음에 또 2개 → delta=11-8=3 → 트리거
        scored2 = [s(DRAFT_THRESHOLD, "n1"), s(DRAFT_THRESHOLD, "n2")]
        out2 = decide_action(scored2, 9, 9, 8, **GATES)
        self.assertTrue(out2["should_draft"])

    def test_only_source_no_draft_eligible(self):
        # score≥3 들어왔지만 ≥4는 0 → Source만 append, draft 안 함
        scored = [s(SOURCE_THRESHOLD, "a"), s(SOURCE_THRESHOLD, "b")]
        out = decide_action(scored, 0, 0, 0, **GATES)
        self.assertEqual(len(out["new_for_source"]), 2)
        self.assertEqual(out["new_for_draft"], [])
        self.assertFalse(out["should_draft"])

    def test_custom_thresholds_override(self):
        # 같은 입력이라도 게이트 값에 따라 결과가 달라져야 함
        scored = [s(5, "a"), s(7, "b")]
        loose = decide_action(
            scored, 0, 0, 0, source_threshold=3, draft_threshold=4, draft_batch=2
        )
        strict = decide_action(
            scored, 0, 0, 0, source_threshold=6, draft_threshold=8, draft_batch=2
        )
        self.assertEqual(len(loose["new_for_source"]), 2)
        self.assertEqual(len(strict["new_for_source"]), 1)
        self.assertEqual(len(strict["new_for_draft"]), 0)


if __name__ == "__main__":
    unittest.main()
