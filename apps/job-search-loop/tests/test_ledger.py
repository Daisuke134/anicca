import hashlib
import inspect
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from job_search_loop.ledger import FenceError, Ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Path(self.tempdir.name) / "ledger.sqlite3"
        self.ledger = Ledger(self.db)
        self.resume = Path(self.tempdir.name) / "resume.pdf"
        self.resume.write_bytes(b"%PDF-1.4\nverified resume\n")
        self.resume_sha256 = hashlib.sha256(self.resume.read_bytes()).hexdigest()
        self.application_id = self.ledger.add_application(
            "Example", "AI Engineer", "https://jobs.example.com/42"
        )

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def _ready(self, application_id=None):
        target = application_id or self.application_id
        self.ledger.transition(target, "qualified")
        self.ledger.transition(target, "materials_ready")

    def _claim(
        self,
        ledger,
        application_id,
        japan_day,
        payload_hash,
        *,
        portfolio_bucket=None,
        record_materials=True,
    ):
        row = ledger.connection.execute(
            "SELECT canonical_url FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
        snapshot = Path(self.tempdir.name) / f"ats-{application_id}.json"
        snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": str(row["canonical_url"]),
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": str(row["canonical_url"]),
                            "controls": [
                                {
                                    "tag": "input",
                                    "type": "email",
                                    "role": None,
                                    "label": "Email",
                                    "name": "email",
                                    "text": "",
                                },
                                {
                                    "tag": "input",
                                    "type": "file",
                                    "role": None,
                                    "label": "Resume",
                                    "name": "resume",
                                    "text": "",
                                },
                                {
                                    "tag": "button",
                                    "type": "submit",
                                    "role": "button",
                                    "label": None,
                                    "name": "submit",
                                    "text": "Submit Application",
                                },
                            ],
                        }
                    ],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        snapshot_sha256 = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        intent = ledger.claim_submission(
            application_id,
            japan_day,
            payload_hash,
            resume_path=self.resume,
            resume_sha256=self.resume_sha256,
            ats_snapshot_path=snapshot,
            ats_snapshot_sha256=snapshot_sha256,
            portfolio_bucket=portfolio_bucket,
        )
        if intent is not None and record_materials:
            ledger.record_submission_materials(
                intent_id=intent.intent_id,
                fence=intent.fence,
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                cover_letter=None,
                employer_answers=[],
            )
        return intent

    def test_daily_portfolio_enforces_two_five_three_bucket_caps(self):
        self.assertIn("portfolio_bucket", inspect.signature(self.ledger.claim_submission).parameters)
        limits = {"dream": 2, "strong_fit": 5, "adjacent": 3}
        for day_index, (bucket, limit) in enumerate(limits.items(), start=1):
            japan_day = f"2026-08-0{day_index}"
            for index in range(limit):
                application_id = self.ledger.add_application(
                    f"{bucket}-{index}",
                    "AI Role",
                    f"https://jobs.example.com/{bucket}-{index}",
                )
                self._ready(application_id)
                self.assertIsNotNone(
                    self._claim(
                        self.ledger,
                        application_id,
                        japan_day,
                        f"{bucket}-hash-{index}",
                        portfolio_bucket=bucket,
                    )
                )
            overflow_id = self.ledger.add_application(
                f"{bucket}-overflow",
                "AI Role",
                f"https://jobs.example.com/{bucket}-overflow",
            )
            self._ready(overflow_id)
            self.assertIsNone(
                self._claim(
                    self.ledger,
                    overflow_id,
                    japan_day,
                    f"{bucket}-overflow-hash",
                    portfolio_bucket=bucket,
                )
            )

    def test_duplicate_job_returns_same_application(self):
        duplicate = self.ledger.add_application(
            " example ",
            "ai engineer",
            "https://jobs.example.com/42/?utm_campaign=test",
        )
        self.assertEqual(duplicate, self.application_id)

    def test_application_owner_is_validated_and_persisted(self):
        self.assertIn("owner", inspect.signature(self.ledger.add_application).parameters)
        manual_id = self.ledger.add_application(
            "Manual Co",
            "AI Engineer",
            "https://jobs.example.com/manual-owner",
            owner="dais_manual",
        )
        recruiter_id = self.ledger.add_application(
            "Recruiter Co",
            "AI Engineer",
            "https://jobs.example.com/recruiter-owner",
            owner="recruiter",
        )

        self.assertEqual(self.ledger.application_owner(self.application_id), "agent")
        self.assertEqual(self.ledger.application_owner(manual_id), "dais_manual")
        self.assertEqual(self.ledger.application_owner(recruiter_id), "recruiter")
        with self.assertRaisesRegex(ValueError, "owner"):
            self.ledger.add_application(
                "Invalid Co",
                "AI Engineer",
                "https://jobs.example.com/invalid-owner",
                owner="other",
            )

    def test_application_owner_is_immutable(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "owner is immutable"):
            self.ledger.connection.execute(
                "UPDATE applications SET owner = 'dais_manual' WHERE id = ?",
                (self.application_id,),
            )

    def test_same_owner_canonical_url_replay_is_idempotent(self):
        first = self.ledger.add_application(
            "Manual Co",
            "AI Engineer",
            "https://jobs.example.com/shared?utm_source=one",
            owner="dais_manual",
        )
        replay = self.ledger.add_application(
            "Manual Company",
            "Senior AI Engineer",
            "https://jobs.example.com/shared?utm_source=two",
            owner="dais_manual",
        )
        self.assertEqual(replay, first)

    def test_cross_owner_canonical_url_is_fenced(self):
        self.ledger.add_application(
            "Manual Co",
            "AI Engineer",
            "https://jobs.example.com/shared-owner",
            owner="dais_manual",
        )
        with self.assertRaisesRegex(FenceError, "owned by dais_manual"):
            self.ledger.add_application(
                "Recruiter Co",
                "Senior AI Engineer",
                "https://jobs.example.com/shared-owner?utm_source=recruiter",
                owner="recruiter",
            )

    def test_attributed_agent_cannot_adopt_manual_posting(self):
        self.ledger.add_application(
            "Manual Co",
            "AI Engineer",
            "https://jobs.example.com/manual-attributed",
            owner="dais_manual",
        )
        generation_id = self.ledger.record_strategy_generation({"threshold": 75})
        with self.assertRaisesRegex(FenceError, "owned by dais_manual"):
            self.ledger.add_attributed_application(
                "Manual Co Renamed",
                "Senior AI Engineer",
                "https://jobs.example.com/manual-attributed?utm_source=agent",
                strategy_generation_id=generation_id,
                source="official_ats",
                query_family="strong_fit",
                rank_config={"threshold": 75},
                role_family="applied_ai",
                material_variant="engineering_en_v2",
                message_variant="none",
                model_route="terra-medium",
                prompt_sha256="a" * 64,
                material_sha256="b" * 64,
            )

    def test_application_research_and_drafts_form_an_immutable_artifact_chain(self):
        artifacts = [
            ("posting", "Official posting text", [], ["https://jobs.example.com/42"]),
            ("company_research", "Official company research", [], ["https://example.com/about"]),
            ("resume_draft", "Grounded resume", ["fact-1"], []),
            ("cover_letter_draft", "Grounded cover letter", ["fact-1"], []),
            ("answers_draft", "Grounded employer answers", ["fact-1"], []),
        ]
        recorded = []
        for index, (kind, content, fact_ids, source_urls) in enumerate(artifacts):
            path = Path(self.tempdir.name) / f"artifact-{index}.txt"
            path.write_text(content, encoding="utf-8")
            path.chmod(0o600)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            artifact_id = self.ledger.record_application_artifact(
                application_id=self.application_id,
                kind=kind,
                path=path,
                sha256=digest,
                fact_ids=fact_ids,
                source_urls=source_urls,
            )
            recorded.append((artifact_id, kind, str(path.resolve()), digest))

        chain = self.ledger.application_artifact_chain(self.application_id)

        self.assertEqual(
            [(row["artifact_id"], row["kind"], row["path"], row["sha256"]) for row in chain],
            recorded,
        )
        self.assertEqual(chain[2]["fact_ids"], ["fact-1"])
        self.assertEqual(chain[0]["source_urls"], ["https://jobs.example.com/42"])
        with self.assertRaises(Exception):
            self.ledger.connection.execute(
                "UPDATE application_artifacts SET kind='posting' WHERE artifact_id=?",
                (recorded[2][0],),
            )

    def test_application_artifact_rejects_hash_mismatch(self):
        path = Path(self.tempdir.name) / "posting.txt"
        path.write_text("Official posting", encoding="utf-8")
        path.chmod(0o600)

        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.ledger.record_application_artifact(
                application_id=self.application_id,
                kind="posting",
                path=path,
                sha256="0" * 64,
                fact_ids=[],
                source_urls=["https://jobs.example.com/42"],
            )

    def test_upskill_projection_rebuilds_from_immutable_ranked_gaps(self):
        second = self.ledger.add_application(
            "Second", "AI Engineer", "https://jobs.example.com/43"
        )
        self.ledger.record_ranked_gaps(
            application_id=self.application_id,
            score=80,
            gaps=["Kubernetes", "Advanced Python"],
            evidence_sha256="1" * 64,
        )
        self.ledger.record_ranked_gaps(
            application_id=second,
            score=60,
            gaps=["Kubernetes", "MLOps"],
            evidence_sha256="2" * 64,
        )

        projection = self.ledger.upskill_projection(profile_skills=["Python"])

        self.assertEqual(projection["analysed_jobs"], 2)
        self.assertEqual(projection["jobs_without_recorded_gaps"], 0)
        self.assertEqual(
            [(row["gap"], row["job_count"], row["weighted_score"]) for row in projection["gaps"]],
            [("Kubernetes", 2, 0.6), ("MLOps", 1, 0.4)],
        )
        self.assertNotIn("Advanced Python", json.dumps(projection))
        self.assertEqual(len(projection["projection_sha256"]), 64)
        replay = self.ledger.upskill_projection(profile_skills=["Python"])
        self.assertEqual(replay, projection)
        with self.assertRaises(Exception):
            self.ledger.connection.execute(
                "UPDATE application_ranked_gaps SET score=100 WHERE application_id=?",
                (self.application_id,),
            )

    def test_upskill_projection_counts_jobs_without_persisted_gaps_without_guessing(self):
        projection = self.ledger.upskill_projection(profile_skills=[])
        self.assertEqual(projection["analysed_jobs"], 0)
        self.assertEqual(projection["jobs_without_recorded_gaps"], 1)
        self.assertEqual(projection["gaps"], [])

    def test_followups_are_due_after_ten_days_and_capped_at_two(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-08-01", "followup-payload"
        )
        self.ledger.complete_submission(intent.intent_id, intent.fence, "submitted")

        first_due = self.ledger.due_followups("2100-01-01T00:00:00+00:00")
        self.assertEqual(first_due[0]["application_id"], self.application_id)
        self.assertEqual(first_due[0]["ordinal"], 1)
        first_id = self.ledger.record_followup(
            application_id=self.application_id,
            ordinal=1,
            sent_at="2100-01-01T00:00:00+00:00",
            evidence_sha256="1" * 64,
        )
        replay_id = self.ledger.record_followup(
            application_id=self.application_id,
            ordinal=1,
            sent_at="2100-01-01T00:00:00+00:00",
            evidence_sha256="1" * 64,
        )
        self.assertEqual(replay_id, first_id)
        self.assertEqual(self.ledger.due_followups("2100-01-10T23:59:59+00:00"), [])
        second_due = self.ledger.due_followups("2100-01-11T00:00:00+00:00")
        self.assertEqual(second_due[0]["ordinal"], 2)
        self.ledger.record_followup(
            application_id=self.application_id,
            ordinal=2,
            sent_at="2100-01-11T00:00:00+00:00",
            evidence_sha256="2" * 64,
        )
        self.assertEqual(self.ledger.due_followups("2101-01-01T00:00:00+00:00"), [])

    def test_outcome_stops_followups_and_archive_rebuilds_the_chain(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-08-01", "archive-payload"
        )
        self.ledger.complete_submission(intent.intent_id, intent.fence, "submitted")
        self.ledger.record_funnel_outcome(
            application_id=self.application_id,
            funnel_stage="recruiter_response",
            disposition="positive",
            evidence_source="gmail",
            evidence_sha256="3" * 64,
            occurred_at="2099-12-01T00:00:00+00:00",
            observed_at="2099-12-01T00:01:00+00:00",
        )

        self.assertEqual(self.ledger.due_followups("2100-01-01T00:00:00+00:00"), [])
        archive = self.ledger.application_archive(self.application_id)
        self.assertEqual(archive["application"]["id"], self.application_id)
        self.assertEqual(archive["outcomes"][0]["funnel_stage"], "recruiter_response")
        self.assertIn("artifacts", archive)
        self.assertIn("followups", archive)

    def test_events_reconstruct_state_after_reopen(self):
        self._ready()
        self.ledger.close()
        self.ledger = Ledger(self.db)
        self.assertEqual(
            self.ledger.current_state(self.application_id), "materials_ready"
        )
        self.assertEqual(len(self.ledger.events(self.application_id)), 3)

    def test_daily_quota_allows_ten_and_blocks_eleventh(self):
        for index in range(10):
            application_id = self.ledger.add_application(
                f"Company {index}",
                "GenAI Engineer",
                f"https://jobs.example.com/quota-{index}",
            )
            self._ready(application_id)
            intent = self._claim(
                self.ledger, application_id, "2026-07-28", f"hash-{index}"
            )
            self.assertIsNotNone(intent)
            status = "submitted" if index % 2 == 0 else "submit_unknown"
            self.ledger.complete_submission(intent.intent_id, intent.fence, status)

        eleventh_id = self.ledger.add_application(
            "Company 11", "AI Product Engineer", "https://jobs.example.com/quota-11"
        )
        self._ready(eleventh_id)
        self.assertIsNone(
            self._claim(self.ledger, eleventh_id, "2026-07-28", "hash-11")
        )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-28"), 10)

    def test_not_submitted_releases_observable_daily_slot(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash"
        )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-28"), 1)
        self.ledger.complete_submission(
            intent.intent_id, intent.fence, "not_submitted"
        )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-28"), 0)

    def test_not_submitted_reopens_with_new_fence_and_attempt_history(self):
        self._ready()
        first = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash-before"
        )
        self.ledger.complete_submission(
            first.intent_id, first.fence, "not_submitted"
        )

        retryable = self.ledger.retryable_applications()
        self.assertEqual(
            retryable,
            [
                {
                    "application_id": self.application_id,
                    "company": "Example",
                    "title": "AI Engineer",
                    "canonical_url": "https://jobs.example.com/42",
                    "intent_id": first.intent_id,
                    "fence": 1,
                }
            ],
        )

        second = self._claim(
            self.ledger, self.application_id, "2026-07-29", "hash-after"
        )
        self.assertIsNotNone(second)
        self.assertEqual(second.intent_id, first.intent_id)
        self.assertEqual(second.fence, first.fence + 1)
        self.assertEqual(self.ledger.current_state(self.application_id), "submit_claimed")
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 1)
        self.assertEqual(self.ledger.retryable_applications(), [])

        with self.assertRaises(FenceError):
            self.ledger.complete_submission(
                first.intent_id, first.fence, "submitted"
            )

        attempts = self.ledger.submission_attempts(self.application_id)
        self.assertEqual(
            [(row["fence"], row["payload_hash"], row["status"]) for row in attempts],
            [
                (1, "hash-before", "not_submitted"),
                (2, "hash-after", "submit_claimed"),
            ],
        )

        self.ledger.complete_submission(
            second.intent_id, second.fence, "submitted"
        )
        self.assertEqual(
            [(row["fence"], row["status"]) for row in self.ledger.submission_attempts(self.application_id)],
            [(1, "not_submitted"), (2, "submitted")],
        )

    def test_stale_fence_cannot_complete(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash"
        )
        with self.assertRaises(FenceError):
            self.ledger.complete_submission(
                intent.intent_id, intent.fence + 1, "submitted"
            )

    def test_unknown_is_not_retried(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash"
        )
        self.ledger.complete_submission(
            intent.intent_id, intent.fence, "submit_unknown"
        )
        self.assertIsNone(
            self._claim(
                self.ledger, self.application_id, "2026-07-29", "new-hash"
            )
        )

    def test_submitted_is_not_retried(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash"
        )
        self.ledger.complete_submission(intent.intent_id, intent.fence, "submitted")
        self.assertIsNone(
            self._claim(
                self.ledger, self.application_id, "2026-07-29", "new-hash"
            )
        )
        self.assertEqual(self.ledger.retryable_applications(), [])

    def test_existing_intent_is_backfilled_into_attempt_history(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "legacy-hash"
        )
        self.ledger.complete_submission(
            intent.intent_id, intent.fence, "not_submitted"
        )
        self.ledger.connection.execute("DROP TABLE submission_material_receipts")
        self.ledger.connection.execute("DROP TABLE submission_click_phases")
        self.ledger.connection.execute("DROP TABLE submission_attempts")
        self.ledger.close()

        self.ledger = Ledger(self.db)
        attempts = self.ledger.submission_attempts(self.application_id)
        self.assertEqual(
            [(row["fence"], row["payload_hash"], row["status"]) for row in attempts],
            [(1, "legacy-hash", "not_submitted")],
        )

    def test_concurrent_claims_never_exceed_ten(self):
        ids = [self.application_id]
        for index in range(1, 20):
            ids.append(
                self.ledger.add_application(
                    f"Company {index}",
                    "AI Engineer",
                    f"https://jobs.example.com/{index + 100}",
                )
            )
        for application_id in ids:
            self._ready(application_id)
        self.ledger.close()
        results = []
        lock = threading.Lock()

        def claim(application_id):
            local = Ledger(self.db)
            try:
                result = self._claim(
                    local,
                    application_id,
                    "2026-07-28",
                    f"hash-{application_id}",
                )
                with lock:
                    results.append(result)
            finally:
                local.close()

        threads = [threading.Thread(target=claim, args=(value,)) for value in ids]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.ledger = Ledger(self.db)
        self.assertEqual(sum(value is not None for value in results), 10)

    def test_snapshot_hash_mismatch_cannot_claim_or_consume_slot(self):
        self._ready()
        with self.assertRaisesRegex(ValueError, "ATS snapshot SHA-256"):
            self.ledger.claim_submission(
                self.application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=Path(self.tempdir.name) / "missing.json",
                ats_snapshot_sha256="0" * 64,
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_non_ready_snapshot_cannot_claim_or_consume_slot(self):
        self._ready()
        snapshot = Path(self.tempdir.name) / "not-ready.json"
        snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": "https://jobs.example.com/42",
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": "https://jobs.example.com/42",
                            "controls": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "ATS snapshot is not ready"):
            self.ledger.claim_submission(
                self.application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=snapshot,
                ats_snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_snapshot_for_another_job_cannot_claim_or_consume_slot(self):
        self._ready()
        snapshot = Path(self.tempdir.name) / "wrong-job.json"
        snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": "https://jobs.example.com/another-job",
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": "https://jobs.example.com/another-job",
                            "controls": [
                                {"tag": "input", "type": "email"},
                                {"tag": "input", "type": "file"},
                                {
                                    "tag": "button",
                                    "type": "submit",
                                    "text": "Submit Application",
                                },
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "ATS snapshot URL"):
            self.ledger.claim_submission(
                self.application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=snapshot,
                ats_snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_workday_job_surface_is_ready_for_navigation_but_not_for_claim(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "ats"
            / "workday-job-surface.json"
        )
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        application_id = self.ledger.add_application(
            "Example Workday",
            "AI Sales Engineer",
            snapshot["url"],
        )
        self._ready(application_id)
        with self.assertRaisesRegex(ValueError, "ATS snapshot is not claim-ready"):
            self.ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=fixture,
                ats_snapshot_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_workday_apply_choice_is_ready_for_navigation_but_not_for_claim(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "ats"
            / "workday-apply-choice-surface.json"
        )
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        application_id = self.ledger.add_application(
            "Example Workday Choice",
            "AI Sales Engineer",
            snapshot["url"],
        )
        self._ready(application_id)
        with self.assertRaisesRegex(ValueError, "ATS snapshot is not claim-ready"):
            self.ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=fixture,
                ats_snapshot_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_workday_account_gate_is_ready_for_navigation_but_not_for_claim(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "ats"
            / "workday-create-account-surface.json"
        )
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        application_id = self.ledger.add_application(
            "Example Workday Account",
            "AI Sales Engineer",
            snapshot["url"],
        )
        self._ready(application_id)
        with self.assertRaisesRegex(ValueError, "ATS snapshot is not claim-ready"):
            self.ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=fixture,
                ats_snapshot_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_submitted_application_retains_exact_resume_for_reporting(self):
        parameters = inspect.signature(self.ledger.claim_submission).parameters
        self.assertIn("resume_path", parameters)
        self.assertIn("resume_sha256", parameters)
        self.assertIn("ats_snapshot_path", parameters)
        self.assertIn("ats_snapshot_sha256", parameters)
        reports = getattr(self.ledger, "submitted_resume_reports", None)
        self.assertIsNotNone(reports)

        resume = Path(self.tempdir.name) / "Daisuke_AI_Resume.pdf"
        resume.write_bytes(b"%PDF-1.4\nverified resume\n")
        resume_sha256 = hashlib.sha256(resume.read_bytes()).hexdigest()
        self._ready()
        ats_snapshot = Path(self.tempdir.name) / f"ats-{self.application_id}.json"
        ats_snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": "https://jobs.example.com/42",
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": "https://jobs.example.com/42",
                            "controls": [
                                {"tag": "input", "type": "email"},
                                {"tag": "input", "type": "file"},
                                {
                                    "tag": "button",
                                    "type": "submit",
                                    "text": "Submit Application",
                                },
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        ats_sha256 = hashlib.sha256(ats_snapshot.read_bytes()).hexdigest()
        intent = self.ledger.claim_submission(
            self.application_id,
            "2026-07-29",
            "payload-hash",
            resume_path=resume,
            resume_sha256=resume_sha256,
            ats_snapshot_path=ats_snapshot,
            ats_snapshot_sha256=ats_sha256,
        )
        self.assertEqual(intent.ats_snapshot_path, str(ats_snapshot.resolve()))
        self.assertEqual(intent.ats_snapshot_sha256, ats_sha256)
        self.ledger.record_submission_materials(
            intent_id=intent.intent_id,
            fence=intent.fence,
            resume_path=resume,
            resume_sha256=resume_sha256,
            cover_letter=None,
            employer_answers=[],
        )
        self.ledger.complete_submission(intent.intent_id, intent.fence, "submitted")

        self.assertEqual(
            reports(),
            [
                {
                    "application_id": self.application_id,
                    "company": "Example",
                    "title": "AI Engineer",
                    "canonical_url": "https://jobs.example.com/42",
                    "resume_path": str(resume.resolve()),
                    "resume_sha256": resume_sha256,
                }
            ],
        )

    def test_submission_material_receipt_binds_exact_inputs_to_intent_fence(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-29", "payload-hash",
            record_materials=False,
        )
        receipt = self.ledger.record_submission_materials(
            intent_id=intent.intent_id,
            fence=intent.fence,
            resume_path=self.resume,
            resume_sha256=self.resume_sha256,
            cover_letter="Grounded exact letter",
            employer_answers=[
                {
                    "question": "Why this role?",
                    "answer": "Because the verified work aligns.",
                    "fact_ids": ["fact-1"],
                }
            ],
        )
        replay = self.ledger.record_submission_materials(
            intent_id=intent.intent_id,
            fence=intent.fence,
            resume_path=self.resume,
            resume_sha256=self.resume_sha256,
            cover_letter="Grounded exact letter",
            employer_answers=[
                {
                    "question": "Why this role?",
                    "answer": "Because the verified work aligns.",
                    "fact_ids": ["fact-1"],
                }
            ],
        )
        self.assertEqual(replay, receipt)
        row = self.ledger.connection.execute(
            "SELECT * FROM submission_material_receipts"
        ).fetchone()
        self.assertEqual(json.loads(row["employer_answers_json"])[0]["question"], "Why this role?")
        self.assertEqual(row["cover_letter"], "Grounded exact letter")
        self.ledger.complete_submission(intent.intent_id, intent.fence, "submitted")
        self.assertEqual(
            self.ledger.record_submission_materials(
                intent_id=intent.intent_id,
                fence=intent.fence,
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                cover_letter="Grounded exact letter",
                employer_answers=[
                    {
                        "question": "Why this role?",
                        "answer": "Because the verified work aligns.",
                        "fact_ids": ["fact-1"],
                    }
                ],
            ),
            receipt,
        )

    def test_submission_material_rebind_and_unrecorded_submit_fail_closed(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-29", "payload-hash",
            record_materials=False,
        )
        with self.assertRaisesRegex(FenceError, "material receipt"):
            self.ledger.complete_submission(intent.intent_id, intent.fence, "submitted")
        self.ledger.record_submission_materials(
            intent_id=intent.intent_id,
            fence=intent.fence,
            resume_path=self.resume,
            resume_sha256=self.resume_sha256,
            cover_letter=None,
            employer_answers=[],
        )
        with self.assertRaises(FenceError):
            self.ledger.record_submission_materials(
                intent_id=intent.intent_id,
                fence=intent.fence,
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                cover_letter="different",
                employer_answers=[],
            )

    def test_interrupted_submission_before_click_is_retryable(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-08-05", "phase-before"
        )
        self.assertEqual(
            self.ledger.submission_click_phase(intent.intent_id, intent.fence),
            "pre_click",
        )

        outcome = self.ledger.reconcile_interrupted_submission(
            intent.intent_id, intent.fence
        )

        self.assertEqual(outcome, "not_submitted")
        self.assertEqual(self.ledger.current_state(self.application_id), "not_submitted")

    def test_interrupted_submission_after_click_is_never_retried(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-08-05", "phase-after"
        )
        self.assertEqual(
            self.ledger.mark_submission_click_phase(
                intent.intent_id, intent.fence, "clicked"
            ),
            "clicked",
        )

        outcome = self.ledger.reconcile_interrupted_submission(
            intent.intent_id, intent.fence
        )

        self.assertEqual(outcome, "submit_unknown")
        self.assertEqual(self.ledger.current_state(self.application_id), "submit_unknown")
        self.assertIsNone(
            self._claim(
                self.ledger, self.application_id, "2026-08-06", "must-not-retry"
            )
        )

    def test_submission_click_phase_is_ordered_and_fenced(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-08-05", "phase-order"
        )
        with self.assertRaises(FenceError):
            self.ledger.mark_submission_click_phase(
                intent.intent_id, intent.fence, "confirmed"
            )
        self.ledger.mark_submission_click_phase(
            intent.intent_id, intent.fence, "clicked"
        )
        self.assertEqual(
            self.ledger.mark_submission_click_phase(
                intent.intent_id, intent.fence, "confirmed"
            ),
            "confirmed",
        )
        with self.assertRaises(FenceError):
            self.ledger.mark_submission_click_phase(
                intent.intent_id, intent.fence + 1, "clicked"
            )


if __name__ == "__main__":
    unittest.main()
