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

    def run_runner(self, prompt_text, use_stdin=False):
        evidence = self.root / "evidence"
        env = os.environ.copy()
        env["PATH"] = f"{self.bin}:{env['PATH']}"
        env["AGENT_RUNNER_CONFIG"] = str(self.config)
        env["ANICCA_USAGE_LEDGER"] = str(self.root / "usage.jsonl")
        command = [
            "python3", str(RUNNER), "--task-class", "tool-agent",
            "--schema", str(self.schema), "--evidence-dir", str(evidence),
            "--task-label", "x23", "--loop", "x23", "--workdir", str(self.root),
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


if __name__ == "__main__":
    unittest.main()
