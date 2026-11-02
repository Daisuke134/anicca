import concurrent.futures
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock


try:
    hq = importlib.import_module("runtime.team_hq.main")
except ModuleNotFoundError:
    hq = None


class Slack:
    """Only the network boundary is replaced; queue and subprocesses are real."""

    def __init__(self):
        self.history = {"": {"ok": True, "messages": []}}
        self.threads = {}
        self.posts = []
        self.lose_post_response = False
        self.hide_posts = False
        self.error = False
        self.calls = []

    def call(self, method, **parameters):
        self.calls.append((method, dict(parameters)))
        if self.error:
            return {"ok": False, "error": "not_authed"}
        cursor = parameters.get("cursor", "")
        if method == "conversations.history":
            page = dict(self.history[cursor])
            if not self.hide_posts:
                page["messages"] = page.get("messages", []) + [
                    p for p in self.posts if not p.get("thread_ts")
                ]
            return page
        if method == "conversations.replies":
            page = dict(self.threads.get((parameters["ts"], cursor), {
                "ok": True, "messages": [],
            }))
            if not self.hide_posts:
                page["messages"] = page.get("messages", []) + [
                    p for p in self.posts if p.get("thread_ts") == parameters["ts"]
                ]
            return page
        if method == "chat.postMessage":
            message = dict(parameters, ts=f"9000.{len(self.posts) + 1:06d}")
            self.posts.append(message)
            if self.lose_post_response:
                raise TimeoutError("private provider details must not be printed")
            return {"ok": True, "ts": message["ts"], "channel": parameters["channel"]}
        raise AssertionError(method)


class HQTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(hq, "HQ runtime is not implemented")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "token").write_text("private-slack-token", encoding="utf-8")
        self.config = {
            "channel_id": "C_TEST", "token_file": str(self.root / "token"),
            "state_dir": str(self.root / "state"),
            "agents": [{"id": "codex", "mention": ["@codex", "<@U_CODEX>"],
                        "command": [sys.executable, "-c", "print('worked')"],
                        "cwd": str(self.root)}],
        }
        self.slack = Slack()
        self.runtime = hq.HQ(self.config, api=self.slack)

    def tasks(self):
        with self.runtime.connect() as database:
            return [dict(row) for row in database.execute("SELECT * FROM tasks ORDER BY created, id")]

    def message(self, ts="101.000001", text="@codex fix the real work", thread=None):
        message = {"ts": ts, "text": text}
        if thread:
            message["thread_ts"] = thread
        return message

    def enqueue(self):
        self.slack.history[""]["messages"] = [self.message()]
        self.runtime.receive()

    def test_http_200_ok_false_is_failure_without_secret(self):
        response = io.BytesIO(b'{"ok":false,"error":"not_authed"}')
        with mock.patch.object(hq.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(hq.HQError) as caught:
                hq.SlackAPI("private-slack-token").call("conversations.history", channel="C_TEST")
        self.assertNotIn("private-slack-token", str(caught.exception))

    def test_history_pagination_and_old_thread_reply_survive_cursor(self):
        self.slack.history = {
            "": {"ok": True, "messages": [self.message("1000.000001", "ordinary root")],
                 "response_metadata": {"next_cursor": "older"}},
            "older": {"ok": True, "messages": [self.message("10.000001", "old root")]},
        }
        self.runtime.receive()
        self.slack.history = {"": {"ok": True, "messages": []}}
        self.slack.threads[("10.000001", "")] = {
            "ok": True, "messages": [self.message("1100.000001", "<@U_CODEX> real reply", "10.000001")],
            "response_metadata": {"next_cursor": "reply2"},
        }
        self.slack.threads[("10.000001", "reply2")] = {
            "ok": True, "messages": [self.message("1101.000001", "@codex second reply", "10.000001")],
        }
        self.assertEqual(self.runtime.receive()["queued"], 2)
        self.assertEqual(self.runtime.receive()["queued"], 0)
        self.assertEqual([r["source_ts"] for r in self.tasks()], ["1100.000001", "1101.000001"])

    def test_legacy_done_import_prevents_replay_and_own_prefix_is_ignored(self):
        legacy = self.root / "legacy.json"
        legacy.write_text(json.dumps({"last": "100", "done": ["101.000001"]}))
        config = dict(self.config, state_dir=str(self.root / "imported"), legacy_state_file=str(legacy))
        runtime = hq.HQ(config, api=self.slack)
        self.slack.history[""]["messages"] = [
            self.message(), self.message("102.000001", "[codex] @codex own reply"),
            self.message("103.000001", "@codex new work"),
            self.message("90.000001", "@codex old processed history"),
        ]
        self.assertEqual(runtime.receive()["queued"], 1)
        legacy.write_text(json.dumps({"last": "100", "done": ["103.000001"]}))
        self.assertEqual(hq.HQ(config, api=self.slack).receive()["queued"], 0)

    def test_receive_error_does_not_advance_poll_cursor(self):
        self.slack.error = True
        with self.assertRaises(hq.HQError):
            self.runtime.receive()
        self.assertIsNone(self.runtime.status()["last_poll"])

    def test_receive_preserves_bounded_page_continuations_and_rotates_threads(self):
        self.config.update(max_history_pages=1, max_threads_per_poll=1, max_thread_pages=1)
        self.runtime = hq.HQ(self.config, api=self.slack)
        self.slack.history = {
            "": {"ok": True, "messages": [self.message("20.000001", "first root")],
                 "response_metadata": {"next_cursor": "second"}},
            "second": {"ok": True, "messages": [self.message("10.000001", "second root")]},
        }
        self.runtime.receive()
        self.runtime.receive()
        history_calls = [parameters for method, parameters in self.slack.calls if method == "conversations.history"]
        self.assertEqual(len(history_calls), 2)
        self.assertEqual(history_calls[1].get("cursor"), "second")
        thread_calls = [parameters["ts"] for method, parameters in self.slack.calls if method == "conversations.replies"]
        self.assertEqual(thread_calls, ["20.000001", "10.000001"])

    def test_initial_history_is_limited_to_configured_lookback(self):
        self.config["lookback_days"] = 1
        self.runtime = hq.HQ(self.config, api=self.slack)
        with mock.patch.object(hq.time, "time", return_value=2000000):
            self.runtime.receive()
        self.assertEqual(self.slack.calls[0][1]["oldest"], "1913600")

    def test_plain_mention_does_not_route_a_different_identifier(self):
        self.slack.history[""]["messages"] = [self.message(text="@codex_other is a different recipient")]
        self.assertEqual(self.runtime.receive()["queued"], 0)

    def test_duplicate_agent_ids_are_rejected_before_task_routing(self):
        self.config["agents"].append(dict(self.config["agents"][0], command=["other-agent"]))
        with self.assertRaises(hq.HQError):
            hq.HQ(self.config, api=self.slack)

    def test_receiver_does_not_wait_on_execution_lock(self):
        self.slack.history[""]["messages"] = [self.message()]
        with self.runtime.lock("work"):
            self.assertEqual(self.runtime.receive()["queued"], 1)

    def test_atomic_claim_never_assigns_one_card_twice(self):
        self.enqueue()
        barrier = threading.Barrier(2)

        def claim():
            runtime = hq.HQ(self.config, api=self.slack)
            barrier.wait()
            return runtime.claim()

        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            claims = list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(sum(row is not None for row in claims), 1)
        task = self.tasks()[0]
        self.assertEqual(task["status"], "working")
        self.assertEqual(task["owner_id"], "codex")

    def test_worker_exit_failure_is_failed_not_success_and_never_reruns(self):
        script = self.root / "fail.py"
        script.write_text("import pathlib,sys\np=pathlib.Path('calls')\np.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint('private-slack-token',file=sys.stderr)\nsys.exit(7)\n")
        self.config["agents"][0]["command"] = [sys.executable, str(script)]
        self.runtime = hq.HQ(self.config, api=self.slack)
        self.enqueue()
        result = self.runtime.work()
        self.assertTrue(result["ok"])
        self.assertEqual(result.get("execution_status"), "failed")
        row = self.tasks()[0]
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["exit_code"], 7)
        self.assertTrue(Path(row["result_path"]).is_file())
        self.runtime.work()
        self.assertEqual((self.root / "calls").read_text(), "x")
        self.assertNotIn("private-slack-token", json.dumps(self.slack.posts))

    def test_success_uses_prompt_stdin_and_artifact_without_adding_flags(self):
        script = self.root / "success.py"
        script.write_text("import pathlib,sys,json\nassert len(sys.argv)==2\nprompt=sys.stdin.read()\npathlib.Path('prompt').write_text(prompt)\npathlib.Path(sys.argv[1]).write_text('実仕事の実行結果\\nSTATE {\"status\":\"reported\",\"next\":\"公式照合\",\"proof\":[\"artifact\"]}')\n")
        self.config["agents"][0]["command"] = [sys.executable, str(script), "{artifact}"]
        self.runtime = hq.HQ(self.config, api=self.slack)
        self.enqueue()
        self.assertTrue(self.runtime.work()["ok"])
        row = self.tasks()[0]
        self.assertEqual(row["status"], "succeeded")
        self.assertEqual(row["reply_state"], "posted")
        receipt = json.loads(Path(row["result_path"]).read_text())
        self.assertEqual(receipt["business_outcome"], "unverified")
        self.assertEqual(receipt["agent_state"]["next"], "公式照合")
        self.assertIn("BOARD", (self.root / "prompt").read_text())
        self.assertEqual(self.runtime.status()["tasks"][0].get("proof"), ["artifact"])

    def test_artifact_symlink_cannot_overwrite_another_file(self):
        victim = self.root / "preserve"
        victim.write_text("preserved")
        script = self.root / "symlink.py"
        script.write_text("import pathlib,sys\npathlib.Path(sys.argv[1]).symlink_to(pathlib.Path('preserve').resolve())\n")
        self.config["agents"][0]["command"] = [sys.executable, str(script), "{artifact}"]
        self.runtime = hq.HQ(self.config, api=self.slack)
        self.enqueue()
        result = self.runtime.work()
        self.assertEqual(result.get("execution_status"), "failed")
        self.assertEqual(victim.read_text(), "preserved")

    def test_marker_only_echo_is_not_an_official_reply_receipt(self):
        self.enqueue()
        task = self.tasks()[0]
        self.slack.hide_posts = True
        self.slack.threads[(task["thread_ts"], "")] = {
            "ok": True, "messages": [self.message("102.000001", task["marker"], task["thread_ts"])],
        }
        self.assertFalse(self.runtime.work()["ok"])
        self.assertEqual(self.tasks()[0]["reply_state"], "post_unknown")

    def test_unknown_post_response_is_reconciled_without_resend_or_rerun(self):
        self.enqueue()
        self.slack.lose_post_response = True
        self.slack.hide_posts = True
        self.assertFalse(self.runtime.work()["ok"])
        self.assertEqual(self.tasks()[0]["reply_state"], "post_unknown")
        self.assertEqual(len(self.slack.posts), 1)
        self.slack.hide_posts = False
        self.assertTrue(self.runtime.work()["ok"])
        self.assertEqual(self.tasks()[0]["reply_state"], "posted")
        self.assertEqual(len(self.slack.posts), 1)

    def test_unknown_reply_does_not_stop_a_different_queued_task(self):
        self.enqueue()
        self.slack.lose_post_response = True
        self.slack.hide_posts = True
        self.runtime.work()
        self.slack.history[""]["messages"] = [self.message("102.000001", "@codex separate work")]
        self.runtime.receive()
        self.slack.lose_post_response = False
        self.slack.hide_posts = False
        # Keep the first marker hidden while allowing the new post's readback.
        first = self.slack.posts[0]
        self.slack.posts = []
        result = self.runtime.work()
        self.assertTrue(result["ok"])
        rows = self.tasks()
        self.assertEqual(rows[0]["reply_state"], "post_unknown")
        self.assertEqual(rows[1]["reply_state"], "posted")
        self.assertNotEqual(result["task_id"], rows[0]["id"])
        self.assertEqual(len(self.slack.posts), 1)
        self.assertNotEqual(first["text"], self.slack.posts[0]["text"])

    def test_working_crash_is_handoff_required_and_never_reassigned(self):
        self.enqueue()
        self.runtime.claim()
        self.runtime.work()
        row = self.tasks()[0]
        self.assertEqual(row["status"], "interrupted")
        self.assertIn("handoff", row["checkpoint"])
        self.assertEqual(self.runtime.status()["handoff_required"], 1)

    def test_execution_receipt_recovers_reply_after_process_completion_crash(self):
        self.enqueue()
        with mock.patch.object(self.runtime, "finish", side_effect=RuntimeError("crash after receipt")):
            with self.assertRaises(RuntimeError):
                self.runtime.work()
        self.assertEqual(self.tasks()[0]["status"], "working")
        self.assertTrue(self.runtime.work()["ok"])
        self.assertEqual(self.tasks()[0]["status"], "succeeded")
        self.assertEqual(len(self.slack.posts), 1)

    def test_schedule_slot_is_deduplicated_and_status_exposes_owner_checkpoint(self):
        self.config["schedules"] = [
            {"id": "hourly", "agent": "codex", "interval_seconds": 3600, "prompt": "収益仕事を選んで実行"},
            {"id": "manager", "agent": "codex", "hours_jst": [9, 14, 21], "prompt": "Managerの仕事"},
        ]
        self.runtime = hq.HQ(self.config, api=self.slack)
        self.assertEqual(self.runtime.schedule(now=1793577600)["queued"], 2)  # 2026-11-02 09:00 JST
        self.assertEqual(self.runtime.schedule(now=1793577601)["queued"], 0)
        status = self.runtime.status()
        self.assertEqual(status["counts"]["queued"], 2)
        self.assertTrue(all(row["id"] and row["owner_id"] and row["updated"] and row["checkpoint"] for row in status["tasks"]))

    def test_timeout_stops_process_group_and_records_unknown_effect(self):
        script = self.root / "sleep.py"
        script.write_text("import subprocess,sys,time\np=subprocess.Popen([sys.executable,'-c',\"import time,pathlib;time.sleep(1);pathlib.Path('child-effect').write_text('bad')\"])\ntime.sleep(30)\n")
        self.config["agents"][0]["command"] = [sys.executable, str(script)]
        self.config["timeout_seconds"] = 0.1
        self.runtime = hq.HQ(self.config, api=self.slack)
        self.enqueue()
        result = self.runtime.work()
        self.assertTrue(result["ok"])
        self.assertEqual(result.get("execution_status"), "failed")
        self.assertEqual(self.tasks()[0]["checkpoint"], "timeout_handoff_required")
        # A second worker never runs the same task even after a timeout.
        self.runtime.work()
        self.assertIsNone(self.runtime.claim())
        time.sleep(1.1)
        self.assertFalse((self.root / "child-effect").exists())

    def test_cli_config_path_and_json_status_are_portable(self):
        config_file = self.root / "team.json"
        config_file.write_text(json.dumps(self.config))
        result = subprocess.run([sys.executable, "-m", "runtime.team_hq.main", "status"],
                                env=dict(os.environ, TEAM_HQ_CONFIG=str(config_file)),
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["counts"], {})
        self.assertNotIn("private-slack-token", result.stdout + result.stderr)

    def test_verified_post_hint_requires_marker_readback_and_idle_is_no_effect(self):
        hint = self.root / "hint.json"
        environment = {"LIFE_MANAGER_RESULT_HINT_PATH": str(hint),
                       "LIFE_MANAGER_LOOP_ID": "team-hq-work", "LIFE_MANAGER_OCCURRENCE_ID": "work:one"}
        with mock.patch.dict(os.environ, environment):
            self.runtime.work()
            self.assertEqual(json.loads(hint.read_text())["status"], "no_effect")
            self.enqueue()
            self.runtime.work()
            receipt = json.loads(hint.read_text())
        self.assertEqual(receipt["kind"], "team_hq_result")
        self.assertEqual(receipt["status"], "verified")
        self.assertEqual(receipt["message_ts"], "9000.000001")
        self.assertEqual(hint.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
