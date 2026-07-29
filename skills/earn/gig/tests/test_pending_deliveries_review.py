import json
import os
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
VERIFY_SCRIPT = SKILL_DIR / "scripts" / "gig_selfimprove_verify.sh"
GIG_PASS = SKILL_DIR / "gig_pass.sh"
RUNBOOK = SKILL_DIR / "GIG_PASS_RUNBOOK.md"


def _step_prompt_line(source: str, label: str) -> str:
    """The line that carries a step's prompt, whatever the invoking function is called.

    X18 renamed the five EDF-selected call sites from step() to lane_step() so a failing
    lane stops cancelling the lanes after it. These assertions are about the PROMPT TEXT,
    not about which wrapper delivers it, so they match either spelling -- otherwise a
    prompt-content guard silently turns into a function-name guard and stops protecting
    the phrases it was written for.
    """
    for line in source.splitlines():
        if line.startswith(f'step "{label}"') or line.startswith(f'lane_step "{label}"'):
            return line
    raise AssertionError(f"no prompt line found for step {label}")


class PendingDeliveriesReviewTest(unittest.TestCase):
    def run_verifier(self, temp_home, poll_control=None):
        gig_dir = Path(temp_home) / "gig"
        gig_dir.mkdir(exist_ok=True)
        if poll_control is not None:
            evidence_dir = gig_dir / "evidence" / f"gig-pass-{poll_control['pass_id']}"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "poll-control.json").write_text(
                json.dumps(poll_control) + "\n",
                encoding="utf-8",
            )
            (gig_dir / ".last-pass").write_text(
                json.dumps(
                    {
                        "ts": int(time.time()),
                        "driver": "gig_pass.sh",
                        "status": "success",
                        "pass_id": poll_control["pass_id"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        env = os.environ.copy()
        env["HOME"] = temp_home
        subprocess.run(
            ["bash", str(VERIFY_SCRIPT)],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(
            (gig_dir / ".selfimprove-todo.json").read_text(encoding="utf-8")
        )

    def test_selfimprove_no_change_is_not_missing(self):
        poll_control = {
            "version": 1,
            "pass_id": "no-change-pass",
            "outcome": "no_change",
            "model_calls": 0,
            "model_call_labels": [],
        }
        with tempfile.TemporaryDirectory() as temp_home:
            output = self.run_verifier(temp_home, poll_control)

        self.assertEqual(output["latest_poll_control"], poll_control)
        self.assertEqual(output["missing"], [])
        self.assertEqual(output["verification_mode"], "normal_noop")

    def test_material_pass_still_requires_self_improvement_evidence(self):
        poll_control = {
            "version": 1,
            "pass_id": "material-pass",
            "outcome": "material_event_handled",
            "model_calls": 1,
            "model_call_labels": ["gig-INQUIRY_REPLY"],
        }
        with tempfile.TemporaryDirectory() as temp_home:
            output = self.run_verifier(temp_home, poll_control)

        self.assertEqual(output["latest_poll_control"], poll_control)
        self.assertEqual(output["verification_mode"], "material_or_improve")
        self.assertEqual(
            output["missing"],
            [
                "self_check",
                "scouted_playbook",
                "funnel",
                "applied_or_nurtured",
                "listing_work",
                "apply_volume",
            ],
        )

    def test_stale_no_change_pass_fails_closed(self):
        poll_control = {
            "version": 1,
            "pass_id": "stale-pass",
            "outcome": "no_change",
            "model_calls": 0,
            "model_call_labels": [],
        }
        with tempfile.TemporaryDirectory() as temp_home:
            gig_dir = Path(temp_home) / "gig"
            self.run_verifier(temp_home, poll_control)
            poll_path = (
                gig_dir
                / "evidence"
                / "gig-pass-stale-pass"
                / "poll-control.json"
            )
            stale = time.time() - 5401
            os.utime(poll_path, (stale, stale))
            output = self.run_verifier(temp_home)

        self.assertEqual(output["latest_poll_control"], {})
        self.assertEqual(output["poll_control_diagnostic"]["kind"], "invalid_contract")
        self.assertEqual(output["verification_mode"], "material_or_improve")
        self.assertNotEqual(output["missing"], [])

    def test_stale_last_pass_timestamp_fails_closed_even_when_file_is_fresh(self):
        poll_control = {
            "version": 1,
            "pass_id": "stale-authoritative-pass",
            "outcome": "no_change",
            "model_calls": 0,
            "model_call_labels": [],
        }
        with tempfile.TemporaryDirectory() as temp_home:
            gig_dir = Path(temp_home) / "gig"
            self.run_verifier(temp_home, poll_control)
            last_pass_path = gig_dir / ".last-pass"
            last_pass = json.loads(last_pass_path.read_text(encoding="utf-8"))
            last_pass["ts"] = int(time.time()) - 5401
            last_pass_path.write_text(
                json.dumps(last_pass) + "\n",
                encoding="utf-8",
            )
            output = self.run_verifier(temp_home)

        self.assertEqual(output["latest_poll_control"], {})
        self.assertEqual(
            output["poll_control_diagnostic"]["kind"],
            "invalid_last_pass_contract",
        )
        self.assertEqual(output["verification_mode"], "material_or_improve")
        self.assertNotEqual(output["missing"], [])

    def test_non_integer_poll_control_version_fails_closed(self):
        for malformed_version in (True, 1.0):
            with self.subTest(version=malformed_version):
                poll_control = {
                    "version": malformed_version,
                    "pass_id": f"malformed-version-{type(malformed_version).__name__}",
                    "outcome": "no_change",
                    "model_calls": 0,
                    "model_call_labels": [],
                }
                with tempfile.TemporaryDirectory() as temp_home:
                    output = self.run_verifier(temp_home, poll_control)

                self.assertEqual(output["latest_poll_control"], {})
                self.assertEqual(
                    output["poll_control_diagnostic"]["kind"],
                    "invalid_contract",
                )
                self.assertEqual(
                    output["verification_mode"],
                    "material_or_improve",
                )
                self.assertNotEqual(output["missing"], [])

    def test_malformed_concatenated_rows_are_skipped_and_reported(self):
        now = int(time.time())
        valid_rows = [
            {"requestId": f"valid-{index}", "status": "applied", "ts": now - index}
            for index in range(2)
        ]
        # The literal backslash-n is the production failure shape: two JSON
        # objects were concatenated into one physical JSONL line.
        malformed = '{"requestId":"bad-a","status":"applied","ts":%d}\\n{"requestId":"bad-b","status":"applied","ts":%d}\n' % (now, now)
        with tempfile.TemporaryDirectory() as temp_home:
            gig_dir = Path(temp_home) / "gig"
            gig_dir.mkdir()
            applied = gig_dir / "applied.jsonl"
            applied.write_text("".join(json.dumps(row) + "\n" for row in valid_rows) + malformed, encoding="utf-8")
            before = applied.read_bytes()
            env = os.environ.copy()
            env["HOME"] = temp_home
            completed = subprocess.run(["bash", str(VERIFY_SCRIPT)], env=env, check=True, capture_output=True, text=True)
            output = json.loads((gig_dir / ".selfimprove-todo.json").read_text(encoding="utf-8"))
            audit = json.loads((gig_dir / "selfimprove-audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            after = applied.read_bytes()

        self.assertEqual(after, before)
        diagnostics = output["ledger_diagnostics"]["applied.jsonl"]
        self.assertEqual(diagnostics["malformed_count"], 1)
        self.assertEqual(diagnostics["details"][0]["line"], 3)
        self.assertEqual(diagnostics["details"][0]["kind"], "invalid_json")
        self.assertIn("Extra data", diagnostics["details"][0]["detail"])
        self.assertFalse(output["evidence"]["apply_volume"])
        self.assertEqual(audit["ledger_diagnostics"], output["ledger_diagnostics"])
        stdout = json.loads(completed.stdout.strip())
        self.assertEqual(stdout["ledger_diagnostics"], output["ledger_diagnostics"])

    def test_all_pending_deliveries_are_written_without_threshold_filtering(self):
        rows = [
            {
                "requestId": "near",
                "category": "writing",
                "price_jpy": 12000,
                "status": "applied",
                "ts": int(datetime(2026, 7, 21, 12, tzinfo=timezone.utc).timestamp()),
                "delivery_date": "2026-07-23",
            },
            {
                "requestId": "far",
                "category": "development",
                "price_jpy": 65000,
                "status": "delivered_pending",
                "ts": int(datetime(2026, 7, 21, 12, tzinfo=timezone.utc).timestamp()),
                "delivery_date": "2026-09-10",
            },
            {
                "requestId": "jst-boundary",
                "category": "design",
                "price_jpy": 30000,
                "status": "applied",
                "ts": int(datetime(2026, 7, 21, 15, 30, tzinfo=timezone.utc).timestamp()),
                "delivery_date": "2026-07-23",
            },
            {
                "requestId": "closed",
                "category": "translation",
                "price_jpy": 8000,
                "status": "rejected",
                "ts": int(datetime(2026, 7, 21, 12, tzinfo=timezone.utc).timestamp()),
                "delivery_date": "2026-07-22",
            },
        ]
        with tempfile.TemporaryDirectory() as temp_home:
            gig_dir = Path(temp_home) / "gig"
            gig_dir.mkdir()
            fixture = "".join(json.dumps(row) + "\n" for row in rows[:2])
            fixture += "null\n[]\n42\n"
            fixture += "".join(json.dumps(row) + "\n" for row in rows[2:])
            (gig_dir / "applied.jsonl").write_text(fixture, encoding="utf-8")
            env = os.environ.copy()
            env["HOME"] = temp_home
            subprocess.run(["bash", str(VERIFY_SCRIPT)], env=env, check=True, capture_output=True, text=True)
            output = json.loads((gig_dir / ".selfimprove-todo.json").read_text(encoding="utf-8"))

        reviews = output["pending_deliveries_review"]
        self.assertEqual([review["requestId"] for review in reviews], ["near", "far", "jst-boundary"])
        self.assertEqual(
            reviews,
            [
                {
                    "requestId": "near",
                    "category": "writing",
                    "price_jpy": 12000,
                    "ts": rows[0]["ts"],
                    "delivery_date": "2026-07-23",
                    "gap_days": 2,
                },
                {
                    "requestId": "far",
                    "category": "development",
                    "price_jpy": 65000,
                    "ts": rows[1]["ts"],
                    "delivery_date": "2026-09-10",
                    "gap_days": 51,
                },
                {
                    "requestId": "jst-boundary",
                    "category": "design",
                    "price_jpy": 30000,
                    "ts": rows[2]["ts"],
                    "delivery_date": "2026-07-23",
                    "gap_days": 1,
                },
            ],
        )

    def test_prompts_require_honest_earliest_date_and_immediate_submission(self):
        gig_pass = GIG_PASS.read_text(encoding="utf-8")
        runbook = RUNBOOK.read_text(encoding="utf-8")
        b1_prompt = _step_prompt_line(gig_pass, "B1")
        b2_prompt = _step_prompt_line(gig_pass, "B2")
        runbook_b1 = runbook.split("B1 NURTURE ALL", 1)[1].split("PURCHASE-STATUS", 1)[0]
        runbook_b2 = runbook.split("B2 APPLY BROADLY", 1)[1].split("B3 LEARN", 1)[0]

        for source_name, source in (("gig_pass B2", b2_prompt), ("runbook B2", runbook_b2)):
            for phrase in ("安全マージンとして日数を足さず", "正直に実行可能な最短日"):
                with self.subTest(source=source_name, phrase=phrase):
                    self.assertTrue(phrase in source, f"{source_name} missing prompt phrase: {phrase}")
        for source_name, source in (("gig_pass B1", b1_prompt), ("runbook B1", runbook_b1)):
            for phrase in ("以前申告した納期を待たず", "直ちに提出"):
                with self.subTest(source=source_name, phrase=phrase):
                    self.assertTrue(phrase in source, f"{source_name} missing prompt phrase: {phrase}")

    def test_step_0_5_reviews_every_pending_delivery_for_possible_acceleration(self):
        gig_pass = GIG_PASS.read_text(encoding="utf-8")
        runbook = RUNBOOK.read_text(encoding="utf-8")
        learn_prompt = _step_prompt_line(gig_pass, "LEARN")
        runbook_learn = runbook.split("STEP 0.5 LEARN", 1)[1].split("PRE-STEP", 1)[0]

        for source_name, source in (("gig_pass LEARN", learn_prompt), ("runbook STEP 0.5", runbook_learn)):
            for phrase in ("pending_deliveries_review", "前倒しできるものが無いか"):
                with self.subTest(source=source_name, phrase=phrase):
                    self.assertTrue(phrase in source, f"{source_name} missing prompt phrase: {phrase}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
