from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger
from job_search_loop.workday_discovery import discover_one


class WorkdayDiscoveryTests(unittest.TestCase):
    def test_discovers_one_best_unseen_japan_role_and_dedupes_next_wake(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "ledger.sqlite3"

            def fake_fetch(source):
                if source["company"] == "NVIDIA":
                    return [
                        {
                            "title": "Solution Architect - Agentic AI",
                            "locationsText": "Japan, Tokyo",
                            "externalPath": "/job/Japan-Tokyo/Solution-Architect---Agentic-AI_JR9",
                        },
                        {
                            "title": "Office Administrator",
                            "locationsText": "Japan, Tokyo",
                            "externalPath": "/job/Japan-Tokyo/Office-Administrator_JR8",
                        },
                    ]
                if source["company"] == "Workday":
                    return [
                        {
                            "title": "Technical Account Manager",
                            "locationsText": "Japan, Tokyo",
                            "externalPath": "/job/Japan-Tokyo/Technical-Account-Manager_JR7",
                        }
                    ]
                return []

            first = discover_one(ledger_path=ledger_path, fetch_jobs=fake_fetch)
            self.assertEqual(first["status"], "discovered")
            self.assertEqual(first["discovered"][0]["title"], "Solution Architect - Agentic AI")

            ledger = Ledger(ledger_path)
            self.assertEqual(ledger.current_state(first["discovered"][0]["application_id"]), "materials_ready")
            ledger.close()

            second = discover_one(ledger_path=ledger_path, fetch_jobs=fake_fetch)
            self.assertEqual(second["status"], "discovered")
            self.assertEqual(second["discovered"][0]["title"], "Technical Account Manager")

    def test_one_source_failure_does_not_stop_other_tenants(self):
        with tempfile.TemporaryDirectory() as directory:
            def fake_fetch(source):
                if source["company"] == "NVIDIA":
                    raise TimeoutError("provider timeout")
                if source["company"] == "Workday":
                    return [
                        {
                            "title": "Senior Technical Account Manager",
                            "locationsText": "Japan, Tokyo",
                            "externalPath": "/job/Japan-Tokyo/Senior-Technical-Account-Manager_JR6",
                        }
                    ]
                return []

            result = discover_one(
                ledger_path=Path(directory) / "ledger.sqlite3", fetch_jobs=fake_fetch
            )
            self.assertEqual(result["status"], "discovered")
            self.assertEqual(result["errors"], ["nvidia:TimeoutError"])
            self.assertEqual(result["discovered"][0]["company"], "Workday")


if __name__ == "__main__":
    unittest.main()
