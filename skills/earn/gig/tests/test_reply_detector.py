import fcntl
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
DETECTOR = ROOT / "scripts" / "reply_detector.py"


class ReplyDetectorTokenBudgetTest(unittest.TestCase):
    """The direct owner removes inherited ANICCA caps before composing replies."""

    def load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("reply_detector_x20", DETECTOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_detector_removes_pass_and_daily_budget_caps(self):
        environ = {}
        self.load().install_token_budget(environ, run_id="reply-detector-42-7")
        self.assertNotIn("ANICCA_BUDGET_SCOPE_ID", environ)
        self.assertNotIn("ANICCA_PASS_TOKEN_BUDGET", environ)
        self.assertNotIn("ANICCA_LOOP_DAILY_TOKEN_BUDGET", environ)
        self.assertNotIn("ANICCA_BUDGET_REQUIRED", environ)

    def test_inherited_budget_is_removed_from_reply_children(self):
        environ = {
            "ANICCA_BUDGET_SCOPE_ID": "pass-99",
            "ANICCA_PASS_TOKEN_BUDGET": "1",
            "ANICCA_LOOP_DAILY_TOKEN_BUDGET": "1",
            "ANICCA_BUDGET_DAILY_SCOPE": "gig-pass",
            "ANICCA_BUDGET_REQUIRED": "1",
        }
        self.load().install_token_budget(environ, run_id="run-1")
        self.assertFalse(any(key.startswith("ANICCA_BUDGET_") for key in environ))
        self.assertNotIn("ANICCA_PASS_TOKEN_BUDGET", environ)
        self.assertNotIn("ANICCA_LOOP_DAILY_TOKEN_BUDGET", environ)


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
            with Path(os.environ['DETECTOR_CALLS']).open('a') as f:
                record={'step':'report','command':sys.argv[1]}
                if os.environ.get('REPORTER_INSPECT'):
                    events=Path(sys.argv[sys.argv.index('--events')+1])
                    payload=json.loads(events.read_text(encoding='utf-8'))
                    record.update(status=payload.get('status'), failed_step=payload.get('failed_step'))
                f.write(json.dumps(record)+'\\n')
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

    def run_detector(self, output=None, extra_env=None):
        env = dict(os.environ, DETECTOR_CALLS=str(self.calls))
        env.update(extra_env or {})
        return subprocess.run(
            self.command(output), capture_output=True, text=True, check=False, env=env,
        )

    def load_detector(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("reply_detector_operator_brake", DETECTOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_operator_brake_status_is_free_held_or_fail_closed(self):
        module = self.load_detector()

        def brake(name, body):
            path = self.root / name
            path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
            path.chmod(0o755)
            return path

        self.assertEqual(
            module._operator_brake_status(brake("free-brake.sh", "exit 1\n")),
            "free",
        )
        self.assertEqual(
            module._operator_brake_status(brake("held-brake.sh", "exit 0\n")),
            "held",
        )
        self.assertEqual(
            module._operator_brake_status(brake("invalid-brake.sh", "exit 2\n")),
            "failed",
        )
        self.assertEqual(
            module._operator_brake_status(self.root / "missing-brake.sh"),
            "failed",
        )
        self.assertEqual(
            module._operator_brake_status(
                brake("slow-brake.sh", "sleep 1\nexit 0\n"), timeout=0.01,
            ),
            "failed",
        )

    def test_operator_brake_defaults_to_reply_lane_state(self):
        module = self.load_detector()
        probe = self.root / "probe-brake.sh"
        expected = module.HOST_STATE_DIR / "gig-work/reply.operator.brake"
        probe.write_text(
            "#!/bin/sh\n"
            f'[ "$GIG_OPERATOR_BRAKE_FILE" = "{expected}" ]\n',
            encoding="utf-8",
        )
        probe.chmod(0o755)

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GIG_OPERATOR_BRAKE_FILE", None)
            self.assertEqual(module._operator_brake_status(probe), "held")

    def test_fresh_officially_unrepliable_thread_closes_old_preclick_action(self):
        module = self.load_detector()
        closed = []

        class FakeOutbox:
            def __init__(self, *_args):
                pass

            def pending_actions(self):
                return [{"action_id": 177, "thread_id": "9827499"},
                        {"action_id": 180, "thread_id": "safe"}]

            def claim(self, **kwargs):
                return {**kwargs, "fencing_token": 9}

            def close_nothing_to_say(self, action_id, **kwargs):
                closed.append((action_id, kwargs["reason"]))

        snapshot = {"inquiries": [
            {"talkroom_id": "9827499", "last_message_side": "buyer",
             "sending_unavailable": True, "next_action": "officially_unrepliable",
             "reply_required": False, "estimate_required": False},
            {"talkroom_id": "safe", "last_message_side": "buyer",
             "sending_unavailable": False, "next_action": "reply",
             "reply_required": True, "estimate_required": False},
        ]}
        with mock.patch.object(module, "ConnectorOutbox", FakeOutbox):
            result = module.close_officially_unrepliable_pending(
                snapshot, database=self.root / "db", manifest=self.root / "manifest",
                owner="owner", now=100,
            )
        self.assertEqual(closed, [(177, "officially_unrepliable")])
        self.assertEqual(result, {"closed_action_ids": [177], "errors": []})

    def test_held_operator_brake_reports_without_running_collector_or_effects(self):
        brake = self.root / "operator.brake"
        expires_at = int(time.time()) + 3600
        brake.write_text(
            f"owner=test\nreason=maintenance\nraised_at={int(time.time())}\n"
            f"expires_at={expires_at}\n",
            encoding="utf-8",
        )

        completed = self.run_detector(
            extra_env={"GIG_OPERATOR_BRAKE_FILE": str(brake)},
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["status"], "operator_brake")
        self.assertEqual(result["errors"], [])
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(calls, [{"step": "report", "command": "reply-wake"}])

    def test_empty_detection_runs_bounded_pipeline_and_writes_owner_only_summary(self):
        output = self.root / "detector-result.json"
        completed = self.run_detector(output)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["trigger"], "fallback")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(
            [call for call in calls if call["step"] == "report"],
            [{"step": "report", "command": "reply-wake"}],
        )

    def test_snapshot_terminal_counts_project_into_wake_result(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({'status':'completed','replied':0,'reconciled':0,
                'requeued':0,'reconcile_pending':0,'failed':0,'blocked':0,'skipped':0,
                'errors':[],'events':[],'dlq_events':[]}), encoding='utf-8')
        """), encoding="utf-8")
        self.collector.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            inquiries = ([{'next_action':'officially_unrepliable'}] * 10
                         + [{'next_action':'stop_contact'}] * 2
                         + [{'next_action':'estimate_failed','last_message_side':'buyer'}]
                         + [{'next_action':'semantic_pending','last_message_side':'seller',
                             'semantic_failure':'semantic_receipt_pending'}]
                         + [{'next_action':'observe'}] * 4)
            output.write_text(json.dumps({'captured_at':'2026-07-22T00:00:00+00:00',
                'orders':[],'quotes':[],'inquiries':inquiries}), encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["officially_unrepliable_count"], 10)
        self.assertEqual(result["stop_contact_count"], 2)
        self.assertEqual(result["classification_failed_count"], 2)
        self.assertEqual(result["semantic_judgement_failed_count"], 1)
        self.assertEqual(result["semantic_migration_pending_count"], 1)

    def test_semantic_failure_does_not_inflate_real_lane_failure(self):
        self.collector.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({'captured_at':'2026-07-22T00:00:00+00:00',
                'orders':[],'quotes':[],'inquiries':[{'next_action':'estimate_failed'}]}), encoding='utf-8')
        """), encoding="utf-8")
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({'status':'failed','replied':0,'reconciled':0,
                'requeued':0,'reconcile_pending':0,'failed':2,'blocked':0,'skipped':0,
                'errors':[],'events':[],'dlq_events':[]}), encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 1, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["semantic_judgement_failed_count"], 1)
        self.assertEqual(result["semantic_migration_pending_count"], 0)

    def test_semantic_failure_with_unknown_lane_failure_stays_thread_local(self):
        self.collector.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({'captured_at':'2026-07-22T00:00:00+00:00',
                'orders':[],'quotes':[],'inquiries':[{'next_action':'estimate_failed'}]}), encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["status"], "completed")
        self.assertIsNone(result["failed"])
        self.assertEqual(result["semantic_judgement_failed_count"], 1)

    def test_missing_snapshot_terminal_counts_stay_unknown(self):
        module = self.load_detector()

        self.assertEqual(
            module._snapshot_terminal_counts({}),
            {
                "officially_unrepliable_count": None,
                "stop_contact_count": None,
                "classification_failed_count": None,
                "semantic_judgement_failed_count": None,
                "semantic_migration_pending_count": None,
            },
        )

    def test_snapshot_activity_counts_are_exact_or_unknown(self):
        module = self.load_detector()

        self.assertEqual(module._snapshot_activity_counts({}), {
            "thread_changed_buyer_count": None,
            "thread_readback_count": None,
            "thread_revalidated_count": None,
        })
        self.assertEqual(module._snapshot_activity_counts({"source_receipt": {
            "thread_changed_buyer_count": 2,
            "thread_readback_count": 3,
            "thread_revalidated_count": 1,
        }}), {
            "thread_changed_buyer_count": 2,
            "thread_readback_count": 3,
            "thread_revalidated_count": 1,
        })

    def test_lock_setup_failure_is_reported_as_bounded_failure(self):
        lock_directory = self.root / "lock-directory"
        lock_directory.mkdir()
        output = self.root / "lock-failure.json"
        command = self.command(output)
        command[command.index("--lock-file") + 1] = str(lock_directory)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=dict(os.environ, DETECTOR_CALLS=str(self.calls)),
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_step"], "lock")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(calls, [{"step": "report", "command": "reply-wake"}])

    def test_evidence_setup_failure_uses_fallback_report_input(self):
        evidence_file = self.root / "evidence-file"
        evidence_file.write_text("not a directory", encoding="utf-8")
        command = self.command()
        command[command.index("--evidence-dir") + 1] = str(evidence_file)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=dict(
                os.environ,
                DETECTOR_CALLS=str(self.calls),
                REPORTER_INSPECT="1",
            ),
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(
            calls,
            [{"step": "report", "command": "reply-wake",
              "status": "failed", "failed_step": "evidence"}],
        )

    def test_primary_output_write_failure_still_reports_once(self):
        output_directory = self.root / "output-directory"
        output_directory.mkdir()
        completed = subprocess.run(
            self.command(output_directory),
            capture_output=True,
            text=True,
            check=False,
            env=dict(
                os.environ,
                DETECTOR_CALLS=str(self.calls),
                REPORTER_INSPECT="1",
            ),
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(
            [call for call in calls if call["step"] == "report"],
            [{"step": "report", "command": "reply-wake",
              "status": "failed", "failed_step": "output"}],
        )

    def test_blocked_rejection_is_projected_and_reported_once_per_wake(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':0,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'blocked':3,'dlq':8,'skipped':0,
                'errors':[{
                    'talkroom_id':'42','status':'blocked',
                    'errors':['submit_rejected_sending_unavailable'],
                }],
                'events':[],
                'dlq_events':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["blocked"], 3)
        self.assertEqual(result["dlq"], 8)
        self.assertEqual(result["effect"], 0)
        self.assertEqual(result["official_readback"], 0)
        self.assertEqual(result["historical_dlq"], 8)
        self.assertEqual(result["newly_dlq"], 0)
        self.assertEqual(result["events"], [])
        self.assertEqual(result["errors"][0]["status"], "blocked")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(
            [call for call in calls if call["step"] == "report"],
            [{"step": "report", "command": "reply-wake"}],
        )

    def test_new_dlq_is_separate_from_historical_dlq(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':0,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'blocked':0,'dlq':1,'skipped':0,
                'errors':[],'events':[], 'dlq_events':[{'status':'dlq'}],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["historical_dlq"], 0)
        self.assertEqual(result["newly_dlq"], 1)

    def test_invalid_dlq_relation_stays_unknown_instead_of_clamping(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':0,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'blocked':0,'dlq':1,'skipped':0,
                'errors':[],'events':[],
                'dlq_events':[{'status':'dlq'}, {'status':'dlq'}],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertIsNone(result["historical_dlq"])
        self.assertEqual(result["newly_dlq"], 2)

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

    def test_transient_collect_failure_retries_once_with_separate_evidence(self):
        self.collector.write_text(textwrap.dedent("""
            import json,os,sys
            from pathlib import Path
            args=sys.argv[1:]
            evidence=Path(args[args.index('--evidence-dir')+1])
            evidence.mkdir(parents=True,exist_ok=True)
            calls=Path(os.environ['DETECTOR_CALLS'])
            previous=calls.read_text().splitlines() if calls.exists() else []
            attempt=sum(json.loads(line).get('step')=='collector' for line in previous)+1
            with calls.open('a') as handle:
                handle.write(json.dumps({'step':'collector','attempt':attempt,
                    'evidence':evidence.name})+'\\n')
            if attempt == 1:
                (evidence/'snapshot-failure.json').write_text(json.dumps({
                    'status':'failed','error':'collector_unhealthy:unexpected_title',
                    'source_receipt':{'source':'direct_inbox','cards_count':88},
                }),encoding='utf-8')
                raise SystemExit(1)
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'captured_at':'2026-07-22T00:00:00+00:00',
                'orders':[],'quotes':[],'inquiries':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["collect_attempts"], 2)
        self.assertTrue(result["collect_recovered"])
        self.assertTrue((self.evidence / "live-dom" / "snapshot-failure.json").exists())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        collector_calls = [call for call in calls if call["step"] == "collector"]
        self.assertEqual(
            collector_calls,
            [
                {"step": "collector", "attempt": 1, "evidence": "live-dom"},
                {"step": "collector", "attempt": 2, "evidence": "live-dom-retry-2"},
            ],
        )

    def test_persistent_collect_failure_stops_after_two_read_only_attempts(self):
        self.collector.write_text(textwrap.dedent("""
            import json,os,sys
            from pathlib import Path
            args=sys.argv[1:]
            evidence=Path(args[args.index('--evidence-dir')+1])
            evidence.mkdir(parents=True,exist_ok=True)
            calls=Path(os.environ['DETECTOR_CALLS'])
            previous=calls.read_text().splitlines() if calls.exists() else []
            attempt=sum(json.loads(line).get('step')=='collector' for line in previous)+1
            with calls.open('a') as handle:
                handle.write(json.dumps({'step':'collector','attempt':attempt,
                    'evidence':evidence.name})+'\\n')
            (evidence/'snapshot-failure.json').write_text(json.dumps({
                'status':'failed','error':'collector_unhealthy:inbox_coverage_incomplete',
                'source_receipt':{'source':'direct_inbox','cards_count':0},
            }),encoding='utf-8')
            if attempt == 1:
                Path(args[args.index('--output')+1]).write_text(json.dumps({
                    'captured_at':'stale','inquiries':[{'next_action':'reply'}],
                }),encoding='utf-8')
            raise SystemExit(1)
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 1, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["failed_step"], "collect")
        self.assertEqual(result["collect_attempts"], 2)
        self.assertFalse(result["collect_recovered"])
        self.assertEqual(result["effect"], 0)
        self.assertEqual(result["official_readback"], 0)
        self.assertEqual(result["pending"], 0)
        self.assertEqual(result["estimate_effect"], 0)
        self.assertEqual(result["estimate_readback"], 0)
        self.assertEqual(result["estimate_pending"], 0)
        self.assertEqual(result["estimate_failed"], 0)
        self.assertFalse((self.evidence / "marketplace-snapshot.json").exists())
        self.assertTrue((self.evidence / "live-dom" / "snapshot-failure.json").exists())
        self.assertTrue((self.evidence / "live-dom-retry-2" / "snapshot-failure.json").exists())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(
            [call["attempt"] for call in calls if call["step"] == "collector"],
            [1, 2],
        )

    def test_retry_never_reuses_partial_snapshot_when_second_collector_writes_nothing(self):
        self.collector.write_text(textwrap.dedent("""
            import json,os,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            calls=Path(os.environ['DETECTOR_CALLS'])
            previous=calls.read_text().splitlines() if calls.exists() else []
            attempt=sum(json.loads(line).get('step')=='collector' for line in previous)+1
            with calls.open('a') as handle:
                handle.write(json.dumps({'step':'collector','attempt':attempt})+'\\n')
            if attempt == 1:
                output.write_text(json.dumps({
                    'captured_at':'partial','inquiries':[{'next_action':'reply'}],
                }),encoding='utf-8')
                raise SystemExit(1)
            raise SystemExit(0)
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 1, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["failed_step"], "collect")
        self.assertEqual(result["collect_attempts"], 2)
        self.assertEqual(
            result["collect_attempt_receipts"][1]["error"], "invalid_snapshot",
        )
        self.assertFalse((self.evidence / "marketplace-snapshot.json").exists())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(
            [call for call in calls if call["step"] != "report"],
            [{"step": "collector", "attempt": 1}, {"step": "collector", "attempt": 2}],
        )

    def test_collector_uses_direct_inbox_only_mode_and_writes_fence_compatible_snapshot(self):
        self.collector.write_text(textwrap.dedent("""
            import json,os,sys
            from pathlib import Path
            args=sys.argv[1:]
            with Path(os.environ['DETECTOR_CALLS']).open('a') as handle:
                handle.write(json.dumps({'step':'collector','args':args})+'\\n')
            assert args[args.index('--mode') + 1] == 'direct-inbox-only'
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'captured_at':'2026-07-22T00:00:00+00:00',
                'orders':[],'quotes':[],'inquiries':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        collector_call = next(call for call in calls if call["step"] == "collector")
        argv = collector_call["args"]
        self.assertEqual(argv[argv.index("--mode") + 1], "direct-inbox-only")
        self.assertEqual(argv[argv.index("--database") + 1], str(self.root / "outbox.sqlite3"))
        self.assertEqual(argv[argv.index("--manifest") + 1], str(self.root / "manifest.json"))
        snapshot = json.loads((self.evidence / "marketplace-snapshot.json").read_text())
        self.assertEqual(snapshot["orders"], [])

    def test_fence_builder_uses_direct_snapshot_only_and_writes_empty_registry(self):
        fence = self.script("fence.py", """
            import json,os,sys
            from pathlib import Path
            args=sys.argv[1:]
            with Path(os.environ['DETECTOR_CALLS']).open('a') as handle:
                handle.write(json.dumps({'step':'fence','args':args})+'\\n')
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({'version':1,'fences':[]}),encoding='utf-8')
        """)
        env = dict(os.environ, DETECTOR_CALLS=str(self.calls))

        completed = subprocess.run(
            self.command() + ["--fence-script", str(fence)],
            capture_output=True, text=True, check=False, env=env,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        fence_call = next(call for call in calls if call["step"] == "fence")
        self.assertNotIn("--queue", fence_call["args"])
        self.assertEqual(
            json.loads((self.evidence / "project-fences.json").read_text()),
            {"version": 1, "fences": []},
        )

    def test_reply_lane_receives_unlimited_finite_queue_budget(self):
        lane = self.script("lane-max-calls.py", """
            import json,os,sys
            from pathlib import Path
            args=sys.argv[1:]
            with Path(os.environ['DETECTOR_CALLS']).open('a') as handle:
                handle.write(json.dumps({'step':'lane','args':args})+'\\n')
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':0,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'skipped':0,'deferred':0,'errors':[],
            }),encoding='utf-8')
        """)
        env = dict(os.environ, DETECTOR_CALLS=str(self.calls))

        completed = subprocess.run(
            self.command() + ["--lane-script", str(lane)],
            capture_output=True, text=True, check=False, env=env,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        lane_call = next(call for call in calls if call["step"] == "lane")
        argv = lane_call["args"]
        self.assertIn("--max-model-calls", argv)
        index = argv.index("--max-model-calls")
        self.assertEqual(argv[index:index + 2], ["--max-model-calls", "0"])
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["deferred"], 0)

    def test_concurrent_trigger_returns_busy_without_running_pipeline(self):
        self.lock.touch(mode=0o600)
        with self.lock.open("r+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["status"], "busy")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(calls, [{"step": "report", "command": "reply-wake"}])

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
        self.assertEqual(result["effect"], 1)
        self.assertEqual(result["official_readback"], 1)
        self.assertEqual(result["telegram_report"], "deferred")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(
            [call for call in calls if call["step"] == "report"],
            [{"step": "report", "command": "reply-wake"}],
        )

    def test_reconciliation_only_reply_is_not_new_effect(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':1,'reconciled':1,'requeued':0,
                'reconcile_pending':0,'blocked':0,'dlq':0,'skipped':0,
                'errors':[],
                'events':[{'action_id':1,'revision':1,'talkroom_id':'42',
                    'origin_at':'2026-07-22T00:00:00+00:00',
                    'seller_sent_at':'2026-07-22T00:01:00+00:00','status':'replied'}],
                'dlq_events':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["effect"], 0)
        self.assertEqual(result["official_readback"], 1)

    def test_invalid_reconciliation_relation_stays_unknown_instead_of_clamping(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':1,'reconciled':2,'requeued':0,
                'reconcile_pending':0,'blocked':0,'dlq':0,'skipped':0,
                'errors':[],'events':[], 'dlq_events':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertIsNone(result["effect"])

    def test_malformed_event_list_does_not_count_as_official_readback(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':1,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'blocked':0,'dlq':0,'skipped':0,
                'errors':[], 'events':[{'status':'replied'}], 'dlq_events':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertIsNone(result["official_readback"])

    def test_verified_event_count_must_match_replied_count(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({
                'status':'completed','replied':0,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'blocked':0,'dlq':0,'skipped':0,
                'errors':[],
                'events':[{'action_id':1,'revision':1,'talkroom_id':'42',
                    'origin_at':'2026-07-22T00:00:00+00:00',
                    'seller_sent_at':'2026-07-22T00:01:00+00:00','status':'replied'}],
                'dlq_events':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertIsNone(result["official_readback"])

    def test_duplicate_verified_event_identity_is_not_official_readback(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            event={'action_id':1,'revision':1,'talkroom_id':'42',
                'origin_at':'2026-07-22T00:00:00+00:00',
                'seller_sent_at':'2026-07-22T00:01:00+00:00','status':'replied'}
            output.write_text(json.dumps({
                'status':'completed','replied':2,'reconciled':0,'requeued':0,
                'reconcile_pending':0,'blocked':0,'dlq':0,'skipped':0,
                'errors':[], 'events':[event,event], 'dlq_events':[],
            }),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertIsNone(result["official_readback"])

    def test_missing_lane_truth_stays_unknown_in_wake_result(self):
        self.lane.write_text(textwrap.dedent("""
            import json,sys
            from pathlib import Path
            args=sys.argv[1:]
            output=Path(args[args.index('--output')+1])
            output.write_text(json.dumps({'status':'completed'}),encoding='utf-8')
        """), encoding="utf-8")

        completed = self.run_detector()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((self.root / "detector-result.json").read_text())
        for key in (
            "effect", "official_readback", "blocked", "historical_dlq",
            "newly_dlq", "failed", "pending", "skipped",
        ):
            self.assertIsNone(result[key], key)

    def test_collector_failure_is_bounded_failure_and_stops_pipeline(self):
        self.collector.write_text("raise SystemExit(7)\n", encoding="utf-8")
        completed = self.run_detector()

        self.assertEqual(completed.returncode, 1)
        result = json.loads((self.root / "detector-result.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_step"], "collect")
        self.assertIsNone(result["observed"])
        self.assertEqual(result["effect"], 0)
        self.assertEqual(result["official_readback"], 0)
        self.assertEqual(result["pending"], 0)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(calls, [{"step": "report", "command": "reply-wake"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
