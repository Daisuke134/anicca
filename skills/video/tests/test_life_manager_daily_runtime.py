#!/usr/bin/env python3
import json
import os
import plistlib
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DAILY = ROOT / "skills/life-manager/life-manager-daily.sh"
PLIST = ROOT / "skills/life-manager/launchd/ai.anicca.life-manager-daily.plist"


def executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class LifeManagerDailyRuntimeTest(unittest.TestCase):
    def test_launchd_contract_keeps_existing_label_and_1015_jst_cadence(self):
        with PLIST.open("rb") as handle:
            data = plistlib.load(handle)
        self.assertEqual(data["Label"], "ai.anicca.life-manager-daily")
        self.assertEqual(
            data["ProgramArguments"],
            [
                "/bin/bash",
                "/Users/operator/Projects/life-manager-main/skills/life-manager/life-manager-daily.sh",
            ],
        )
        self.assertEqual(data["StartCalendarInterval"], {"Hour": 10, "Minute": 15})
        self.assertEqual(data["ProcessType"], "Background")
        self.assertEqual(data.get("EnvironmentVariables", {}), {})

    def run_daily(self, generator_rc=0, distributor_rc=0, self_improver_rc=0, runner_rc=0):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        home = root / "home"
        (home / ".openclaw/logs").mkdir(parents=True)
        generator = executable(
            root / "generator",
            "#!/usr/bin/env bash\n"
            f"[ {generator_rc} -eq 0 ] || exit {generator_rc}\n"
            "printf '%s\\n' '{\"selected_id\":\"A02\",\"output\":\"/tmp/exact-daily.mp4\",\"duration_seconds\":34.656}'\n",
        )
        runner = executable(
            root / "runner",
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$@\" >\"$CAPTURE_ARGS\"\n"
            "cat >\"$CAPTURE_PROMPT\"\n"
            "evidence=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  if [ \"$1\" = --evidence-dir ]; then evidence=$2; shift 2; else shift; fi\n"
            "done\n"
            "mkdir -p \"$evidence\"\n"
            f"printf '%s\\n' '{{\"status\":\"{'success' if runner_rc == 0 else 'failed'}\",\"selected_provider\":\"codex\","
            f"\"selected_model\":\"gpt-5.6-luna\",\"selected_effort\":\"medium\",\"attempt_count\":1,"
            f"\"usage\":{{\"provider_cost_usd\":0,\"cost_basis\":\"subscription\"}}}}' >\"$evidence/summary.json\"\n"
            f"exit {runner_rc}\n",
        )
        distributor = executable(
            root / "distributor",
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$@\" >\"$CAPTURE_DISTRIBUTOR_ARGS\"\n"
            f"[ {distributor_rc} -eq 0 ] || exit {distributor_rc}\n"
            "printf '%s\\n' '{\"creative_id\":\"A02\",\"instagram_url\":\"https://www.instagram.com/reel/IGREAL/\","
            "\"tiktok_url\":\"https://www.tiktok.com/@life/video/123\"}'\n",
        )
        self_improver = executable(
            root / "self-improver",
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$@\" >\"$CAPTURE_SELF_IMPROVER_ARGS\"\n"
            f"[ {self_improver_rc} -eq 0 ] || exit {self_improver_rc}\n"
            "printf '%s\\n' '{\"status\":\"started\",\"day_index\":1,\"creative_id\":\"A02\","
            "\"next_creative_id\":\"A03\",\"next_change_reason\":\"baseline established from real public metrics\"}'\n",
        )
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "LM_VIDEO_GENERATOR": str(generator),
                "RUN_AGENT_BIN": str(runner),
                "LM_VIDEO_DISTRIBUTOR": str(distributor),
                "LM_MARKETING_SELF_IMPROVER": str(self_improver),
                "LM_DAILY_RUN_LEDGER": str(root / "daily-runs.jsonl"),
                "LM_DAILY_USAGE_LEDGER": str(root / "usage.jsonl"),
                "CAPTURE_ARGS": str(root / "args"),
                "CAPTURE_PROMPT": str(root / "prompt"),
                "CAPTURE_DISTRIBUTOR_ARGS": str(root / "distributor-args"),
                "CAPTURE_SELF_IMPROVER_ARGS": str(root / "self-improver-args"),
            }
        )
        result = subprocess.run(["bash", str(DAILY)], env=env, text=True, capture_output=True)
        return result, root

    def test_success_uses_luna_marketing_route_and_records_cost_provenance(self):
        result, root = self.run_daily()
        self.assertEqual(result.returncode, 0, result.stderr)
        args = (root / "args").read_text(encoding="utf-8")
        self.assertIn("--task-class\nmarketing-agent\n", args)
        prompt = (root / "prompt").read_text(encoding="utf-8")
        self.assertIn("/tmp/exact-daily.mp4", prompt)
        self.assertIn("A02", prompt)
        self.assertIn("DETERMINISTIC DISTRIBUTION COMPLETE", prompt)
        self.assertIn("https://www.instagram.com/reel/IGREAL/", prompt)
        self.assertIn("https://www.tiktok.com/@life/video/123", prompt)
        self.assertIn("not repost either platform", prompt)
        self.assertIn("SELF-IMPROVEMENT LEDGER RECORDED", prompt)
        self.assertIn("baseline established from real public metrics", prompt)
        self.assertIn("Do not invoke life-manager-daily.sh", prompt)
        self.assertIn("Do not inspect, monitor, or wait for this active process", prompt)
        distribution_args = (root / "distributor-args").read_text(encoding="utf-8")
        self.assertIn("--creative-id\nA02\n", distribution_args)
        self.assertIn("--video\n/tmp/exact-daily.mp4\n", distribution_args)
        self_improver_args = (root / "self-improver-args").read_text(encoding="utf-8")
        self.assertEqual(self_improver_args, "\n")
        row = json.loads((root / "daily-runs.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(row["status"], "success")
        self.assertEqual(row["model"], "gpt-5.6-luna")
        self.assertEqual(row["creative_id"], "A02")
        self.assertEqual(row["creative_output"], "/tmp/exact-daily.mp4")
        self.assertEqual(row["provider_cost_usd"], 0)
        self.assertEqual(row["marginal_cost_usd"], 0)
        self.assertEqual(row["cost_tier"], "subscription")
        self.assertEqual((root / "daily-runs.jsonl").stat().st_mode & 0o777, 0o600)
        self.assertTrue((root / "home/.openclaw/state/.life-manager-core-last-pass").exists())

    def test_generator_failure_propagates_exact_nonzero_without_runner(self):
        result, root = self.run_daily(generator_rc=17)
        self.assertEqual(result.returncode, 17)
        self.assertFalse((root / "args").exists())
        self.assertFalse((root / "home/.openclaw/state/.life-manager-core-last-pass").exists())

    def test_recursive_invocation_fails_before_generator_or_runner(self):
        result, root = self.run_daily()
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(root / "home"),
                "LM_DAILY_ACTIVE": "1",
                "LM_VIDEO_GENERATOR": str(root / "generator"),
                "RUN_AGENT_BIN": str(root / "runner"),
                "LM_VIDEO_DISTRIBUTOR": str(root / "distributor"),
                "CAPTURE_ARGS": str(root / "recursive-args"),
                "CAPTURE_PROMPT": str(root / "recursive-prompt"),
            }
        )
        recursive = subprocess.run(["bash", str(DAILY)], env=env, text=True, capture_output=True)
        self.assertEqual(recursive.returncode, 73)
        self.assertFalse((root / "recursive-args").exists())

    def test_generation_only_mode_keeps_distribution_locked_for_9c(self):
        result, root = self.run_daily()
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(root / "home"),
                "LM_DAILY_GENERATION_ONLY": "1",
                "LM_VIDEO_GENERATOR": str(root / "generator"),
                "RUN_AGENT_BIN": str(root / "runner"),
                "LM_DAILY_RUN_LEDGER": str(root / "generation-only-runs.jsonl"),
                "LM_DAILY_USAGE_LEDGER": str(root / "generation-only-usage.jsonl"),
                "CAPTURE_ARGS": str(root / "generation-only-args"),
                "CAPTURE_PROMPT": str(root / "generation-only-prompt"),
                "CAPTURE_DISTRIBUTOR_ARGS": str(root / "generation-only-distributor-args"),
            }
        )
        generation_only = subprocess.run(["bash", str(DAILY)], env=env, text=True, capture_output=True)
        self.assertEqual(generation_only.returncode, 0, generation_only.stderr)
        prompt = (root / "generation-only-prompt").read_text(encoding="utf-8")
        self.assertIn("GENERATION-ONLY 9b", prompt)
        self.assertIn("Do not post", prompt)
        self.assertIn("ffprobe", prompt)
        self.assertIn("full decode", prompt)
        self.assertIn(str(ROOT / "skills/video/daily-lm-video/creative-bank.jsonl"), prompt)
        self.assertIn(str(root / "home/.openclaw/state/lm-video/daily-render-state.jsonl"), prompt)
        self.assertIn("Do not search", prompt)
        self.assertFalse((root / "generation-only-distributor-args").exists())
        self.assertFalse((root / "generation-only-self-improver-args").exists())

    def test_distribution_failure_propagates_without_invoking_agent(self):
        result, root = self.run_daily(distributor_rc=29)
        self.assertEqual(result.returncode, 29)
        self.assertTrue((root / "distributor-args").exists())
        self.assertFalse((root / "args").exists())
        self.assertFalse((root / "home/.openclaw/state/.life-manager-core-last-pass").exists())

    def test_self_improver_failure_propagates_without_invoking_agent(self):
        result, root = self.run_daily(self_improver_rc=31)
        self.assertEqual(result.returncode, 31)
        self.assertTrue((root / "self-improver-args").exists())
        self.assertFalse((root / "args").exists())
        self.assertFalse((root / "home/.openclaw/state/.life-manager-core-last-pass").exists())

    def test_runner_failure_and_timeout_propagate_and_do_not_touch_success_marker(self):
        for runner_rc in (23, 124):
            with self.subTest(runner_rc=runner_rc):
                result, root = self.run_daily(runner_rc=runner_rc)
                self.assertEqual(result.returncode, runner_rc)
                row = json.loads((root / "daily-runs.jsonl").read_text(encoding="utf-8"))
                self.assertEqual(row["status"], "failed")
                self.assertEqual(row["exit_code"], runner_rc)
                self.assertFalse((root / "home/.openclaw/state/.life-manager-core-last-pass").exists())


if __name__ == "__main__":
    unittest.main()
