from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger
from job_search_loop.workday_search_loop import (
    cached_source_fetcher,
    rotated_sources,
    search_until_qualified,
    snapshot_candidates,
    validate_shortlist,
)
from job_search_loop.workday_qualification import qualify_one


class WorkdayQualificationTests(unittest.TestCase):
    def test_snapshot_skips_failed_source_and_keeps_other_company(self):
        with tempfile.TemporaryDirectory() as directory:
            sources = (
                {"company": "Broken", "host": "broken.wd1.myworkdayjobs.com", "site": "Careers"},
                {"company": "Good", "host": "good.wd1.myworkdayjobs.com", "site": "Careers"},
            )

            def fetch(source):
                if source["company"] == "Broken":
                    raise TimeoutError
                return [{"title": "Good Role", "locationsText": "Tokyo", "externalPath": "/job/Good_R1"}]

            rows = snapshot_candidates(
                ledger_path=Path(directory) / "ledger.sqlite3",
                sources=sources,
                fetch_jobs=fetch,
            )

            self.assertEqual([row["company"] for row in rows], ["Good"])

    def test_shortlist_rejects_model_invented_url(self):
        candidates = [{"url": "https://a.wd1.myworkdayjobs.com/Careers/job/A"}]
        with self.assertRaisesRegex(ValueError, "unknown URL"):
            validate_shortlist(
                {"ranked_urls": ["https://invented.example/job/1"]}, candidates
            )

    def test_each_source_is_fetched_once_per_wake(self):
        calls = []
        source = {"company": "A", "host": "a.myworkdayjobs.com"}
        fetch = cached_source_fetcher(
            lambda row: calls.append(row["company"]) or [{"title": "Role"}]
        )

        self.assertEqual(fetch(source), [{"title": "Role"}])
        self.assertEqual(fetch(source), [{"title": "Role"}])
        self.assertEqual(calls, ["A"])

    def test_sources_rotate_across_companies_in_one_wake(self):
        sources = ({"company": "A"}, {"company": "B"}, {"company": "C"})
        self.assertEqual(
            [row["company"] for row in rotated_sources(sources, 1)],
            ["B", "C", "A"],
        )

    def test_same_wake_continues_after_reject_and_hold_until_qualified(self):
        decisions = iter(("rejected", "hold", "qualified"))
        discovered = []

        def discover():
            number = len(discovered) + 1
            discovered.append(number)
            return {"status": "discovered", "discovered": [{"id": number}]}

        def qualify():
            return {"status": "decided", "decision": next(decisions)}

        result = search_until_qualified(
            discover=discover,
            qualify=qualify,
            max_candidates=10,
        )

        self.assertEqual(discovered, [1, 2, 3])
        self.assertEqual(result["status"], "qualified")
        self.assertEqual([row["decision"] for row in result["decisions"]], [
            "rejected", "hold", "qualified"
        ])

    def test_daily_owner_searches_until_qualified_before_browser_lane(self):
        script = (
            Path(__file__).resolve().parents[1] / "scripts/run-daily.sh"
        ).read_text(encoding="utf-8")
        qualifier = "-m job_search_loop.workday_search_loop"
        browser = "-m job_search_loop.browser_agent.orchestrator"
        self.assertIn(qualifier, script)
        self.assertLess(script.index(qualifier), script.index(browser))
        self.assertNotIn("-m job_search_loop.workday_discovery", script)
        self.assertNotIn("-m job_search_loop.workday_qualification", script)

    def _row(self, root: Path) -> tuple[Path, str, Path]:
        ledger_path = root / "ledger.sqlite3"
        ledger = Ledger(ledger_path)
        application_id = ledger.add_application(
            "Example",
            "Principal Stretch Role",
            "https://example.wd5.myworkdayjobs.com/Site/job/Japan/Role_JR1",
        )
        ledger.transition(application_id, "qualified")
        ledger.transition(application_id, "materials_ready")
        ledger.close()
        memory = root / "candidate-memory.json"
        memory.write_text(json.dumps({"facts": [{"claim": "Grounded experience"}]}))
        return ledger_path, application_id, memory

    def test_rejected_model_decision_never_enters_browser_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path, application_id, memory = self._row(root)

            result = qualify_one(
                ledger_path=ledger_path,
                candidate_memory_path=memory,
                fetch_description=lambda _url: "Requires unsupported principal scope",
                run_model=lambda _prompt: {
                    "decision": "rejected",
                    "mandatory_evidence": [],
                    "unsupported_gaps": ["Principal scope is unsupported"],
                    "interview_thesis": "No grounded interview case",
                    "location_feasibility": "Tokyo",
                    "compensation_thesis": "Unknown",
                    "compensation_uncertain": True,
                    "resume_variant": "business",
                },
            )

            ledger = Ledger(ledger_path)
            self.assertEqual(result["decision"], "rejected")
            self.assertFalse(ledger.workday_fit_qualified(application_id))
            self.assertEqual(ledger.current_state(application_id), "rejected")
            ledger.close()

    def test_qualified_model_decision_unlocks_only_that_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path, application_id, memory = self._row(root)

            result = qualify_one(
                ledger_path=ledger_path,
                candidate_memory_path=memory,
                fetch_description=lambda _url: "Applied AI customer role in Tokyo",
                run_model=lambda _prompt: {
                    "decision": "qualified",
                    "mandatory_evidence": ["Grounded experience matches"],
                    "unsupported_gaps": [],
                    "interview_thesis": "Direct applied AI deployment evidence",
                    "location_feasibility": "Tokyo onsite is feasible",
                    "compensation_thesis": "Target is plausible but unpublished",
                    "compensation_uncertain": True,
                    "resume_variant": "business",
                },
            )

            ledger = Ledger(ledger_path)
            self.assertEqual(result["decision"], "qualified")
            self.assertTrue(ledger.workday_fit_qualified(application_id))
            self.assertEqual(ledger.current_state(application_id), "materials_ready")
            ledger.close()

    def test_old_hold_is_re_evaluated_once_by_new_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path, application_id, memory = self._row(root)
            ledger = Ledger(ledger_path)
            ledger.record_workday_fit_decision(
                application_id, "hold", "a" * 64, policy_version="old-policy"
            )
            ledger.close()

            result = qualify_one(
                ledger_path=ledger_path,
                candidate_memory_path=memory,
                fetch_description=lambda _url: "Applied AI implementation role",
                run_model=lambda _prompt: {
                    "decision": "qualified",
                    "mandatory_evidence": ["Equivalent impact is grounded"],
                    "unsupported_gaps": ["Published years exceed tenure"],
                    "interview_thesis": "Credible interview case now",
                    "location_feasibility": "Tokyo",
                    "compensation_thesis": "Unpublished and uncertain",
                    "compensation_uncertain": True,
                    "resume_variant": "business",
                },
            )

            ledger = Ledger(ledger_path)
            self.assertEqual(result["decision"], "qualified")
            self.assertTrue(ledger.workday_fit_qualified(application_id))
            ledger.close()

    def test_old_hold_from_unavailable_source_does_not_block_search(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path, application_id, memory = self._row(root)
            ledger = Ledger(ledger_path)
            ledger.record_workday_fit_decision(
                application_id, "hold", "a" * 64, policy_version="old-policy"
            )
            ledger.close()

            result = qualify_one(
                ledger_path=ledger_path,
                candidate_memory_path=memory,
                fetch_description=lambda _url: self.fail("must not fetch foreign source"),
                run_model=lambda _prompt: self.fail("must not run model"),
                allowed_hosts={"another.wd1.myworkdayjobs.com"},
            )

            self.assertEqual(result["status"], "no_pending_workday_fit")


if __name__ == "__main__":
    unittest.main()
