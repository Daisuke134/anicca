import fcntl
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DETECTOR = ROOT / "scripts" / "reply_detector.py"


class ReplyDetectorTokenBudgetTest(unittest.TestCase):
    """X20: the detector composes buyer replies outside any pass. Before this it
    exported no budget env, so agent_runner recorded budget_not_configured and
    never charged those calls -- 47 of them between 07-23 and 07-25."""

    def load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("reply_detector_x20", DETECTOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_detector_installs_its_own_budget_scope(self):
        environ = {}
        self.load().install_token_budget(environ, run_id="reply-detector-42-7")
        self.assertEqual(environ["ANICCA_BUDGET_SCOPE_ID"], "reply-detector-42-7")
        self.assertEqual(environ["ANICCA_BUDGET_DAILY_SCOPE"], "gig-reply-detector")
        self.assertEqual(environ["ANICCA_PASS_TOKEN_BUDGET"], "65536")
        self.assertEqual(environ["ANICCA_LOOP_DAILY_TOKEN_BUDGET"], "1048576")
        self.assertEqual(environ["ANICCA_BUDGET_REQUIRED"], "1")

    def test_launchagent_overrides_are_honoured(self):
        environ = {
            "GIG_REPLY_PASS_TOKEN_BUDGET": "1234",
            "GIG_DAILY_TOKEN_BUDGET": "5678",
            "GIG_BUDGET_DAILY_SCOPE": "gig-other",
        }
        self.load().install_token_budget(environ, run_id="run-1")
        self.assertEqual(environ["ANICCA_PASS_TOKEN_BUDGET"], "1234")
        self.assertEqual(environ["ANICCA_LOOP_DAILY_TOKEN_BUDGET"], "5678")
        self.assertEqual(environ["ANICCA_BUDGET_DAILY_SCOPE"], "gig-other")

    def test_an_inherited_pass_scope_is_not_overwritten(self):
        """When a pass spawns the detector, the pass owns the budget."""
        environ = {"ANICCA_BUDGET_SCOPE_ID": "pass-99",
                   "ANICCA_BUDGET_DAILY_SCOPE": "gig-pass"}
        self.load().install_token_budget(environ, run_id="run-1")
        self.assertEqual(environ["ANICCA_BUDGET_SCOPE_ID"], "pass-99")
        self.assertEqual(environ["ANICCA_BUDGET_DAILY_SCOPE"], "gig-pass")


class ReplyDetectorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence = self.root / "evidence"
        self.lock = self.root / "detector.lock"
        self.calls = self.root / "calls.jsonl"
        self.collector = self.script("collector.py", """
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({'captured_at':'2026-07-22T00:00:00+00:00','orders':[],'quotes':[],'inquiries':[]}),encoding='utf-8')
        """)
        self.queue = self.script("queue.py", """
            import json,os,sys
            from pathlib import Path
            args=sys.argv[1:]
            with Path(os.environ['DETECTOR_CALLS']).open('a') as f: f.write(json.dumps({'step':'queue','command':args[0]})+'\\n')
            if args[0]=='build':
                output=Path(args[args.index('--output')+1])
                output.write_text(json.dumps({'status':'queue_empty','errors':[],'items':[]}),encoding='utf-8')
        """)
        self.lane = self.script("lane.py", """
            import json,os,sys
            from pathlib import Path
            args=sys.argv[1:]
            with Path(os.environ['DETECTOR_CALLS']).open('a') as f:
                f.write(json.dumps({'step':'lane','hidden_browser':'--hidden-browser' in args})+'\\n')
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({'status':'completed','replied':0,'reconciled':0,'requeued':0,'reconcile_pending':0,'skipped':0,'errors':[]}),encoding='utf-8')
        """)
        self.reporter = self.script("reporter.py", """
            import json,os,sys
            from pathlib import Path
            with Path(os.environ['DETECTOR_CALLS']).open('a') as f: f.write(json.dumps({'step':'report'})+'\\n')
            raise SystemExit(int(os.environ.get('REPORTER_RC','0')))
        """)

    def tearDown(self):
        self.temp.cleanup()

    def script(self, name, source):
        path = self.root / name
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return path

    def command(self, output=None):
        return [
            sys.executable, str(DETECTOR),
            "--evidence-dir", str(self.evidence),
            "--lock-file", str(self.lock),
            "--database", str(self.root / "outbox.sqlite3"),
            "--manifest", str(self.root / "manifest.json"),
            "--runner", str(self.root / "must-not-run-model"),
            "--schema", str(self.root / "must-not-read-schema"),
            "--cdp-helper", str(self.root / "must-not-open-browser"),
            "--snapshot-script", str(self.collector),
            "--queue-script", str(self.queue),
            "--lane-script", str(self.lane),
            "--telegram-report-script", str(self.reporter),
            "--telegram-database", str(self.root / "telegram.sqlite3"),
            "--output", str(output or self.root / "detector-result.json"),
        ]

    def run_detector(self, output=None):
        env = dict(os.environ, DETECTOR_CALLS=str(self.calls))
        return subprocess.run(
            self.command(output), capture_output=True, text=True, check=False, env=env,
        )

    def test_empty_detection_runs_bounded_pipeline_and_writes_owner_only_summary(self):
        output = self.root / "detector-result.json"
        completed = self.run_detector(output)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["trigger"], "fallback")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(calls, [
            {"step": "queue", "command": "build"},
            {"step": "queue", "command": "enqueue"},
            {"step": "lane", "hidden_browser": False},
        ])
        self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)

    def test_blocked_rejection_is_projected_without_triggering_reporter(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':0,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'blocked':1,'skipped':0,
                'errors':[{
                    'talkroom_id':'42','status':'blocked',
                    'errors':['submit_rejected_sending_unavailable'],
                }],
                'events':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["blocked"], 1)
        self.assertEqual(result["events"], [])
        self.assertEqual(result["errors"][0]["status"], "blocked")
        self.assertFalse(self.calls.exists() and '"step": "report"' in self.calls.read_text())

    def test_fallback_collector_uses_hidden_dom_only_mode(self):
        self.collector.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            assert '--hidden-no-screenshot' in args
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'captured_at':'2026-07-22T00:00:00+00:00',
                'orders':[],'quotes':[],'inquiries':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_concurrent_trigger_returns_busy_without_running_pipeline(self):
        self.lock.touch(mode=0o600)
        with self.lock.open("r+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["status"], "busy")
        self.assertFalse(self.calls.exists())

    def test_verified_event_invokes_reporter_but_report_failure_does_not_fail_reply(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':1,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'skipped':0,'errors':[],
                'events':[{'action_id':1,'revision':1,'talkroom_id':'42','origin_at':'2026-07-22T00:00:00+00:00','seller_sent_at':'2026-07-22T00:01:00+00:00','status':'replied'}],
            }),encoding='utf-8')
        """), encoding="utf-8")
        env = dict(os.environ, DETECTOR_CALLS=str(self.calls), REPORTER_RC="9")
        completed = subprocess.run(
            self.command(), capture_output=True, text=True, check=False, env=env,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["replied"], 1)
        self.assertEqual(result["events"][0]["talkroom_id"], "42")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertIn({"step": "report"}, calls)

    def test_collector_failure_is_bounded_failure_and_stops_pipeline(self):
        self.collector.write_text("raise SystemExit(7)\n", encoding="utf-8")
        completed = self.run_detector()

        self.assertEqual(completed.returncode, 1)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_step"], "collect")
        self.assertFalse(self.calls.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
