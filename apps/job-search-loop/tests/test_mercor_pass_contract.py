import json
from pathlib import Path
import unittest

from job_search_loop.agent_runner import AgentRunner, TASK_CLASSES


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
            "only the pass evidence directory",
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


if __name__ == "__main__":
    unittest.main()
