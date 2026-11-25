"""check_decision_answer: the bid-decision answer contract, checked on the finished answer instead of trusted."""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "skills/create-best-proposal/scripts"))
import check_decision_answer as check  # noqa: E402

GOOD_INTAKE = """BID_DECISION: intake-incomplete
STATUS: DECISION_MEMO_ONLY
REQUIRED_INPUTS: similar-project records for the last 5 years; contract amounts; proof of completion

No proposal body was written.
"""
GOOD_CONDITIONAL = """BID_DECISION: conditional-bid
CONDITION: obtain a partner certificate | owner: Kim | deadline: 2099-11-30T17:00:00+09:00 | accepted: yes
CONDITION: confirm staffing | owner: Lee | deadline: 2099-12-01T09:00Z | accepted: yes
"""


class DecisionAnswerTests(unittest.TestCase):
    def problems(self, text, material="unknown"):
        return check.check(text, material)

    def test_the_contract_example_answers_pass(self):
        self.assertEqual(self.problems(GOOD_INTAKE, "absent"), [])
        self.assertEqual(self.problems(GOOD_CONDITIONAL, "present"), [])
        self.assertEqual(self.problems("BID_DECISION: bid\n"), [])
        self.assertEqual(self.problems("BID_DECISION: no-bid\nSTATUS: DECISION_MEMO_ONLY\n"), [])

    def test_markdown_decoration_around_the_lines_is_tolerated(self):
        text = "**BID_DECISION: `intake-incomplete`**\n- **STATUS:** `DECISION_MEMO_ONLY`\n- REQUIRED_INPUTS: records\n"
        self.assertEqual(self.problems(text, "absent"), [])

    def test_missing_or_unknown_decision_line_fails(self):
        self.assertTrue(self.problems("입찰 판단: 조건부 입찰입니다."))
        self.assertTrue(self.problems("# Title\nBID_DECISION: intake-incomplete\n"), "must be the FIRST non-empty line")
        self.assertIn("not one of", self.problems("BID_DECISION: maybe\n")[0])
        self.assertTrue(self.problems(""))

    def test_missing_label_fails_for_memo_decisions(self):
        """The failure seen in manual runs: the right conclusion, no status label."""
        text = "BID_DECISION: intake-incomplete\nREQUIRED_INPUTS: records\n"
        self.assertIn("DECISION_MEMO_ONLY", self.problems(text)[0])
        self.assertTrue(self.problems("BID_DECISION: no-bid\n"))

    def test_label_on_a_bid_or_conditional_bid_fails(self):
        self.assertTrue(self.problems("BID_DECISION: bid\nSTATUS: DECISION_MEMO_ONLY\n"))
        self.assertTrue(self.problems(GOOD_CONDITIONAL + "STATUS: DECISION_MEMO_ONLY\n"))

    def test_no_bidder_material_forces_intake_incomplete(self):
        """The failure seen in manual runs: a conditional bid with no evidence about the bidder."""
        self.assertIn("no bidder material", self.problems(GOOD_CONDITIONAL, "absent")[0])
        self.assertTrue(self.problems("BID_DECISION: bid\n", "absent"))
        self.assertTrue(self.problems("BID_DECISION: no-bid\nSTATUS: DECISION_MEMO_ONLY\n", "absent"))
        self.assertEqual(self.problems(GOOD_CONDITIONAL, "unknown"), [], "without the flag the rule does not apply")

    def test_intake_incomplete_must_list_inputs_and_invent_nothing(self):
        self.assertTrue(self.problems("BID_DECISION: intake-incomplete\nSTATUS: DECISION_MEMO_ONLY\n"))
        invented = GOOD_INTAKE + "CONDITION: get records | owner: Kim | deadline: 2099-01-01T00:00Z | accepted: yes\n"
        self.assertTrue(any("invented" in item for item in self.problems(invented)))

    def test_conditional_bid_needs_owner_iso_deadline_and_acceptance_per_condition(self):
        base = "BID_DECISION: conditional-bid\nCONDITION: x | owner: {o} | deadline: {d} | accepted: {a}\n"
        ok = dict(o="Kim", d="2099-11-30T17:00:00+09:00", a="yes")
        self.assertEqual(self.problems(base.format(**ok)), [])
        for key, bad in (("o", "TBD"), ("o", "미정"), ("d", "2099-11-30"), ("d", "next week"),
                         ("d", "2099-11-30T17:00:00"), ("a", "no"), ("a", "pending")):
            with self.subTest(key=key, bad=bad):
                self.assertTrue(self.problems(base.format(**{**ok, key: bad})))
        self.assertTrue(self.problems("BID_DECISION: conditional-bid\n"), "no CONDITION line at all")

    def test_one_bad_condition_among_good_ones_is_reported(self):
        text = GOOD_CONDITIONAL + "CONDITION: z | owner: TBD | deadline: 2099-11-30T17:00Z | accepted: yes\n"
        self.assertEqual(len(self.problems(text)), 1)
        self.assertIn("condition 3", self.problems(text)[0])

    def test_cli_exit_codes(self):
        def run(content, *extra):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "answer.md"
                if content is not None:
                    path.write_text(content, encoding="utf-8")
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    code = check.main([str(path), *extra])
                return code, out.getvalue()
        code, out = run(GOOD_INTAKE, "--bidder-material", "absent")
        self.assertEqual((code, "DECISION-ANSWER: OK" in out), (0, True))
        code, out = run(GOOD_CONDITIONAL, "--bidder-material", "absent")
        self.assertEqual((code, "DECISION-ANSWER: PROBLEMS" in out), (1, True))
        self.assertEqual(run(None)[0], 2)


if __name__ == "__main__":
    unittest.main()
