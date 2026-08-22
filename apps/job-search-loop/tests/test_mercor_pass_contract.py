import json
from pathlib import Path
import tempfile
import unittest

from job_search_loop.agent_runner import AgentRunner, TASK_CLASSES
from job_search_loop.mercor_pass import build_context, validate_evidence_paths


ROOT = Path(__file__).resolve().parents[1]


class MercorPassContractTests(unittest.TestCase):
    def test_task_class_is_modelled_browser_lane(self):
        self.assertEqual(TASK_CLASSES["mercor_pass"], "browser-lane-agent")

    def test_prompt_contains_model_led_submit_guard_and_human_stop(self):
        prompt = (ROOT / "prompts" / "mercor-pass.md").read_text(encoding="utf-8")
        for required in (
            "model-led",
            "3 of 3 steps completed",
            "Submit application",
            "continue to the next distinct listing",
            "not a terminal pass result",
            "never retry",
            "needs_human",
            "browser Google 2FA button named `はい`",
            "Never write evidence",
            "only the current `evidence_dir`",
            "exact `evidence_dir` supplied",
            "never inspect or reuse an older `model-pass-*` directory",
            "visible pagination controls",
            "button titled `Page N` or `Next`",
            "up to four additional pages",
            "with a bounded maximum of twelve candidate",
            "detail pages per wake",
            "Never stop after the first Explore page",
        ):
            self.assertIn(required, prompt)

    def test_success_result_contract_validates(self):
        schema = json.loads(
            (ROOT / "schemas" / "mercor-pass-result.v1.schema.json").read_text(encoding="utf-8")
        )
        result = {
            "status": "submitted",
            "inspected_listings": [{
                "listing_id": "list-test",
                "url": "https://work.mercor.com/jobs/test",
                "title": "Software Evaluator",
                "application_state": "3/3",
                "submit_visible": True,
                "decision": "submitted",
            }],
            "submitted": [{
                "listing_id": "list-test",
                "title": "Software Evaluator",
                "url": "https://work.mercor.com/jobs/test",
                "status": "submitted_pending_review",
                "evidence_url": "https://work.mercor.com/jobs/apply/test",
                "evidence_path": "/tmp/evidence.json",
            }],
            "needs_human": [],
            "blocked": [],
            "evidence": {
                "page_url": "https://work.mercor.com/jobs/apply/test",
                "screenshot_path": "/tmp/screenshot.png",
                "dom_path": "/tmp/dom.json",
            },
        }
        AgentRunner.validate(result, schema)

    def test_runner_snapshots_prompt_and_schema_into_private_pass_evidence(self):
        script = (ROOT / "scripts" / "run-mercor.sh").read_text(encoding="utf-8")
        for required in (
            'PASS_PROMPT="$EVIDENCE/mercor-pass.md"',
            'PASS_SCHEMA="$EVIDENCE/mercor-pass-result.v1.schema.json"',
            'cp "$JOB_SEARCH_APP_ROOT/schemas/mercor-pass-result.v1.schema.json" "$PASS_SCHEMA"',
            '--prompt "$PASS_PROMPT"',
            '--schema "$PASS_SCHEMA"',
        ):
            self.assertIn(required, script)

    def test_runner_normalizes_model_evidence_modes_after_the_pass(self):
        script = (ROOT / "scripts" / "run-mercor.sh").read_text(encoding="utf-8")
        self.assertIn('find "$EVIDENCE" -type d -exec chmod 700 {} +', script)
        self.assertIn('find "$EVIDENCE" -type f -exec chmod 600 {} +', script)

    def test_evidence_paths_must_stay_inside_current_private_pass(self):
        with self.subTest("stale evidence path is rejected"):
            with self.assertRaises(ValueError):
                validate_evidence_paths(
                    {
                        "status": "needs_human",
                        "evidence": {
                            "page_url": "https://work.mercor.com/explore",
                            "screenshot_path": "/tmp/old-pass/screenshot.png",
                            "dom_path": "/tmp/old-pass/dom.json",
                        },
                        "submitted": [],
                    },
                    Path("/tmp/current-pass"),
                )

    def test_evidence_paths_accept_existing_files_inside_current_private_pass(self):
        with self.subTest("current evidence is accepted"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                screenshot = root / "screenshot.png"
                dom = root / "dom.json"
                screenshot.write_bytes(b"png")
                dom.write_text("{}", encoding="utf-8")
                validate_evidence_paths(
                    {
                        "status": "needs_human",
                        "evidence": {
                            "page_url": "https://work.mercor.com/explore",
                            "screenshot_path": str(screenshot),
                            "dom_path": str(dom),
                        },
                        "submitted": [],
                    },
                    root,
                )

    def test_context_binds_the_current_evidence_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            state.mkdir()
            context = build_context(
                state_root=state,
                profile_path=root / "profile.json",
                resume_path=root / "resume.pdf",
                cdp_url="http://127.0.0.1:9334",
                evidence_dir=root / "evidence" / "current-pass",
            )
            self.assertEqual(
                context["evidence_dir"],
                str((root / "evidence" / "current-pass").resolve()),
            )


if __name__ == "__main__":
    unittest.main()
