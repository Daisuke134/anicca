import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.assessment_workflow import (
    AssessmentError,
    AssessmentStore,
    SubmissionUncertain,
    build_manifest,
    classify_ai_policy,
    prepare_workspace,
    route_assessment,
    run_isolated,
)


class AssessmentWorkflowTests(unittest.TestCase):
    def test_ai_policy_requires_explicit_rules(self):
        self.assertEqual(
            classify_ai_policy("You may use AI assistants and external resources."),
            "explicitly_allowed",
        )
        self.assertEqual(
            classify_ai_policy("Do not use AI, ChatGPT, Copilot, or outside help."),
            "explicitly_prohibited",
        )
        self.assertEqual(
            classify_ai_policy("Please complete this exercise by Friday."),
            "unspecified",
        )

    def test_only_explicitly_allowed_unproctored_take_home_is_autonomous(self):
        self.assertEqual(
            route_assessment(
                assessment_type="take_home",
                ai_policy="explicitly_allowed",
                proctored=False,
            ),
            "autonomous_allowed",
        )
        for assessment_type, policy, proctored in (
            ("take_home", "unspecified", False),
            ("take_home", "explicitly_prohibited", False),
            ("coding_test", "explicitly_allowed", True),
            ("live_interview", "explicitly_allowed", False),
        ):
            with self.subTest(
                assessment_type=assessment_type,
                policy=policy,
                proctored=proctored,
            ):
                self.assertEqual(
                    route_assessment(
                        assessment_type=assessment_type,
                        ai_policy=policy,
                        proctored=proctored,
                    ),
                    "manual_integrity_gate",
                )

    def test_manifest_requires_https_timezone_and_source_spans(self):
        manifest = build_manifest(
            thread_id="thread-1",
            message_id="message-1",
            company="Example AI",
            role="Applied AI Engineer",
            assessment_type="take_home",
            source_url="https://example.com/assessment",
            deadline="2026-08-05T17:00:00+09:00",
            deadline_source_span="Submit by August 5 at 17:00 JST",
            rules_text="AI assistants are allowed.",
            rules_source_span="You may use AI assistants.",
            proctored=False,
        )
        self.assertEqual(manifest["route"], "autonomous_allowed")
        self.assertEqual(manifest["ai_policy"], "explicitly_allowed")
        for invalid in (
            {"source_url": "http://example.com/test"},
            {"deadline": "2026-08-05T17:00:00"},
            {"rules_source_span": " "},
        ):
            kwargs = {
                "thread_id": "thread-1",
                "message_id": "message-1",
                "company": "Example AI",
                "role": "Applied AI Engineer",
                "assessment_type": "take_home",
                "source_url": "https://example.com/assessment",
                "deadline": "2026-08-05T17:00:00+09:00",
                "deadline_source_span": "Submit by August 5 at 17:00 JST",
                "rules_text": "AI assistants are allowed.",
                "rules_source_span": "You may use AI assistants.",
                "proctored": False,
            }
            kwargs.update(invalid)
            with self.subTest(invalid=invalid):
                with self.assertRaises(AssessmentError):
                    build_manifest(**kwargs)

    def test_workspace_and_manifest_are_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._manifest()
            workspace = prepare_workspace(root, manifest)
            manifest_path = workspace / "manifest.json"
            self.assertEqual(workspace.stat().st_mode & 0o777, 0o700)
            self.assertEqual(manifest_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8"))["assessment_id"],
                manifest["assessment_id"],
            )

    def test_state_machine_rejects_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AssessmentStore(Path(directory) / "assessment.sqlite3")
            manifest = self._manifest()
            store.register(manifest)
            self.assertEqual(store.state(manifest["assessment_id"]), "detected")
            with self.assertRaises(AssessmentError):
                store.transition(manifest["assessment_id"], "verified")
            store.transition(manifest["assessment_id"], "prepared")
            store.transition(manifest["assessment_id"], "executing")
            store.transition(manifest["assessment_id"], "verified")
            self.assertEqual(store.state(manifest["assessment_id"]), "verified")
            store.close()

    def test_manual_route_is_durably_policy_blocked_on_registration(self):
        manifest = build_manifest(
            thread_id="thread-2",
            message_id="message-2",
            company="Example AI",
            role="Applied AI Engineer",
            assessment_type="coding_test",
            source_url="https://example.com/proctored",
            deadline="2026-08-05T17:00:00+09:00",
            deadline_source_span="Submit by August 5 at 17:00 JST",
            rules_text="Complete the assessment in the proctored environment.",
            rules_source_span="Complete the assessment in the proctored environment.",
            proctored=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            store = AssessmentStore(Path(directory) / "assessment.sqlite3")
            store.register(manifest)
            self.assertEqual(
                store.state(manifest["assessment_id"]),
                "policy_blocked",
            )
            store.close()

    def test_submission_started_or_unknown_is_never_claimed_again(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AssessmentStore(Path(directory) / "assessment.sqlite3")
            manifest = self._manifest()
            assessment_id = manifest["assessment_id"]
            store.register(manifest)
            for state in ("prepared", "executing", "verified"):
                store.transition(assessment_id, state)
            fence = store.claim_submission(assessment_id)
            store.mark_submit_started(assessment_id, fence)
            with self.assertRaises(SubmissionUncertain):
                store.claim_submission(assessment_id)
            store.mark_submit_unknown(assessment_id, fence, "browser outcome unknown")
            with self.assertRaises(SubmissionUncertain):
                store.claim_submission(assessment_id)
            store.close()

    def test_isolated_runner_writes_hashed_private_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._manifest()
            workspace = prepare_workspace(root / "workspaces", manifest)
            store = AssessmentStore(root / "assessment.sqlite3")
            store.register(manifest)
            store.transition(manifest["assessment_id"], "prepared")
            result = run_isolated(
                store=store,
                assessment_id=manifest["assessment_id"],
                workspace=workspace,
                argv=["/usr/bin/python3", "-c", "print('verified fixture')"],
                evidence_dir=root / "evidence",
                timeout_seconds=30,
            )
            self.assertEqual(result["status"], "verified")
            self.assertEqual(store.state(manifest["assessment_id"]), "verified")
            self.assertEqual(len(result["stdout_sha256"]), 64)
            output = Path(result["stdout_path"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.read_text(encoding="utf-8").strip(), "verified fixture")
            store.close()

    def test_isolated_runner_denies_home_secret_and_network(self):
        private_parent = Path.home() / ".local/state/anicca/job-search"
        private_parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(dir=private_parent) as directory:
            root = Path(directory)
            secret = root / "outside-workspace-secret.txt"
            secret.write_text("must-not-be-readable", encoding="utf-8")
            manifest = self._manifest()
            workspace = prepare_workspace(root / "workspaces", manifest)
            store = AssessmentStore(root / "assessment.sqlite3")
            store.register(manifest)
            store.transition(manifest["assessment_id"], "prepared")
            program = (
                "import pathlib,socket\n"
                "blocked=0\n"
                f"\ntry: pathlib.Path({str(secret)!r}).read_text()"
                "\nexcept (PermissionError,OSError): blocked+=1\n"
                "try: socket.create_connection(('example.com',443),timeout=1)\n"
                "except OSError: blocked+=1\n"
                "raise SystemExit(0 if blocked == 2 else 9)\n"
            )
            result = run_isolated(
                store=store,
                assessment_id=manifest["assessment_id"],
                workspace=workspace,
                argv=["/usr/bin/python3", "-c", program],
                evidence_dir=root / "evidence",
                timeout_seconds=30,
            )
            self.assertEqual(result["status"], "verified")
            store.close()

    def test_inbox_prompt_routes_assessments_through_integrity_gate(self):
        root = Path(__file__).parents[1]
        prompt = (root / "prompts" / "inbox-pass.md").read_text(encoding="utf-8")
        self.assertIn("assessment_workflow", prompt)
        self.assertIn("explicitly_allowed", prompt)
        self.assertIn("manual_integrity_gate", prompt)
        self.assertIn("submit_started", prompt)
        schema = json.loads(
            (root / "schemas" / "inbox-pass-result.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("assessments", schema["required"])

    @staticmethod
    def _manifest():
        return build_manifest(
            thread_id="thread-1",
            message_id="message-1",
            company="Example AI",
            role="Applied AI Engineer",
            assessment_type="take_home",
            source_url="https://example.com/assessment",
            deadline="2026-08-05T17:00:00+09:00",
            deadline_source_span="Submit by August 5 at 17:00 JST",
            rules_text="You may use AI assistants and external resources.",
            rules_source_span="You may use AI assistants and external resources.",
            proctored=False,
        )


if __name__ == "__main__":
    unittest.main()
