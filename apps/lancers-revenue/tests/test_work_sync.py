import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
WORK_SYNC_PATH = REPO_ROOT / "skills/earn/lancers/scripts/work_sync.py"


def _load():
    spec = importlib.util.spec_from_file_location("test_lancers_work_sync", WORK_SYNC_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("work_sync_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fetcher(*, detail=None, messages=None, duplicate_message=False, malformed=False):
    board = {"id": 7, "modified": "2026-08-13T00:00:00Z", "is_required_reply": True, "unread_count": 2, "buyer_name": "buyer identity"}
    detail = detail if detail is not None else {"id": 7, "with": {"proposal": {"id": "proposal-7"}, "job": {"id": "job-7"}, "serviceItemContract": {"id": "contract-7"}}, "token": "provider-token"}
    message = {"id": 9, "board_id": 7, "modified": "2026-08-13T00:00:00Z", "is_required_reply": False, "send_user": {"name": "buyer identity"}, "body": "private message text", "cookie": "session-cookie"}
    message = messages if messages is not None else message
    calls = []
    def fetch(path):
        calls.append(path)
        if path.startswith("/v1/message_api/boards/?"):
            return {"not": "an array"} if malformed else ([] if "modified=" in path else [board])
        if path == "/v1/message_api/boards/7": return detail
        if "/messages?" in path:
            if "message_id=" in path: return []
            return [message, message] if duplicate_message else [message]
        raise AssertionError(path)
    return fetch, calls


def _ledger(root: Path, *proposal_ids: str) -> Path:
    path = root / "marketplace-ledger.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE marketplace_events (platform TEXT, event_type TEXT, external_id TEXT)")
    connection.executemany("INSERT INTO marketplace_events VALUES ('lancers', 'application_verified', ?)", [(value,) for value in proposal_ids])
    connection.commit(); connection.close()
    return path


class WorkSyncTests(unittest.TestCase):
    def test_complete_snake_case_snapshot_is_sanitized_and_correlated(self):
        sync = _load(); fetch, calls = _fetcher()
        result = sync._snapshot(fetch, {"proposal-7"})
        self.assertEqual((result["board_count"], result["required_reply_count"], result["unread_count"]), (1, 1, 2))
        self.assertEqual((result["application_board_count"], result["storefront_contract_candidate_count"]), (1, 1))
        self.assertTrue(result["ok"] and result["source_complete"])
        rendered = json.dumps(result, ensure_ascii=False)
        for secret in ("private message text", "buyer identity", "session-cookie", "provider-token", "buyer_name"):
            self.assertNotIn(secret, rendered)
        self.assertTrue(any("limit=20" in path for path in calls))
        self.assertTrue(any("message_id=9" in path and "direction=prev" in path for path in calls))

    def test_application_count_requires_verified_receipt_read_only_set(self):
        sync = _load(); fetch, _ = _fetcher()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); ledger = _ledger(root, "proposal-7")
            before = ledger.read_bytes()
            self.assertEqual(sync._snapshot(fetch, sync._verified_proposals(root / "work-sync.json"))["application_board_count"], 1)
            self.assertEqual(ledger.read_bytes(), before)
            self.assertEqual(sync._snapshot(fetch, {"other-proposal"})["application_board_count"], 0)
            with tempfile.TemporaryDirectory() as missing_directory:
                with self.assertRaisesRegex(sync.SourceFailure, "application_receipts_unavailable"):
                    sync._verified_proposals(Path(missing_directory) / "missing.json")

    def test_empty_with_remains_unknown_without_event_or_contract(self):
        sync = _load(); fetch, _ = _fetcher(detail={"id": 7, "with": {}})
        rendered = json.dumps(sync._snapshot(fetch, set()), ensure_ascii=False)
        self.assertIn('"application_board_count": 0', rendered)
        self.assertIn('"storefront_contract_candidate_count": 0', rendered)
        self.assertNotIn("order_awarded", rendered)
        self.assertNotIn("ledger", rendered)

    def test_duplicate_malformed_and_truncated_sources_fail_closed(self):
        sync = _load()
        fetch, _ = _fetcher(duplicate_message=True)
        with self.assertRaisesRegex(sync.SourceFailure, "duplicate_message_id"):
            sync._snapshot(fetch, set())
        fetch, _ = _fetcher(malformed=True)
        with self.assertRaisesRegex(sync.SourceFailure, "provider_response_invalid"):
            sync._snapshot(fetch, set())
        fetch, _ = _fetcher()
        with patch.object(sync, "MAX_BOARD_PAGES", 1), self.assertRaisesRegex(sync.SourceFailure, "board_page_limit_reached"):
            sync._snapshot(fetch, set())

    def test_cleanup_failure_returns_one_stable_nonzero_json_result(self):
        sync = _load(); fetch, _ = _fetcher()
        class Page:
            def evaluate(self, _script, path): return {"ok": True, "body": fetch(path)}
            def close(self): raise RuntimeError("Page.handleJavaScriptDialog: No dialog is showing")
        class Browser:
            def __init__(self):
                self.contexts = [self]; self._anicca_playwright_runtime = self; self.stopped = False
            def new_page(self): return Page()
            def stop(self): self.stopped = True
        browser, output = Browser(), io.StringIO()
        with tempfile.TemporaryDirectory() as directory, patch.object(sync.application_tick, "_production_account_ready", return_value=True):
            _ledger(Path(directory), "proposal-7")
            code = sync.main(["--worker", "--json", "--state-path", str(Path(directory) / "application.json")], output_stream=output, browser_factory=lambda _url: browser)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue()), {"ok": False, "logged_in": True, "source_complete": False, "error": "cleanup_failed"})
        self.assertTrue(browser.stopped)

    def test_watchdog_forwards_valid_nonzero_worker_failure_json(self):
        sync = _load()
        result = sync._watchdog([sys.executable, "-c", "import json,sys; print(json.dumps({'ok': False, 'logged_in': True, 'source_complete': False, 'error': 'cleanup_failed'})); sys.exit(1)"], 1)
        self.assertEqual(result, {"ok": False, "logged_in": True, "source_complete": False, "error": "cleanup_failed"})

    def test_watchdog_kills_harmless_descendant_on_timeout(self):
        sync = _load()
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "descendant.pid"
            code = "import pathlib, subprocess, sys, time; child=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); pathlib.Path(sys.argv[1]).write_text(str(child.pid)); time.sleep(60)"
            started = time.monotonic()
            result = sync._watchdog([sys.executable, "-c", code, str(marker)], 0.15)
            self.assertLess(time.monotonic() - started, 3)
            self.assertEqual(result, {"ok": False, "logged_in": False, "source_complete": False, "error": "tick_timeout"})
            child_pid = int(marker.read_text())
            time.sleep(0.1)
            with self.assertRaises(ProcessLookupError): os.kill(child_pid, 0)

    def test_watchdog_kills_lingering_descendant_after_normal_leader_exit(self):
        sync = _load()
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "descendant.pid"
            success = {"ok": True, "logged_in": True, "source_complete": True}
            code = "import json, pathlib, subprocess, sys; child=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); pathlib.Path(sys.argv[1]).write_text(str(child.pid)); print(json.dumps({!r}))".format(success)
            result = sync._watchdog([sys.executable, "-c", code, str(marker)], 1)
            self.assertEqual(result, success)
            child_pid = int(marker.read_text())
            time.sleep(0.1)
            with self.assertRaises(ProcessLookupError): os.kill(child_pid, 0)


if __name__ == "__main__":
    unittest.main()
