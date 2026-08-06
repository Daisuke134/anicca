import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.candidate_routes import materialize_canonical_routes
from job_search_loop.ledger import Ledger


class CandidateRouteTests(unittest.TestCase):
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
