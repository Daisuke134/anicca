import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "agent_runner.py"
TOKEN_BUDGET = ROOT / "token_budget.py"


def load_budget_module():
    spec = importlib.util.spec_from_file_location("token_budget_for_admission", TOKEN_BUDGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load token_budget")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BudgetAdmissionTest(unittest.TestCase):
    def test_task_reservation_allows_multiple_agents_to_share_one_pass_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "provider-was-launched"
            provider = bin_dir / "claude"
            provider.write_text(
                "#!/bin/sh\n"
                f"touch '{marker}'\n"
                "printf '%s' '{\"result\":\"{\\\"status\\\":\\\"ok\\\"}\"}'\n",
                encoding="utf-8",
            )
            provider.chmod(0o700)
            schema = root / "schema.json"
            schema.write_text(
                json.dumps(
                    {
                        "type": "object",
                        "required": ["status"],
                        "properties": {"status": {"const": "ok"}},
                    }
                ),
                encoding="utf-8",
            )
            prompt = root / "prompt.md"
            prompt.write_text(
                "Return the bounded contract JSON after completing the task.",
                encoding="utf-8",
            )
            config = root / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "task_classes": {
                            "tool-agent": {
                                "route": "test-budget-admission",
                                "timeout_seconds": 5,
                                "token_reservation": 20,
                                "candidates": [
                                    {
                                        "provider": "claude-direct",
                                        "model": "sonnet",
                                    }
                                ],
                            }
                        },
                        "providers": {
                            "claude-direct": {"executable": str(provider)}
                        },
                        "timeout_seconds": 5,
                    }
                ),
                encoding="utf-8",
            )

            budget = load_budget_module()
            budget_path = root / "token-budget.jsonl"
            ledger = budget.TokenBudgetLedger(budget_path)
            day = budget.budget_day_for(datetime.now(timezone.utc), "UTC")
            prior = ledger.reserve(
                event_id="prior-event",
                loop="job-search",
                scope_id="prior-pass",
                daily_scope="job-search-daily",
                day=day,
                reservation_tokens=70,
                pass_limit=100,
                daily_limit=100,
            )
            self.assertEqual(prior["status"], "allowed")
            ledger.settle(
                event_id="prior-event",
                actual_tokens=70,
                measurement="provider_reported",
            )

            evidence = root / "evidence"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "AGENT_RUNNER_CONFIG": str(config),
                "ANICCA_USAGE_LEDGER": str(root / "usage.jsonl"),
                "ANICCA_TOKEN_BUDGET_LEDGER": str(budget_path),
                "ANICCA_BUDGET_REQUIRED": "1",
                "ANICCA_BUDGET_SCOPE_ID": "current-pass",
                "ANICCA_PASS_TOKEN_BUDGET": "100",
                "ANICCA_LOOP_DAILY_TOKEN_BUDGET": "100",
                "ANICCA_BUDGET_DAILY_SCOPE": "job-search-daily",
                "ANICCA_BUDGET_DAY_TZ": "UTC",
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--task-class",
                    "tool-agent",
                    "--prompt-file",
                    str(prompt),
                    "--schema",
                    str(schema),
                    "--evidence-dir",
                    str(evidence),
                    "--task-label",
                    "budget-admission",
                    "--loop",
                    "job-search",
                    "--workdir",
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertTrue(marker.exists())
            self.assertNotEqual(result.returncode, 75, result.stderr)
            summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["attempt_count"], 1)
            self.assertEqual(summary["budget"]["status"], "allowed")
            self.assertEqual(summary["budget"]["reservation_tokens"], 20)
            self.assertEqual(summary["budget"]["daily_consumed_tokens"], 70)


if __name__ == "__main__":
    unittest.main()
