import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from job_search_loop.candidate_routes import (
    filter_terminal_candidates,
    materialize_canonical_routes,
)
from job_search_loop.ledger import Ledger


class CandidateRouteTests(unittest.TestCase):
    def test_terminal_urls_and_evidence_aliases_are_removed_before_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite3"
            ledger = Ledger(database)
            submitted = ledger.add_application(
                "Submitted AI", "Engineer", "https://jobs.example/role?utm_source=old"
            )
            rejected = ledger.add_application(
                "Rejected AI", "Architect", "https://jobs.example/rejected"
            )
            aliased = ledger.add_application(
                "Alias AI", "Solutions Engineer", "evidence://gmail/manual-1"
            )
            ledger._append_event(submitted, "discovered", "submitted")
            ledger.connection.execute(
                "UPDATE applications SET current_state='submitted' WHERE id=?", (submitted,)
            )
            ledger.transition(rejected, "rejected")
            ledger._append_event(aliased, "discovered", "submit_unknown")
            ledger.connection.execute(
                "UPDATE applications SET current_state='submit_unknown' WHERE id=?", (aliased,)
            )
            ledger.connection.commit()
            ledger.close()
            payload = {"candidates": [
                {"company": "Submitted AI", "title": "Engineer", "official_url": "https://jobs.example/role?utm_campaign=new"},
                {"company": "Rejected AI", "title": "Architect", "official_url": "https://jobs.example/rejected"},
                {"company": "Alias AI", "title": "Solutions Engineer", "official_url": "https://jobs.ashbyhq.com/alias/role"},
                {"company": "Fresh AI", "title": "Engineer", "official_url": "https://jobs.example/fresh"},
            ]}

            filtered = filter_terminal_candidates(database, payload)

            self.assertEqual(
                [item["company"] for item in filtered["candidates"]], ["Fresh AI"]
            )
            self.assertEqual(filtered["terminal_filter"]["excluded_count"], 3)
            self.assertEqual(
                set(filtered["terminal_filter"]["reasons"]),
                {"submitted", "rejected", "submit_unknown"},
            )

    def test_terminal_history_is_removed_before_shortlisting(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite3"
            ledger = Ledger(database)
            terminal = ledger.add_application(
                "Old AI", "AI Engineer", "https://jobs.example/old"
            )
            ledger._append_event(terminal, "discovered", "submitted")
            ledger.connection.execute(
                "UPDATE applications SET current_state='submitted' WHERE id=?",
                (terminal,),
            )
            ledger.connection.commit()
            ledger.close()
            payload = {"candidates": [
                {
                    "company": "Old AI", "title": "AI Engineer",
                    "official_url": "https://jobs.example/old",
                    "gate_status": "pass", "ranking_ready": True,
                },
                {
                    "company": "Fresh AI", "title": "AI Deployment Engineer",
                    "official_url": "https://jobs.example/fresh",
                    "gate_status": "pass", "ranking_ready": True,
                },
            ]}

            filtered = filter_terminal_candidates(database, payload, limit=1)

            self.assertEqual(
                [row["company"] for row in filtered["candidates"]], ["Fresh AI"]
            )
            self.assertEqual(filtered["terminal_filter"]["included_count"], 1)
            self.assertEqual(filtered["terminal_filter"]["selected_count"], 1)

    def test_manual_owned_candidate_is_audited_and_next_candidate_materializes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, database = Path(directory), Path(directory) / "ledger.sqlite3"
            ledger = Ledger(database)
            ledger.import_external_application(
                company="Manual AI", title="AI Engineer", owner="dais_manual",
                source="gmail", source_message_id="manual-1",
                applied_at="2026-08-05T00:00:00+09:00",
                evidence_sha256=hashlib.sha256(b"manual").hexdigest(),
            )
            ledger.close()
            payload = root / "prefilter.json"
            payload.write_text(json.dumps({"candidates": [
                {"company": "Manual AI", "title": "AI Engineer", "official_url": "https://jobs.ashbyhq.com/manual/role", "provider": "ashby", "ranking_ready": True, "ranking": {"score": 100}},
                {"company": "Next AI", "title": "Applied AI Engineer", "official_url": "https://jobs.ashbyhq.com/next/role", "provider": "ashby", "ranking_ready": True, "ranking": {"score": 90}},
            ]}), encoding="utf-8")

            result = materialize_canonical_routes(database, payload)

            self.assertEqual(result[0]["status"], "skipped_cross_owner")
            self.assertEqual(result[0]["reason"], "canonical_posting_owned_elsewhere")
            self.assertEqual(len(result[0]["url_sha256"]), 64)
            self.assertIn("application_id", result[1])

    def test_ranked_candidate_materializes_one_idempotent_canonical_route(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "prefilter.json"
            payload.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "company": "Example AI",
                                "title": "AI Engineer",
                                "official_url": "https://jobs.ashbyhq.com/example/role",
                                "provider": "ashby",
                                "ranking_ready": True,
                                "ranking": {"score": 90},
                                "source_spans": ["official title span"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            database = root / "ledger.sqlite3"

            first = materialize_canonical_routes(database, payload)
            second = materialize_canonical_routes(database, payload)

            self.assertEqual(first, second)
            self.assertEqual(len(first), 1)
            ledger = Ledger(database)
            try:
                routes = ledger.application_routes(first[0]["application_id"])
            finally:
                ledger.close()
            self.assertEqual(len(routes), 1)
            self.assertEqual(routes[0]["route_kind"], "canonical_ats")
            self.assertEqual(routes[0]["ordinal"], 1)
            self.assertEqual(routes[0]["delivery_state"], "eligible")


if __name__ == "__main__":
    unittest.main()
