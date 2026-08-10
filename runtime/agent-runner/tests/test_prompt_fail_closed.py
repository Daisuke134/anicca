"""X23: a prompt that cannot carry a task must never reach a paid provider.

Measured 2026-07-26/27 on the capafy loop: claude-direct returned a one-turn
greeting ("Ready. Task or question?") and the run was still billed $0.135.
Whatever makes a prompt degenerate, the money is spent the moment the provider
process starts, so the only place a guard can actually save anything is before
the launch. These tests pin that ordering: an empty/trivial prompt exits
non-zero with no provider execution and no evidence directory contents.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "agent_runner.py"


class PromptFailClosedTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.marker = self.root / "provider-was-launched"
        self.schema = self.root / "schema.json"
        self.schema.write_text(json.dumps({
            "type": "object",
            "required": ["status"],
            "properties": {"status": {"const": "ok"}},
        }), encoding="utf-8")
        # A stub provider that records the fact it ran at all. If the guard
        # works, this marker must not exist.
        stub = self.bin / "claude"
        stub.write_text(
            "#!/usr/bin/env bash\nset -u\n"
            f"touch {self.marker}\n"
            "printf '%s' '{\"result\": \"{\\\"status\\\":\\\"ok\\\"}\"}'\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({
            "version": 1,
            "task_classes": {
                "tool-agent": {
                    "timeout_seconds": 5,
                    "candidates": [{"provider": "claude-direct", "model": "sonnet"}],
                },
            },
            "providers": {"claude-direct": {"executable": "claude"}},
            "timeout_seconds": 5,
        }), encoding="utf-8")

    def run_runner(self, prompt_text, use_stdin=False, extra_env=None, *, loop="x23", task_label="x23"):
        evidence = self.root / "evidence"
        env = os.environ.copy()
        env["PATH"] = f"{self.bin}:{env['PATH']}"
        env["AGENT_RUNNER_CONFIG"] = str(self.config)
        env["ANICCA_USAGE_LEDGER"] = str(self.root / "usage.jsonl")
        env.update(extra_env or {})
        command = [
            "python3", str(RUNNER), "--task-class", "tool-agent",
            "--schema", str(self.schema), "--evidence-dir", str(evidence),
            "--task-label", task_label, "--loop", loop, "--workdir", str(self.root),
        ]
        if use_stdin:
            command.append("--prompt-stdin")
            proc = subprocess.run(command, env=env, text=True,
                                  input=prompt_text, capture_output=True)
        else:
            prompt_file = self.root / "prompt.txt"
            prompt_file.write_text(prompt_text, encoding="utf-8")
            command.extend(["--prompt-file", str(prompt_file)])
            proc = subprocess.run(command, env=env, text=True, capture_output=True)
        return proc, evidence

    def assert_rejected_before_spend(self, proc, evidence):
        self.assertEqual(proc.returncode, 2, f"stdout={proc.stdout} stderr={proc.stderr}")
        self.assertIn("prompt", proc.stderr.lower())
        self.assertFalse(
            self.marker.exists(),
            "provider process was launched -- money is already spent at that point",
        )
        self.assertFalse((evidence / "attempts.jsonl").exists())

    def test_empty_prompt_file_is_rejected_before_any_provider_launch(self):
        proc, evidence = self.run_runner("")
        self.assert_rejected_before_spend(proc, evidence)

    def test_whitespace_only_prompt_is_rejected_before_any_provider_launch(self):
        proc, evidence = self.run_runner("\n   \n\t\n")
        self.assert_rejected_before_spend(proc, evidence)

    def test_trivial_prompt_is_rejected_before_any_provider_launch(self):
        proc, evidence = self.run_runner("hi\n")
        self.assert_rejected_before_spend(proc, evidence)

    def test_empty_stdin_prompt_is_rejected_before_any_provider_launch(self):
        proc, evidence = self.run_runner("", use_stdin=True)
        self.assert_rejected_before_spend(proc, evidence)

    def test_real_prompt_still_reaches_the_provider(self):
        proc, _ = self.run_runner("Return the bounded contract JSON only.\n")
        self.assertTrue(
            self.marker.exists(),
            f"regression: real prompt never launched provider. stderr={proc.stderr}",
        )

    def test_usage_attempt_is_durable_before_launch_and_completion_reuses_id(self):
        ids = set()
        for rc, status, override in ((0, "success", False), (9, "failed", True)):
            usage, observed = self.root / f"usage-{rc}.jsonl", self.root / f"observed-{rc}"
            attempt = self.root / f"attempt-{rc}.jsonl" if override else usage.with_name("agent-usage-attempts.jsonl")
            self.bin.joinpath("claude").write_text("#!/usr/bin/env bash\n" "p=\"${ANICCA_USAGE_ATTEMPT_LEDGER:-$(dirname \"$ANICCA_USAGE_LEDGER\")/agent-usage-attempts.jsonl}\"\n" f"test -s \"$p\" || exit 91\ncp \"$p\" \"{observed}\"\nprintf '%s' '{{\"type\":\"result\",\"result\":\"{{\\\"status\\\":\\\"ok\\\"}}\",\"usage\":{{\"input_tokens\":10,\"output_tokens\":2}}}}'\nexit {rc}\n", encoding="utf-8"); self.bin.joinpath("claude").chmod(0o755)
            env = {"ANICCA_USAGE_LEDGER": str(usage), **({"ANICCA_USAGE_ATTEMPT_LEDGER": str(attempt)} if override else {})}
            proc, evidence = self.run_runner("Return the bounded contract JSON only.\n", extra_env=env)
            self.assertEqual(proc.returncode == 0, rc == 0, proc.stderr)
            row = json.loads(observed.read_text().splitlines()[0]); self.assertEqual(set(row), {"version", "event_id", "timestamp", "loop", "task_label", "attempt", "provider", "model"}); self.assertRegex(row["event_id"], r"^[0-9a-f]{24}$"); self.assertTrue(row["timestamp"].endswith("+00:00")); self.assertEqual(os.stat(attempt).st_mode & 0o777, 0o600); self.assertNotIn(row["event_id"], ids); ids.add(row["event_id"])
            evidence_row = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0]); completion = json.loads(usage.read_text().splitlines()[0]); self.assertEqual(evidence_row["event_id"], row["event_id"]); self.assertEqual((completion["event_id"], completion["status"]), (row["event_id"], status))

    def test_completion_write_failure_leaves_unmatched_attempt(self):
        usage, attempt = self.root / "blocked-usage", self.root / "agent-usage-attempts.jsonl"; usage.mkdir()
        self.bin.joinpath("claude").write_text("#!/usr/bin/env bash\n" "p=\"${ANICCA_USAGE_ATTEMPT_LEDGER:-$(dirname \"$ANICCA_USAGE_LEDGER\")/agent-usage-attempts.jsonl}\"\n" "test -s \"$p\" || exit 91\nprintf '%s' '{\"type\":\"result\",\"result\":\"{\\\"status\\\":\\\"ok\\\"}\",\"usage\":{\"input_tokens\":10,\"output_tokens\":2}}'\n", encoding="utf-8"); self.bin.joinpath("claude").chmod(0o755)
        proc, evidence = self.run_runner("Return the bounded contract JSON only.\n", extra_env={"ANICCA_USAGE_LEDGER": str(usage), "ANICCA_USAGE_ATTEMPT_LEDGER": str(attempt)})
        self.assertEqual(proc.returncode, 0, proc.stderr); self.assertTrue(attempt.exists()); durable = json.loads(attempt.read_text().splitlines()[0]); row = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0]); self.assertTrue(row["telemetry_error"]); self.assertEqual(row["event_id"], durable["event_id"]); self.assertTrue(usage.is_dir()); self.assertEqual(list(usage.iterdir()), [])

    def test_attempt_write_failure_blocks_provider_and_settles_zero(self):
        blocked = self.root / "blocked-attempt"; blocked.mkdir(); config = json.loads(self.config.read_text()); config["task_classes"]["tool-agent"]["token_reservation"] = 30; self.config.write_text(json.dumps(config), encoding="utf-8")
        budget = self.root / "token-budget.jsonl"; env = {"ANICCA_USAGE_ATTEMPT_LEDGER": str(blocked), "ANICCA_BUDGET_SCOPE_ID": "attempt-failure-pass", "ANICCA_PASS_TOKEN_BUDGET": "100", "ANICCA_LOOP_DAILY_TOKEN_BUDGET": "100", "ANICCA_TOKEN_BUDGET_LEDGER": str(budget)}
        proc, evidence = self.run_runner("Return the bounded contract JSON only.\n", extra_env=env)
        settlements = [json.loads(line) for line in budget.read_text().splitlines() if json.loads(line)["type"] == "settlement"]; self.assertNotEqual(proc.returncode, 0); self.assertEqual(proc.stderr.strip(), "agent-runner: usage attempt capture failed"); self.assertFalse(self.marker.exists()); self.assertFalse((self.root / "usage.jsonl").exists()); self.assertFalse((evidence / "attempts.jsonl").exists()); self.assertEqual(len(settlements), 1); self.assertEqual((settlements[0]["charged_tokens"], settlements[0]["measurement"]), (0, "unavailable")); self.assertTrue((evidence / "summary.json").exists())

    def test_invalid_capture_boundaries_fail_before_effects(self):
        prompt = "Return the bounded contract JSON only.\n"
        for kwargs in ({"loop": ""}, {"loop": " "}, {"task_label": ""}, {"task_label": " "}):
            proc, evidence = self.run_runner(prompt, **kwargs); self.assertEqual(proc.returncode, 2); self.assertFalse(self.marker.exists()); self.assertFalse(evidence.exists())
        same = self.root / "same-ledger.jsonl"; proc, evidence = self.run_runner(prompt, extra_env={"ANICCA_USAGE_LEDGER": str(same), "ANICCA_USAGE_ATTEMPT_LEDGER": str(same)}); self.assertEqual(proc.returncode, 2); self.assertIn("must differ", proc.stderr); self.assertFalse(self.marker.exists()); self.assertFalse(evidence.exists()); self.assertFalse(same.exists())
        config = json.loads(self.config.read_text()); config["task_classes"]["tool-agent"]["candidates"] = [{"provider": "claude-direct", "model": " "}]; self.config.write_text(json.dumps(config), encoding="utf-8"); proc, evidence = self.run_runner(prompt); self.assertEqual(proc.returncode, 2); self.assertIn("candidate provider/model", proc.stderr); self.assertFalse(self.marker.exists()); self.assertFalse(evidence.exists())

    def test_fallback_attempts_have_unique_matching_completion_ids(self):
        calls = self.root / "calls"; config = json.loads(self.config.read_text()); config["task_classes"]["tool-agent"]["candidates"] = [{"provider": "claude-direct", "model": "first"}, {"provider": "claude-direct", "model": "second"}]; self.config.write_text(json.dumps(config), encoding="utf-8")
        self.bin.joinpath("claude").write_text("#!/usr/bin/env bash\n" "p=\"${ANICCA_USAGE_ATTEMPT_LEDGER:-$(dirname \"$ANICCA_USAGE_LEDGER\")/agent-usage-attempts.jsonl}\"\n" f"test -s \"$p\" || exit 91\nn=0; test -f \"{calls}\" && n=$(wc -l < \"{calls}\"); n=$((n+1)); printf '%s\\n' x >> \"{calls}\"\n" "if [ \"$n\" = 1 ]; then echo 'usage limit resets Jul 29' >&2; exit 1; fi\nprintf '%s' '{\"type\":\"result\",\"result\":\"{\\\"status\\\":\\\"ok\\\"}\",\"usage\":{\"input_tokens\":10,\"output_tokens\":2}}'\n", encoding="utf-8"); self.bin.joinpath("claude").chmod(0o755)
        proc, evidence = self.run_runner("Return the bounded contract JSON only.\n"); self.assertEqual(proc.returncode, 0, proc.stderr); attempts = [json.loads(line) for line in (self.root / "agent-usage-attempts.jsonl").read_text().splitlines()]; completions = [json.loads(line) for line in (self.root / "usage.jsonl").read_text().splitlines()]; self.assertEqual(len(attempts), 2); self.assertEqual(len(completions), 2); self.assertEqual(len({row["event_id"] for row in attempts}), 2); self.assertEqual([row["event_id"] for row in attempts], [row["event_id"] for row in completions]); self.assertTrue((evidence / "attempts.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
