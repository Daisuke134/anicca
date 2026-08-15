"""A4 wiring: the retainer lane must actually FIRE, and must never take the pass down.

`retainer_followthrough()` built a queue, logged a count and returned. Everything
underneath it -- the scheduler, the booking ledger, the browser driver -- existed and
was tested, and none of it was reachable from production. A lane that cannot be
reached is indistinguishable from a lane that does not exist: the 三者面談 offer sat
unanswered for a day while the code that answers it passed its own tests.

Two properties are contracted here, and they pull in opposite directions:

1. the pass INVOKES the executor with the queue it just built -- otherwise nothing
   ever happens;
2. the executor FAILING does not fail the pass -- this lane rides along with paid
   delivery, and a follow-through tab changing its markup must never stop money work.

The seam is the `retainer_lane.py run` CLI, so this test stubs that one script and
asserts on how the pass calls it. The executor's own semantics are contracted in
test_retainer_followthrough.py.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


GIG_WORK = Path(__file__).resolve().parents[1]

SNAPSHOT = {
    "captured_at": "2026-07-30T23:00:00+00:00",
    "orders": [],
    "quotes": [],
    "inquiries": [],
    "retainer_applications": [
        {
            "application_id": "01KYPJ0M0ACF4DBAFSJVFN9K24",
            "thread_url": (
                "https://coconala.com/mypage/job_matching/job_talkroom/"
                "01KYPJ0M0ACF4DBAFSJVFN9K24"
            ),
            "title": "【長期・在宅】SNS投稿・更新サポートスタッフ募集",
            "client": "買い手F",
            "last_message_at": "2026/07/30 00:32",
            "last_message_body": "一度面談の機会を頂きたく",
            "status": "面談調整中",
        }
    ],
    "retainer_collector_error": None,
}


class RetainerLaneIsWiredTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gig-retainer-wiring.")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.gig = self.home / "life-manager" / "skills" / "gig-work"
        for directory in (
            self.gig / "scripts",
            self.gig / "schemas",
            self.gig / "config" / "connectors",
            self.home / "life-manager" / "skills" / "agent-runner",
            self.home / "anicca" / "skills" / "browser" / "scripts",
            self.home / "gig",
        ):
            directory.mkdir(parents=True, exist_ok=True)
        for name in ("gig_pass.sh", "passprep.py", "strategy.default.json"):
            shutil.copy(GIG_WORK / name, self.gig / name)
        for name in (
            "delivery_queue.py", "delivery_cadence.py", "delivery_project.py",
            "project_ledger.py", "delivery_identity.py", "reply_queue.py",
            "connector_outbox.py", "retainer_thread.py",
        ):
            shutil.copy(GIG_WORK / "scripts" / name, self.gig / "scripts" / name)
        shutil.copy(
            GIG_WORK / "config" / "connectors" / "coconala.json",
            self.gig / "config" / "connectors" / "coconala.json",
        )
        shutil.copy(
            GIG_WORK / "schemas" / "gig_step_result.schema.json",
            self.gig / "schemas" / "gig_step_result.schema.json",
        )
        self.snapshot = self.root / "snapshot.json"
        self.snapshot.write_text(json.dumps(SNAPSHOT, ensure_ascii=False), encoding="utf-8")
        self.calls = self.root / "retainer-calls.jsonl"
        os.chmod(self.gig / "gig_pass.sh", 0o755)

    def _install_stub_lane(self, *, run_exit_code: int) -> None:
        """Stand in for the real lane: record every invocation, build a real queue."""
        stub = f'''#!/usr/bin/env python3
import json, os, sys
argv = sys.argv[1:]
with open(os.environ["RETAINER_CALL_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(argv, ensure_ascii=False) + "\\n")


def flag(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


if argv and argv[0] == "build":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import retainer_thread
    snapshot = json.load(open(flag("--snapshot"), encoding="utf-8"))
    queue = retainer_thread.build_queue(snapshot)
    with open(flag("--output"), "w", encoding="utf-8") as handle:
        json.dump(queue, handle, ensure_ascii=False)
    print(json.dumps({{"status": queue["status"], "items": len(queue["items"])}}))
    raise SystemExit(0)

if argv and argv[0] == "run":
    output = flag("--output")
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            json.dump({{"status": "completed", "model_calls": 0}}, handle)
    raise SystemExit({run_exit_code})

raise SystemExit(64)
'''
        target = self.gig / "scripts" / "retainer_lane.py"
        target.write_text(stub, encoding="utf-8")
        os.chmod(target, 0o755)

    def _run_pass(self) -> subprocess.CompletedProcess:
        environment = dict(os.environ)
        environment.update({
            "HOME": str(self.home),
            "GIG_WORKER_LEASE_ACTIVE": "1",
            "GIG_QUEUE_FIXTURE": str(self.snapshot),
            "GIG_TODAY": "2026-07-31",
            "GIG_PASS_ID": "wiring",
            "GIG_LOCK_DIR": str(self.root / "lock.d"),
            "RETAINER_CALL_LOG": str(self.calls),
        })
        return subprocess.run(
            ["bash", str(self.gig / "gig_pass.sh")],
            capture_output=True, text=True, timeout=600, env=environment,
        )

    def _calls(self) -> list[list[str]]:
        if not self.calls.exists():
            return []
        return [
            json.loads(line)
            for line in self.calls.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_the_pass_fires_the_lane_against_the_queue_it_just_built(self):
        self._install_stub_lane(run_exit_code=0)
        self._run_pass()
        runs = [call for call in self._calls() if call and call[0] == "run"]
        self.assertEqual(len(runs), 1, f"lane was never fired; calls={self._calls()}")
        argv = runs[0]
        self.assertIn("--queue", argv)
        queue_path = argv[argv.index("--queue") + 1]
        self.assertTrue(queue_path.endswith("retainer-queue.json"), queue_path)
        queue = json.loads(Path(queue_path).read_text(encoding="utf-8"))
        self.assertEqual(
            [item["talkroom_id"] for item in queue["items"]],
            ["01KYPJ0M0ACF4DBAFSJVFN9K24"],
        )
        # The lane keeps its own budget; it must never be handed the reply lane's.
        self.assertIn("--max-model-calls", argv)
        self.assertEqual(argv[argv.index("--max-model-calls") + 1], "1")

    def test_a_failing_lane_does_not_take_the_pass_down(self):
        self._install_stub_lane(run_exit_code=1)
        completed = self._run_pass()
        runs = [call for call in self._calls() if call and call[0] == "run"]
        self.assertEqual(len(runs), 1, "lane was never fired")
        text = completed.stderr or ""
        self.assertIn("RETAINER_FOLLOWTHROUGH", text)
        # Degraded, not fatal: the lane says so itself and no pass failure is recorded.
        self.assertIn("degraded", text)
        failures = self.home / "gig" / "failures.jsonl"
        recorded = failures.read_text(encoding="utf-8") if failures.exists() else ""
        self.assertNotIn("retainer", recorded)


if __name__ == "__main__":
    unittest.main()
