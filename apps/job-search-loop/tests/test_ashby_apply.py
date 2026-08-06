import importlib
import hashlib
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


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
        with tempfile.TemporaryDirectory() as directory:
            screenshot = Path(directory) / "pre-submit.png"
            screenshot.write_bytes(b"grounded form")
            valid["pre_submit_screenshot"] = {
                "path": str(screenshot),
                "sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
            }
            self.assertEqual(
                module.validate_fill_result(valid, profile=self._grounding_profile()),
                {
                    "status": "pre_submit_ready",
                    "verified_count": 1,
                    "screenshot_sha256": valid["pre_submit_screenshot"]["sha256"],
                },
            )

        module.validate_profile_grounding(
            [
                {
                    "question": "Name",
                    "answer": "Candidate Name",
                    "fact_ids": ["profile.name"],
                    "kind": "fill",
                }
            ],
            self._grounding_profile(),
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

    def test_apply_cli_requires_grounded_inputs_and_existing_submit_fence(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "job_search_loop.ashby_apply",
                    "apply",
                    "--endpoint",
                    "http://127.0.0.1:9222",
                    "--url",
                    "https://jobs.ashbyhq.com/example/role",
                    "--output",
                    str(Path(directory) / "apply-result.json"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn(
                "apply requires --answers, --resume, --profile, --ledger, "
                "--intent-id, and --fence",
                completed.stderr,
            )
            self.assertNotIn("invalid choice", completed.stderr)

    def test_resident_fill_receipt_requires_verified_non_submit_actions(self):
        module = importlib.import_module("job_search_loop.ashby_apply")
        self.assertTrue(
            hasattr(module, "validate_fill_result"),
            "resident fill receipt validator is missing",
        )

        with tempfile.TemporaryDirectory() as directory:
            screenshot = Path(directory) / "pre-submit.png"
            screenshot.write_bytes(b"verified form")
            valid = {
                "status": "ready",
                "receipts": [
                    {"kind": "fill", "verified": True},
                    {"kind": "select", "verified": True},
                    {"kind": "check", "verified": True},
                    {"kind": "upload", "verified": True},
                ],
                "pre_submit_screenshot": {
                    "path": str(screenshot),
                    "sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
                },
            }
            self.assertEqual(
                module.validate_fill_result(valid),
                {
                    "status": "pre_submit_ready",
                    "verified_count": 4,
                    "screenshot_sha256": valid["pre_submit_screenshot"]["sha256"],
                },
            )

            for invalid in (
                {**valid, "receipts": [{"kind": "fill", "verified": False}]},
                {**valid, "receipts": [{"kind": "submit", "verified": True}]},
                {**valid, "status": "submitted"},
                {**valid, "receipts": []},
            ):
                with self.assertRaises(ValueError):
                    module.validate_fill_result(invalid)

    def test_resident_fill_receipt_requires_matching_pre_submit_screenshot(self):
        module = importlib.import_module("job_search_loop.ashby_apply")
        with tempfile.TemporaryDirectory() as directory:
            screenshot = Path(directory) / "pre-submit.png"
            screenshot.write_bytes(b"real pre-submit screenshot")
            valid = {
                "status": "ready",
                "receipts": [{"kind": "fill", "verified": True}],
                "pre_submit_screenshot": {
                    "path": str(screenshot),
                    "sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
                },
            }

            self.assertEqual(
                module.validate_fill_result(valid),
                {
                    "status": "pre_submit_ready",
                    "verified_count": 1,
                    "screenshot_sha256": valid["pre_submit_screenshot"]["sha256"],
                },
            )
            for invalid in (
                {key: value for key, value in valid.items() if key != "pre_submit_screenshot"},
                {
                    **valid,
                    "pre_submit_screenshot": {
                        **valid["pre_submit_screenshot"],
                        "sha256": "0" * 64,
                    },
                },
            ):
                with self.assertRaisesRegex(ValueError, "pre-submit screenshot"):
                    module.validate_fill_result(invalid)

    def test_capture_pre_submit_screenshot_records_real_file_and_hash(self):
        module = importlib.import_module("job_search_loop.ashby_apply")

        class Page:
            def screenshot(self, *, path, full_page):
                self.call = (path, full_page)
                Path(path).write_bytes(b"captured browser page")

        with tempfile.TemporaryDirectory() as directory:
            page = Page()
            output = Path(directory) / "ashby-result.json"
            screenshot = module.capture_pre_submit_screenshot(page, output)

            expected_path = Path(directory) / "ashby-result.pre-submit.png"
            self.assertEqual(page.call, (str(expected_path), True))
            self.assertEqual(
                screenshot,
                {
                    "path": str(expected_path),
                    "sha256": hashlib.sha256(b"captured browser page").hexdigest(),
                },
            )
            self.assertEqual(expected_path.stat().st_mode & 0o777, 0o600)

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

    def test_ashby_active_class_confirms_selected_yes_no_button(self):
        from job_search_loop.ashby_apply import (
            combobox_selection_is_committed,
            selection_state_is_active,
        )

        self.assertTrue(
            selection_state_is_active(
                class_name="_container_pjyt6_1 _option_1svni_32 _active_1svni_57",
                aria_checked=None,
                aria_pressed=None,
                data_state=None,
                native_checked=False,
            )
        )
        self.assertTrue(
            combobox_selection_is_committed(
                value="Tokyo, Tokyo Prefecture, Japan", aria_expanded="false"
            )
        )
        self.assertFalse(
            combobox_selection_is_committed(
                value="Tokyo, Japan", aria_expanded="true"
            )
        )
        self.assertFalse(
            selection_state_is_active(
                class_name="_container_pjyt6_1 _option_1svni_32",
                aria_checked=None,
                aria_pressed=None,
                data_state=None,
                native_checked=False,
            )
        )
        self.assertTrue(
            selection_state_is_active(
                class_name="",
                aria_checked=None,
                aria_pressed=None,
                data_state=None,
                native_checked=True,
            )
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

    def test_semantic_submit_fences_one_click_and_returns_authoritative_observation(self):
        from job_search_loop import ashby_apply

        self.assertTrue(
            hasattr(ashby_apply, "execute_semantic_submit"),
            "semantic resident Submit action is missing",
        )
        execute_semantic_submit = ashby_apply.execute_semantic_submit

        events = []
        response = SimpleNamespace(status=200)
        response.json = lambda: {
            "data": {
                "submitApplicationFormAction": {
                    "applicationFormResult": {"__typename": "FormSubmitSuccess"}
                }
            }
        }
        request = SimpleNamespace(
            post_data_json={
                "operationName": "ApiSubmitSingleApplicationFormAction"
            },
            response=lambda: response,
        )
        observer = MagicMock()
        observer.__enter__.side_effect = lambda: (
            events.append("observer_attached")
            or SimpleNamespace(value=request)
        )
        observer.__exit__.return_value = False
        submit = MagicMock()
        submit.count.return_value = 1
        submit.click.side_effect = lambda: events.append("clicked")
        status = MagicMock()
        status.count.return_value = 1
        status.inner_text.return_value = (
            "Success\nYour application was successfully submitted. "
            "We'll contact you if there are next steps."
        )
        alert = MagicMock()
        alert.count.return_value = 0
        page = MagicMock()
        page.expect_request.return_value = observer
        locators = {
            "button": submit,
            "status": status,
            "alert": alert,
        }
        page.get_by_role.side_effect = lambda role, **_: locators[role]
        span = MagicMock()
        span.__enter__.side_effect = lambda: events.append("span_started") or span
        span.__exit__.side_effect = lambda *_: events.append("span_finished") or False
        telemetry = MagicMock()
        telemetry.span.return_value = span
        self.assertIn(
            "telemetry",
            inspect.signature(execute_semantic_submit).parameters,
            "semantic Submit has no action-span boundary",
        )
        self.assertEqual(
            inspect.signature(execute_semantic_submit)
            .parameters["timeout_ms"]
            .default,
            90_000,
        )
        receipt = execute_semantic_submit(
            page,
            commit_click=lambda: events.append("click_fenced"),
            commit_request_started=lambda: events.append("request_fenced"),
            timeout_ms=12_000,
            telemetry=telemetry,
        )

        self.assertEqual(
            events,
            [
                "span_started",
                "observer_attached",
                "click_fenced",
                "clicked",
                "request_fenced",
                "span_finished",
            ],
        )
        telemetry.span.assert_called_once_with("submit.action")
        span.set_attributes.assert_called_once_with(
            {"confirmation.observed": True}
        )
        predicate = page.expect_request.call_args.args[0]
        self.assertTrue(predicate(request))
        self.assertEqual(page.expect_request.call_args.kwargs["timeout"], 12_000)
        self.assertEqual(receipt["classification"], "authoritative_success")
        self.assertEqual(
            receipt["submit_operation"],
            "ApiSubmitSingleApplicationFormAction",
        )
        self.assertEqual(receipt["http_status"], 200)
        self.assertNotIn("data", receipt)

    def test_semantic_submit_timeout_returns_post_click_evidence_before_page_closes(self):
        from job_search_loop.ashby_apply import execute_semantic_submit

        events = []
        observer = MagicMock()
        observer.__enter__.return_value = SimpleNamespace(value=None)
        observer.__exit__.side_effect = PlaywrightTimeoutError("timed out")
        submit = MagicMock()
        submit.count.return_value = 1
        submit.click.side_effect = lambda: events.append("clicked")
        status = MagicMock()
        status.count.return_value = 0
        alert = MagicMock()
        alert.count.return_value = 1
        alert.all_inner_texts.return_value = ["Please complete this required field"]
        recaptcha = MagicMock()
        recaptcha.count.return_value = 1
        recaptcha.input_value.return_value = ""
        page = MagicMock()
        page.expect_request.return_value = observer
        page.get_by_role.side_effect = lambda role, **_: {
            "button": submit,
            "status": status,
            "alert": alert,
        }[role]
        page.locator.return_value = recaptcha

        receipt = execute_semantic_submit(
            page,
            commit_click=lambda: events.append("click_fenced"),
            commit_request_started=lambda: events.append("request_fenced"),
            timeout_ms=1,
        )

        self.assertEqual(events, ["click_fenced", "clicked"])
        self.assertEqual(receipt["classification"], "unconfirmed")
        self.assertEqual(
            receipt["post_click_observation"]["classification"],
            "validation_rejected",
        )
        self.assertTrue(receipt["post_click_observation"]["timed_out"])
        self.assertNotIn("visible_error_texts", receipt)


if __name__ == "__main__":
    unittest.main()
