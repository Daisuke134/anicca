import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AshbyApplyTests(unittest.TestCase):
    @staticmethod
    def _grounding_profile():
        return {
            "version": 1,
            "candidate": {
                "name": "Candidate Name",
                "application_email": "candidate@example.test",
                "phone": "+81-00-0000-0000",
                "start_date": "2026-12-01",
            },
            "facts": [
                {
                    "id": "availability_tokyo_office",
                    "claim": "Available in a Tokyo office three days per week.",
                    "evidence": "User statement.",
                },
                {
                    "id": "availability_start_date_20261201",
                    "claim": "Available to start on December 1, 2026.",
                    "evidence": "User statement.",
                },
            ],
        }

    def test_profile_grounding_rejects_unrelated_standard_answer(self):
        module = importlib.import_module("job_search_loop.ashby_apply")
        self.assertTrue(
            hasattr(module, "validate_profile_grounding"),
            "deterministic Ashby profile grounding is missing",
        )
        bad = {
            "status": "ready",
            "receipts": [
                {
                    "question": "When can you start a new role?",
                    "answer": "Available in a Tokyo office three days per week.",
                    "fact_ids": ["availability_tokyo_office"],
                    "kind": "fill",
                    "verified": True,
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "standard answer is not profile-grounded"):
            module.validate_fill_result(bad, profile=self._grounding_profile())

        valid = {
            **bad,
            "receipts": [
                {
                    **bad["receipts"][0],
                    "answer": "2026-12-01",
                    "fact_ids": ["profile.start_date"],
                }
            ],
        }
        self.assertEqual(
            module.validate_fill_result(valid, profile=self._grounding_profile()),
            {"status": "pre_submit_ready", "verified_count": 1},
        )

    def test_profile_grounding_rejects_unknown_fact_id_for_custom_question(self):
        module = importlib.import_module("job_search_loop.ashby_apply")
        self.assertTrue(
            hasattr(module, "validate_profile_grounding"),
            "deterministic Ashby profile grounding is missing",
        )
        receipt = {
            "status": "ready",
            "receipts": [
                {
                    "question": "Describe your relevant experience",
                    "answer": "Grounded answer",
                    "fact_ids": ["invented_fact"],
                    "kind": "fill",
                    "verified": True,
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "unknown profile fact id"):
            module.validate_fill_result(receipt, profile=self._grounding_profile())

    def test_verify_cli_returns_structured_rejection_for_non_ready_result(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fill-result.json"
            profile = Path(directory) / "profile.json"
            output.write_text(
                json.dumps({"status": "needs_fact", "receipts": []}) + "\n",
                encoding="utf-8",
            )
            profile.write_text(
                json.dumps(self._grounding_profile()) + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "job_search_loop.ashby_apply",
                    "verify",
                    "--output",
                    str(output),
                    "--profile",
                    str(profile),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertEqual(
                json.loads(completed.stdout),
                {
                    "status": "rejected",
                    "reason": "resident fill result is not ready",
                },
            )
            self.assertEqual(completed.stderr, "")

    def test_verify_cli_requires_private_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fill-result.json"
            output.write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "receipts": [
                            {"kind": "upload", "verified": True},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "job_search_loop.ashby_apply",
                    "verify",
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("verify requires --profile", completed.stderr)

    def test_resident_fill_receipt_requires_verified_non_submit_actions(self):
        module = importlib.import_module("job_search_loop.ashby_apply")
        self.assertTrue(
            hasattr(module, "validate_fill_result"),
            "resident fill receipt validator is missing",
        )

        valid = {
            "status": "ready",
            "receipts": [
                {"kind": "fill", "verified": True},
                {"kind": "select", "verified": True},
                {"kind": "check", "verified": True},
                {"kind": "upload", "verified": True},
            ],
        }
        self.assertEqual(
            module.validate_fill_result(valid),
            {"status": "pre_submit_ready", "verified_count": 4},
        )

        for invalid in (
            {**valid, "receipts": [{"kind": "fill", "verified": False}]},
            {**valid, "receipts": [{"kind": "submit", "verified": True}]},
            {**valid, "status": "submitted"},
            {**valid, "receipts": []},
        ):
            with self.assertRaises(ValueError):
                module.validate_fill_result(invalid)

    def test_yes_no_buttons_win_over_internal_checkbox(self):
        from job_search_loop.ashby_apply import classify_control

        self.assertEqual(
            classify_control(
                has_file=False,
                has_checkbox=True,
                has_select=False,
                options=["Yes", "No"],
                has_editable=False,
            ),
            "select",
        )

    def test_plan_uses_current_live_field_paths_not_prior_posting_ids(self):
        from job_search_loop.ashby_apply import build_actions

        fields = [
            {
                "field_path": "new-phone-id",
                "question": "Phone number",
                "required": True,
                "control": "fill",
            },
            {
                "field_path": "new-authorization-id",
                "question": "Are you authorized to work in Japan?",
                "required": True,
                "control": "select",
                "options": ["Yes", "No"],
            },
            {
                "field_path": "new-attestation-id",
                "question": "I confirm I have read the above.",
                "required": True,
                "control": "check",
            },
            {
                "field_path": "_systemfield_resume",
                "question": "Resume/CV",
                "required": True,
                "control": "upload",
            },
        ]
        answer_map = {
            "Phone number": {
                "answer": "+81-00-0000-0000",
                "fact_ids": ["profile.phone"],
                "prior_field_path": "old-phone-id",
            },
            "Are you authorized to work in Japan?": {
                "answer": "Yes",
                "fact_ids": ["legal.japan_work_authorization"],
            },
            "I confirm I have read the above.": {
                "answer": "Confirmed",
                "fact_ids": ["candidate.attestation"],
            },
        }

        result = build_actions(
            fields,
            answer_map=answer_map,
            resume_path="/private/resume.pdf",
            resume_sha256="a" * 64,
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(
            [action["field_path"] for action in result["actions"]],
            [
                "new-phone-id",
                "new-authorization-id",
                "new-attestation-id",
                "_systemfield_resume",
            ],
        )
        self.assertEqual(
            [action["kind"] for action in result["actions"]],
            ["fill", "select", "check", "upload"],
        )
        self.assertNotIn("old-phone-id", repr(result))


if __name__ == "__main__":
    unittest.main()
