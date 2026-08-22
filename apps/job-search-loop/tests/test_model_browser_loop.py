import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

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

    def test_daily_owner_routes_forms_only_through_framework_orchestrator(self):
        daily = (APP_ROOT / "scripts" / "run-daily.sh").read_text(encoding="utf-8")
        prompt = (APP_ROOT / "prompts" / "daily-pass.md").read_text(encoding="utf-8")

        self.assertNotIn("job_search_loop.ashby_fast_path", daily)
        self.assertNotIn("job_search_loop.workday_fast_path", daily)
        self.assertNotIn('"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER"', daily)
        self.assertEqual(
            daily.count("-m job_search_loop.browser_agent.orchestrator"), 1
        )
        self.assertNotIn("deterministic Ashby fast path owns", prompt)
        self.assertNotIn("A `blocked` row remains durable work", prompt)
        self.assertIn("RowResumer.restore(endpoint,", prompt)
        self.assertIn("ObservationBuilder.build(handle)", prompt)
        self.assertIn("ActionExecutor.execute(handle,", prompt)
        self.assertIn("remain inside this one Luna xhigh runner turn", prompt)
        self.assertIn("AgentPolicy.next_step", prompt)
        self.assertIn("validation_feedback(previous_observation, current_observation)", prompt)
        self.assertIn("ValidationFeedbackV1.messages", prompt)
        self.assertNotIn("a same-surface result is\n`not_submitted`/a blocker", prompt.lower())
        self.assertIn("Never batch actions from one observation", prompt)
        self.assertIn("validates the complete EvidenceStore action chain", prompt)
        self.assertIn("never\nreplay prior actions", prompt)
        self.assertIn("StepEvidenceV1", prompt)
        self.assertIn("job_search_loop.browser_agent.candidate_memory", daily)
        self.assertIn("CandidateMemoryView", prompt)
        self.assertIn("JOB_SEARCH_ANSWER_MEMORY", daily)
        self.assertIn("AnswerMemory.concept_for_question", prompt)
        self.assertIn("AnswerResolver.resolve(FieldQuestionV1)", prompt)
        self.assertIn("StableInferencePolicy", prompt)
        self.assertIn("JOB_SEARCH_MACHINE_CREDENTIALS", daily)
        self.assertIn("MachineWorkdayCredentialStore", prompt)
        self.assertIn("WorkdayAuthTool.prepare", prompt)
        self.assertIn("surface names are observation hints, not a prescribed workflow", prompt)
        self.assertNotIn("workday_job\n  →", prompt)
        self.assertNotIn("workday-accounts.json", prompt)
        self.assertNotIn("if an unverified fact is a mandatory form field, block", prompt)
        self.assertIn("are not answer outcomes", prompt)
        self.assertNotIn("Use `chromium.connect_over_cdp(endpoint)`", prompt)

    def test_orchestrator_delegates_once_to_the_existing_bounded_runner(self):
        from job_search_loop.browser_agent.orchestrator import invoke_runner

        completed = Mock(returncode=0)
        with patch(
            "job_search_loop.browser_agent.orchestrator.subprocess.run",
            return_value=completed,
        ) as run:
            returncode = invoke_runner(
                runner=Path("/runtime/agent_runner.py"),
                prompt=Path("/app/prompts/daily-pass.md"),
                schema=Path("/app/schemas/pass-result.v1.schema.json"),
                evidence_dir=Path("/state/evidence/wake"),
                workdir=Path("/repo"),
                timeout_seconds=900,
                python="/python3",
                active_provider="workday",
            )

        self.assertEqual(returncode, 0)
        run.assert_called_once()
        command = run.call_args.args[0]
        kwargs = run.call_args.kwargs
        self.assertEqual(
            command,
            [
                "/python3",
                "/runtime/agent_runner.py",
                "--task-class",
                "browser-lane-agent",
                "--escalation-reason",
                "mandatory-model-browser-loop",
                "--timeout-seconds",
                "900",
                "--prompt-file",
                "/app/prompts/daily-pass.md",
                "--schema",
                "/app/schemas/pass-result.v1.schema.json",
                "--evidence-dir",
                "/state/evidence/wake",
                "--task-label",
                "job-search-daily",
                "--loop",
                "job-search",
                "--workdir",
                "/repo",
            ],
        )
        self.assertIs(kwargs["check"], False)
        self.assertEqual(
            kwargs["env"]["JOB_SEARCH_ACTIVE_APPLICATION_PROVIDER"], "workday"
        )

    def test_every_eligible_workday_row_reaches_the_mandatory_model_lane(self):
        daily = (APP_ROOT / "scripts" / "run-daily.sh").read_text(encoding="utf-8")
        prompt = (APP_ROOT / "prompts" / "daily-pass.md").read_text(encoding="utf-8")
        normalized_prompt = " ".join(prompt.split())

        self.assertNotIn("JOB_SEARCH_ENABLE_MODEL_FALLBACK", daily)
        self.assertNotIn("-m job_search_loop.workday_fast_path", daily)
        self.assertEqual(
            daily.count("-m job_search_loop.browser_agent.orchestrator"), 1
        )
        self.assertIn('"status": "model_owned"', daily)
        self.assertIn(
            "Process every eligible Workday row returned by both Ledger queue methods",
            normalized_prompt,
        )
        self.assertNotIn("do not reopen a row it advanced", prompt)
        self.assertNotIn("preserve that exact blocker", prompt)

    def test_workday_is_the_only_active_application_lane_during_10p(self):
        daily = (APP_ROOT / "scripts" / "run-daily.sh").read_text(encoding="utf-8")
        prompt = (APP_ROOT / "prompts" / "daily-pass.md").read_text(encoding="utf-8")
        normalized_prompt = " ".join(prompt.split())

        self.assertIn("-m job_search_loop.ashby_discovery", daily)
        self.assertIn('"status": "discovery_only"', daily)
        self.assertIn('"reason": "workday_10p"', daily)
        self.assertIn("--active-provider workday", daily)
        self.assertIn(
            "JOB_SEARCH_ACTIVE_APPLICATION_PROVIDER must be workday",
            normalized_prompt,
        )
        self.assertIn(
            "Do not open or navigate to any Ashby application form during Workday 10P",
            normalized_prompt,
        )


if __name__ == "__main__":
    unittest.main()
