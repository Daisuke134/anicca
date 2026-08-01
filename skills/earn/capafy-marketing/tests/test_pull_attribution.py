#!/usr/bin/env python3
import importlib.util
import io
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pull_attribution.py"
SPEC = importlib.util.spec_from_file_location("pull_attribution", SCRIPT)
pull_attribution = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pull_attribution)


class PullAttributionTests(unittest.TestCase):
    def test_fetches_stats_joins_sales_and_appends_one_daily_row(self):
        stats_response = io.BytesIO(json.dumps({"1": 4, "2": 0}).encode())
        sales_payload = {
            "data": [
                {"agentId": 1, "name": "Writer", "sales": 7},
                {"agentId": "2", "name": "Planner", "sales": 3},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "capafy-attribution.jsonl"
            with (
                patch.object(pull_attribution.request, "urlopen", return_value=stats_response) as urlopen,
                patch.object(pull_attribution, "_fetch_agents", return_value=sales_payload),
            ):
                result = pull_attribution.pull(
                    stats_url="https://landing.example/go-stats",
                    output_file=output,
                    today=date(2026, 7, 19),
                )

            urlopen.assert_called_once()
            request_arg = urlopen.call_args.args[0]
            self.assertEqual(request_arg.full_url, "https://landing.example/go-stats")
            self.assertEqual(result["date"], "2026-07-19")
            self.assertEqual(
                result["agents"],
                [
                    {"agent_id": "1", "clicks": 4, "sales": 7, "name": "Writer"},
                    {"agent_id": "2", "clicks": 0, "sales": 3, "name": "Planner"},
                ],
            )
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 1)

    def test_second_pull_on_same_date_does_not_append(self):
        existing = {"date": "2026-07-19", "agents": []}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "capafy-attribution.jsonl"
            output.write_text(json.dumps(existing) + "\n", encoding="utf-8")

            result = pull_attribution.pull(
                output_file=output,
                today=date(2026, 7, 19),
            )

            self.assertEqual(result, existing)
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 1)

    def test_failed_event_sync_keeps_row_and_next_pull_retries_without_refetch(self):
        stats_response = io.BytesIO(json.dumps({"4866150011": 2}).encode())
        sales_payload = {
            "data": [
                {"agentId": "4866150011", "name": "Decision Debate", "sales": None}
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "capafy-attribution.jsonl"
            calls = root / "calls.jsonl"
            sync = root / "event-sync.py"
            sync.write_text(
                "#!/usr/bin/env python3\n"
                "import json,os,sys\n"
                "with open(os.environ['SYNC_CALLS'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n"
                "raise SystemExit(int(os.environ.get('SYNC_EXIT','0')))\n"
            )
            sync.chmod(0o755)
            environment = {
                "SYNC_CALLS": str(calls),
                "SYNC_EXIT": "7",
            }
            with (
                patch.dict(os.environ, environment, clear=False),
                patch.object(pull_attribution.request, "urlopen", return_value=stats_response) as urlopen,
                patch.object(pull_attribution, "_fetch_agents", return_value=sales_payload),
            ):
                with self.assertRaisesRegex(RuntimeError, "event sync failed"):
                    pull_attribution.pull(
                        stats_url="https://landing.example/go-stats",
                        output_file=output,
                        today=date(2026, 8, 2),
                        event_sync=sync,
                        event_ledger=root / "events.jsonl",
                        evidence_dir=root / "evidence",
                    )
                os.environ["SYNC_EXIT"] = "0"
                result = pull_attribution.pull(
                    stats_url="https://landing.example/go-stats",
                    output_file=output,
                    today=date(2026, 8, 2),
                    event_sync=sync,
                    event_ledger=root / "events.jsonl",
                    evidence_dir=root / "evidence",
                )

            self.assertEqual(result["date"], "2026-08-02")
            self.assertEqual(len(output.read_text().splitlines()), 1)
            self.assertEqual(len(calls.read_text().splitlines()), 2)
            urlopen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
