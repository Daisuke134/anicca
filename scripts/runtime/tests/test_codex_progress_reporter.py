import importlib.util
import json
import pathlib
import tempfile
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "codex-progress-reporter.py"
SPEC = importlib.util.spec_from_file_location("codex_progress_reporter", MODULE_PATH)
reporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reporter)


class CodexProgressReporterTests(unittest.TestCase):
    def write_session(self, directory, name, messages):
        path = pathlib.Path(directory) / name
        path.write_text("\n".join(json.dumps(message) for message in messages) + "\n")
        return path

    def test_summarizes_latest_agent_update_and_marks_recent_session_working(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_session(temp_dir, "rollout-abc.jsonl", [
                {"type": "event_msg", "payload": {"type": "agent_message", "message": "テストを追加している", "phase": "commentary"}}
            ])
            summary = reporter.session_summary(path, now=1_000, modified_at=980)

        self.assertEqual(summary["label"], "abc")
        self.assertEqual(summary["status"], "作業中")
        self.assertEqual(summary["update"], "テストを追加している")

    def test_marks_a_quiet_but_recent_session_stalled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_session(temp_dir, "rollout-abc.jsonl", [])
            summary = reporter.session_summary(path, now=1_000, modified_at=250)

        self.assertEqual(summary["status"], "停滞の可能性")
        self.assertEqual(summary["update"], "最後の進捗メッセージを待機中")

    def test_formats_one_compact_report_for_all_active_sessions(self):
        report = reporter.format_report([
            {"label": "abc", "status": "作業中", "update": "テストを追加している"},
            {"label": "def", "status": "停滞の可能性", "update": "最後の進捗メッセージを待機中"},
        ], now=1_000)

        self.assertIn("Codex:::", report)
        self.assertIn("abc: 作業中 — テストを追加している", report)
        self.assertIn("def: 停滞の可能性", report)


if __name__ == "__main__":
    unittest.main()
