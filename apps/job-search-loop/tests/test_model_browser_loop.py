import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from job_search_loop.ats import detect_provider, evaluate_snapshot


APP_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
SCHEMA_PATH = APP_ROOT / "schemas" / "browser-row-run.v1.schema.json"


def _evidence_ref(name: str) -> dict[str, str]:
    return {"ref": f"evidence:{name}", "sha256": "a" * 64}


def _row_run(*, provider: str, canonical_url: str) -> dict[str, object]:
    return {
        "version": 1,
        "api_version": "job-hunter-browser-agent/1",
        "row": {
            "application_id": f"application:{provider}:replay",
            "company": "Recorded shape employer",
            "role": "Recorded shape role",
            "canonical_url": canonical_url,
            "provider": provider,
            "ledger_state": "materials_ready",
            "candidate_memory_ref": "candidate:memory:v1",
            "answer_memory_ref": "answer:memory:v1",
            "resume": _evidence_ref("resume"),
            "posting": _evidence_ref("posting"),
            "eligibility": {
                "decision": "eligible",
                "policy_version": "eligibility:v1",
                "evidence": _evidence_ref("eligibility"),
            },
        },
        "run": {
            "row_run_id": f"row-run:{provider}:replay",
            "wake_id": "wake:replay",
            "step_index": 0,
            "remaining_steps": 50,
            "remaining_seconds": 900,
            "observation_ref": None,
            "checkpoint_predecessor_sha256": None,
            "updated_at": "2026-08-22T00:00:00Z",
            "state": "queued",
            "effect_phase": "pre_submit",
        },
    }


class ModelBrowserLoopContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def assertValid(self, value: dict[str, object]) -> None:
        errors = sorted(self.validator.iter_errors(value), key=lambda item: list(item.path))
        self.assertEqual([], [error.message for error in errors])

    def assertInvalid(self, value: dict[str, object]) -> None:
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_recorded_workday_and_ashby_shapes_replay_through_one_row_contract(self):
        workday = json.loads(
            (FIXTURES / "browser_agent" / "workday-step1-live-shape.v1.json").read_text(
                encoding="utf-8"
            )
        )
        ashby = json.loads(
            (FIXTURES / "ats" / "ashby-application-surface.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(workday["evidence_class"], "live_cdp_sanitized_projection")
        self.assertEqual(workday["source_control_count"], 42)
        self.assertRegex(workday["source_sha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(detect_provider(workday["canonical_url"]), "workday")
        self.assertEqual(evaluate_snapshot(ashby)["surface"], "ashby_application")

        self.assertValid(
            _row_run(provider="workday", canonical_url=workday["canonical_url"])
        )
        self.assertValid(_row_run(provider="ashby", canonical_url=ashby["url"]))

    def test_row_contract_rejects_secrets_raw_answers_terminal_retries_and_reclick(self):
        valid = _row_run(
            provider="workday",
            canonical_url="https://tenant.wd1.myworkdayjobs.com/job/role/apply",
        )
        cases = []
        for forbidden_key in ("password", "cookie", "email_code", "raw_answer"):
            value = copy.deepcopy(valid)
            value["row"][forbidden_key] = "must-not-cross-boundary"
            cases.append(value)
        for terminal in ("submitted", "submit_unknown"):
            value = copy.deepcopy(valid)
            value["row"]["ledger_state"] = terminal
            cases.append(value)
        reclick = copy.deepcopy(valid)
        reclick["run"].update(
            {
                "state": "acting",
                "effect_phase": "post_submit_verification",
                "intent_id": "intent:one",
                "fence": 1,
                "final_action_receipt": _evidence_ref("submit-click"),
            }
        )
        cases.append(reclick)

        for value in cases:
            with self.subTest(value=value):
                self.assertInvalid(value)

    def test_current_fast_paths_are_recorded_as_all_five_contract_gaps(self):
        workday = (APP_ROOT / "job_search_loop" / "workday_fast_path.py").read_text(
            encoding="utf-8"
        )
        ashby = (APP_ROOT / "job_search_loop" / "ashby_fast_path.py").read_text(
            encoding="utf-8"
        )
        sources = workday + "\n" + ashby
        gaps = set()
        if "async def _snapshot" in workday and "page.screenshot" not in workday:
            gaps.add("observation_without_screenshot")
        if "_click_surface" in sources and "_fill_step" in sources:
            gaps.add("fast_path_owns_actions")
        if '"status": "blocked"' in sources:
            gaps.add("row_failure_becomes_blocked")
        if "CheckpointStore" not in sources:
            gaps.add("no_durable_row_checkpoint")
        if "complete_submission" in sources and "_confirmation" in sources:
            gaps.add("fast_path_owns_completion_classification")

        self.assertEqual(
            {
                "observation_without_screenshot",
                "fast_path_owns_actions",
                "row_failure_becomes_blocked",
                "no_durable_row_checkpoint",
                "fast_path_owns_completion_classification",
            },
            gaps,
        )


if __name__ == "__main__":
    unittest.main()
