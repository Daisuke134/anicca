from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger
from job_search_loop.workday_search_loop import (
    cached_source_fetcher,
    interleave_companies,
    qualified_queue_ids,
    rank_candidates,
    rotated_sources,
    search_until_qualified,
    snapshot_candidates,
    submitted_company_portfolio,
    validate_shortlist,
    unique_sources,
)
from job_search_loop.workday_qualification import qualify_one


class WorkdayQualificationTests(unittest.TestCase):
    def test_candidate_windows_interleave_companies_instead_of_source_volume(self):
        rows = [
            {"company": "Rakuten", "url": f"r-{index}"}
            for index in range(4)
        ] + [
            {"company": "Salesforce", "url": "s-1"},
            {"company": "Razer", "url": "z-1"},
        ]
        self.assertEqual(
            [row["url"] for row in interleave_companies(rows)],
            ["r-0", "s-1", "z-1", "r-1", "r-2", "r-3"],
        )

    def test_submitted_portfolio_is_counted_for_model_ranking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite3"
            ledger = Ledger(path)
            for index, company in enumerate(("Rakuten", "Rakuten", "Razer")):
                application_id = ledger.add_application(
                    company,
                    f"Role {index}",
                    f"https://{company.lower()}.wd1.myworkdayjobs.com/job/{index}",
                )
                ledger.transition(application_id, "qualified")
                ledger.transition(application_id, "materials_ready")
                ledger.connection.execute(
                    "UPDATE applications SET current_state='submitted' WHERE id=?",
                    (application_id,),
                )
            ledger.connection.commit()
            ledger.close()
            self.assertEqual(
                submitted_company_portfolio(path),
                {"Rakuten": 2, "Razer": 1},
            )
    def test_transient_qualification_failure_retries_same_wake(self):
        attempts = 0

        def qualify():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("model at capacity")
            return {"status": "decided", "decision": "qualified"}

        result = search_until_qualified(
            discover=lambda: {"status": "queue_present", "discovered": []},
            qualify=qualify,
            max_candidates=3,
        )

        self.assertEqual(result["status"], "qualified")
        self.assertEqual(attempts, 2)

    def test_qualified_queue_is_detected_before_snapshot_search(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "ledger.sqlite3"
            ledger = Ledger(ledger_path)
            application_id = ledger.add_application(
                "Example", "Role", "https://example.wd1.myworkdayjobs.com/Careers/job/R1"
            )
            ledger.transition(application_id, "qualified")
            ledger.transition(application_id, "materials_ready")
            ledger.record_workday_fit_decision(
                application_id, "qualified", "a" * 64, policy_version="test"
            )
            ledger.close()

            self.assertEqual(
                qualified_queue_ids(
                    ledger_path, {"example.wd1.myworkdayjobs.com"}
                ),
                (application_id,),
            )

    def test_duplicate_registry_source_is_fetched_once(self):
        sources = (
            {"company": "A", "host": "a.wd1.myworkdayjobs.com", "tenant": "a", "site": "Careers", "search_text": "one"},
            {"company": "A", "host": "a.wd1.myworkdayjobs.com", "tenant": "a", "site": "Careers", "search_text": "two"},
        )
        self.assertEqual(len(unique_sources(sources)), 1)

    def test_complete_snapshot_is_ranked_in_chunks_then_finalists(self):
        candidates = [
            {"url": f"https://a.wd1.myworkdayjobs.com/Careers/job/{index}"}
            for index in range(50)
        ]
        calls = []
        candidate_id_calls = []

        def rank(chunk):
            calls.append([row["url"] for row in chunk])
            candidate_id_calls.append([row["candidate_id"] for row in chunk])
            return {"ranked_candidate_ids": [chunk[-1]["candidate_id"]]}

        result = rank_candidates(
            candidates=candidates,
            rank_chunk=rank,
            chunk_size=2,
        )

        self.assertEqual(len(calls), 26)
        self.assertEqual(len(calls[-1]), 25)
        self.assertEqual(result, (calls[-1][-1],))
        self.assertTrue(all(ids[0] == "c0" for ids in candidate_id_calls))

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

    def test_shortlist_drops_model_invented_url_and_keeps_official_rows(self):
        official = "https://a.wd1.myworkdayjobs.com/Careers/job/A"
        candidates = [{"candidate_id": "candidate-1", "url": official}]
        self.assertEqual(
            validate_shortlist(
                {"ranked_candidate_ids": ["invented", "candidate-1"]},
                candidates,
            ),
            (official,),
        )

    def test_shortlist_fails_closed_when_no_official_url_remains(self):
        with self.assertRaisesRegex(ValueError, "no official candidate ID"):
            validate_shortlist(
                {"ranked_candidate_ids": ["invented"]},
                [{"candidate_id": "candidate-1", "url": "https://a.wd1.myworkdayjobs.com/Careers/job/A"}],
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
