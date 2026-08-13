import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from job_search_loop.guardian import ledger_health
from job_search_loop.ledger import FenceError, Ledger
from job_search_loop.route_executor import execute_next_message_route
from job_search_loop.summary import build_summary_v2


class RouteExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.ledger = Ledger(root / "ledger.sqlite3")
        self.application_id = self.ledger.add_application(
            "Example", "AI Engineer", "https://jobs.example.test/role"
        )
        self.message = root / "message.txt"
        self.message.write_text("Grounded application message", encoding="utf-8")
        self.resume = root / "resume.pdf"
        self.resume.write_bytes(b"%PDF resume")
        self.source_sha = hashlib.sha256(b"official source").hexdigest()

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def _route(self, kind, endpoint, ordinal, acceptance):
        return self.ledger.register_application_route(
            self.application_id,
            route_kind=kind,
            endpoint=endpoint,
            ordinal=ordinal,
            source_url="https://careers.example.test/jobs",
            source_sha256=self.source_sha,
            recipient_acceptance=acceptance,
        )

    def _advance_to(self, state):
        for target in ("qualified", "materials_ready", "submit_claimed", state):
            self.ledger.transition(self.application_id, target)

    def _deliver_route(self, route_id, *, fence, provider_id, evidence_sha256):
        self.ledger.claim_application_route(
            route_id,
            actor="resident_worker",
            fence=fence,
            message_path=str(self.message),
            message_sha256=hashlib.sha256(self.message.read_bytes()).hexdigest(),
            resume_path=str(self.resume),
            resume_sha256=hashlib.sha256(self.resume.read_bytes()).hexdigest(),
        )
        self.ledger.complete_application_route(
            route_id,
            fence=fence,
            state="delivered",
            provider_id=provider_id,
            evidence_sha256=evidence_sha256,
        )
        return self.ledger.application_routes(self.application_id)[0]

    def _append_legacy_outreach(
        self, application_id, company, *, fence, email_payload=None, project=False
    ):
        route_id = self.ledger.register_application_route(
            application_id,
            route_kind="recruiting_outreach",
            endpoint=f"talent@{company.casefold().replace(' ', '')}.example.test",
            ordinal=4,
            source_url="https://careers.example.test/jobs",
            source_sha256=self.source_sha,
            recipient_acceptance="outreach_only",
        )
        evidence_sha256 = hashlib.sha256(
            f"{application_id}-outreach-receipt".encode()
        ).hexdigest()
        self.ledger.claim_application_route(
            route_id,
            actor="resident_worker",
            fence=fence,
            message_path=str(self.message),
            message_sha256=hashlib.sha256(self.message.read_bytes()).hexdigest(),
            resume_path=str(self.resume),
            resume_sha256=hashlib.sha256(self.resume.read_bytes()).hexdigest(),
        )
        self.ledger.complete_application_route(
            route_id,
            fence=fence,
            state="delivered",
            provider_id=f"gmail:{application_id}",
            evidence_sha256=evidence_sha256,
        )
        if project:
            route = next(
                row for row in self.ledger.application_routes(application_id)
                if row["route_id"] == route_id
            )
            with self.ledger._transaction():
                self.ledger._project_delivered_application_route_in_transaction(
                    row={**route, "recipient_acceptance": "accepts_applications"},
                    provider_id=f"gmail:{application_id}",
                    evidence_sha256=evidence_sha256,
                )
        with self.ledger._transaction():
            self.ledger._append_event(
                application_id,
                "submitted",
                "email_sent",
                email_payload
                if email_payload is not None
                else {
                    "route_id": route_id,
                    "provider_id": f"gmail:{application_id}",
                    "channel": "recruiting_outreach",
                },
            )
            self.ledger.connection.execute(
                "UPDATE applications SET current_state = 'email_sent' WHERE id = ?",
                (application_id,),
            )
        return route_id, evidence_sha256

    def _seed_legacy_outreach(self, company, url, *, fence, email_payload=None):
        application_id = self.ledger.add_application(company, "AI Engineer", url)
        for state in ("qualified", "materials_ready", "submit_claimed", "submitted"):
            self.ledger.transition(application_id, state)
        route_id, evidence_sha256 = self._append_legacy_outreach(
            application_id,
            company,
            fence=fence,
            email_payload=email_payload,
            project=True,
        )
        return application_id, route_id, evidence_sha256

    def _append_forged_correction(
        self, route, *, provider_id=None, evidence_sha256=None
    ):
        with self.ledger._transaction():
            self.ledger._append_event(
                self.application_id,
                "submitted",
                "submit_unknown",
                {
                    "route_id": str(route["route_id"]),
                    "provider_id": provider_id or str(route["provider_id"]),
                    "evidence_sha256": evidence_sha256
                    or str(route["delivery_evidence_sha256"]),
                    "reason": "outreach_only_delivery_correction",
                },
            )
            self.ledger.connection.execute(
                "UPDATE applications SET current_state = 'submit_unknown' WHERE id = ?",
                (self.application_id,),
            )

    def _seed_authoritative_submission_before_outreach(self, company, url, *, fence):
        application_id = self.ledger.add_application(company, "AI Engineer", url)
        for state in ("qualified", "materials_ready", "submit_claimed", "submit_unknown"):
            self.ledger.transition(application_id, state)
        confirmation_sha256 = hashlib.sha256(
            f"{application_id}-gmail-confirmation".encode()
        ).hexdigest()
        with self.ledger._transaction():
            self.ledger._append_event(
                application_id,
                "submit_unknown",
                "submitted",
                {
                    "message_id": f"gmail-message-{application_id}",
                    "thread_id": f"gmail-thread-{application_id}",
                    "evidence_sha256": confirmation_sha256,
                    "received_at": "2026-08-13T00:00:00+00:00",
                },
            )
            self.ledger.connection.execute(
                "UPDATE applications SET current_state = 'submitted' WHERE id = ?",
                (application_id,),
            )
        self._append_legacy_outreach(application_id, company, fence=fence)
        return application_id

    def test_delivered_email_is_sent_once_and_exact_artifacts_are_preserved(self):
        self._route("recruiting_email", "jobs@example.test", 3, "accepts_applications")
        calls = []

        def transport(**payload):
            calls.append(payload)
            return {
                "status": "delivered",
                "provider_id": "gmail:message-42",
                "evidence_sha256": hashlib.sha256(b"provider receipt").hexdigest(),
            }

        first = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=1,
            message_path=self.message,
            resume_path=self.resume,
            transport=transport,
        )
        second = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=2,
            message_path=self.message,
            resume_path=self.resume,
            transport=transport,
        )

        self.assertEqual(first["status"], "delivered")
        self.assertEqual(second["status"], "cross_route_terminal")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["recipient"], "jobs@example.test")
        route = self.ledger.application_routes(self.application_id)[0]
        self.assertEqual(route["message_sha256"], hashlib.sha256(self.message.read_bytes()).hexdigest())
        self.assertEqual(route["resume_sha256"], hashlib.sha256(self.resume.read_bytes()).hexdigest())
        japan_day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        self.assertEqual(self.ledger.current_state(self.application_id), "submitted")
        self.assertEqual(self.ledger.confirmed_daily_count(japan_day), 1)

    def test_delivered_outreach_preserves_receipt_without_confirming_application(self):
        self._route(
            "recruiting_outreach", "talent@example.test", 4, "outreach_only"
        )

        result = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=1,
            message_path=self.message,
            resume_path=self.resume,
            transport=lambda **payload: {
                "status": "delivered",
                "provider_id": "gmail:outreach-42",
                "evidence_sha256": hashlib.sha256(b"outreach receipt").hexdigest(),
            },
        )

        route = self.ledger.application_routes(self.application_id)[0]
        japan_day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        self.assertEqual(result["status"], "delivered")
        self.assertEqual(route["route_kind"], "recruiting_outreach")
        self.assertEqual(route["delivery_state"], "delivered")
        self.assertEqual(route["provider_id"], "gmail:outreach-42")
        self.assertEqual(self.ledger.current_state(self.application_id), "discovered")
        self.assertEqual(self.ledger.confirmed_daily_count(japan_day), 0)
        self.assertEqual(self.ledger.funnel_outcomes(self.application_id), [])

    def test_reconciliation_corrects_run_74_outreach_without_rewriting_receipt(self):
        for state in ("qualified", "materials_ready", "submit_claimed", "submit_unknown"):
            self.ledger.transition(self.application_id, state)
        route_id = self._route(
            "recruiting_outreach", "talent@example.test", 4, "outreach_only"
        )
        evidence_sha256 = hashlib.sha256(b"run 74 outreach receipt").hexdigest()
        self.ledger.claim_application_route(
            route_id,
            actor="resident_worker",
            fence=74,
            message_path=str(self.message),
            message_sha256=hashlib.sha256(self.message.read_bytes()).hexdigest(),
            resume_path=str(self.resume),
            resume_sha256=hashlib.sha256(self.resume.read_bytes()).hexdigest(),
        )
        self.ledger.complete_application_route(
            route_id,
            fence=74,
            state="delivered",
            provider_id="gmail:run-74-outreach",
            evidence_sha256=evidence_sha256,
        )

        route = self.ledger.application_routes(self.application_id)[0]
        with self.ledger._transaction():
            self.ledger._project_delivered_application_route_in_transaction(
                row={**route, "recipient_acceptance": "accepts_applications"},
                provider_id=str(route["provider_id"]),
                evidence_sha256=evidence_sha256,
            )
        self.assertEqual(self.ledger.current_state(self.application_id), "submitted")

        first = self.ledger.reconcile_delivered_application_routes()
        second = self.ledger.reconcile_delivered_application_routes()
        summary = next(
            row
            for row in self.ledger.event_summary_rows()
            if row["application_id"] == self.application_id
        )
        health = ledger_health(self.ledger.path)

        japan_day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        route = self.ledger.application_routes(self.application_id)[0]
        self.assertEqual(first["outreach_correction_count"], 1)
        self.assertEqual(second["outreach_correction_count"], 0)
        self.assertEqual(self.ledger.current_state(self.application_id), "submit_unknown")
        self.assertEqual(self.ledger.confirmed_daily_count(japan_day), 0)
        self.assertEqual(route["provider_id"], "gmail:run-74-outreach")
        self.assertEqual(route["delivery_evidence_sha256"], evidence_sha256)
        self.assertEqual(
            [event["to_state"] for event in self.ledger.application_route_events(route_id)],
            ["eligible", "action_started", "delivered"],
        )
        self.assertEqual(summary["current_state"], "submit_unknown")
        self.assertFalse(summary["ever_submitted"])
        self.assertTrue(summary["submission_attempted"])
        self.assertNotIn("confirmed_application", summary["positive_funnel_stages"])
        self.assertEqual(health["status"], "healthy")
        summary_value = build_summary_v2(
            day=japan_day,
            applications=[
                {
                    **summary,
                    "canonical_url": "https://jobs.ashbyhq.com/example/run-74",
                }
            ],
        )
        self.assertEqual(summary_value["ats_progress"]["confirmed_adapters"], [])

    def test_reconciliation_repairs_every_legacy_outreach_chain_append_only(self):
        first_id, first_route, first_evidence = self._seed_legacy_outreach(
            "Legacy One", "https://jobs.example.test/legacy-one", fence=101
        )
        second_id, second_route, second_evidence = self._seed_legacy_outreach(
            "Legacy Two", "https://jobs.example.test/legacy-two", fence=102
        )
        before_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]
        before_route_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM application_route_events"
        ).fetchone()[0]

        first = self.ledger.reconcile_delivered_application_routes()
        second = self.ledger.reconcile_delivered_application_routes()

        self.assertEqual(first["outreach_correction_count"], 2)
        self.assertEqual(second["outreach_correction_count"], 0)
        for application_id in (first_id, second_id):
            self.assertEqual(
                [row["funnel_stage"] for row in self.ledger.funnel_outcomes(application_id)],
                ["confirmed_application"],
            )
        self.assertEqual(
            self.ledger.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            before_event_count + 2,
        )
        self.assertEqual(
            self.ledger.connection.execute(
                "SELECT COUNT(*) FROM application_route_events"
            ).fetchone()[0],
            before_route_event_count,
        )
        for application_id, route_id, evidence_sha256 in (
            (first_id, first_route, first_evidence),
            (second_id, second_route, second_evidence),
        ):
            self.assertEqual(self.ledger.current_state(application_id), "submit_unknown")
            correction = self.ledger.connection.execute(
                "SELECT from_state, to_state, payload_json FROM events "
                "WHERE application_id = ? ORDER BY rowid DESC LIMIT 1",
                (application_id,),
            ).fetchone()
            self.assertEqual(
                (correction["from_state"], correction["to_state"]),
                ("email_sent", "submit_unknown"),
            )
            payload = json.loads(str(correction["payload_json"]))
            self.assertEqual(payload["route_id"], route_id)
            self.assertEqual(payload["provider_id"], f"gmail:{application_id}")
            self.assertEqual(payload["evidence_sha256"], evidence_sha256)
            summary = next(
                row
                for row in self.ledger.event_summary_rows()
                if row["application_id"] == application_id
            )
            self.assertFalse(summary["ever_submitted"])
            self.assertTrue(summary["submission_attempted"])
            self.assertEqual(
                [
                    row
                    for row in self.ledger.strategy_outcome_projection()
                    if row["funnel_stage"] == "confirmed_application"
                ],
                [],
            )
            self.assertEqual(
                self.ledger.connection.execute(
                    "SELECT status FROM daily_slots WHERE application_id = ?",
                    (application_id,),
                ).fetchone()["status"],
                "submit_unknown",
            )
            self.assertEqual(
                [row["to_state"] for row in self.ledger.application_route_events(route_id)],
                ["eligible", "action_started", "delivered"],
            )
        self.assertEqual(ledger_health(self.ledger.path)["status"], "healthy")

    def test_reconciliation_rejects_unbound_legacy_email_sent_event(self):
        application_id, route_id, evidence_sha256 = self._seed_legacy_outreach(
            "Unbound Legacy",
            "https://jobs.example.test/unbound-legacy",
            fence=103,
            email_payload={},
        )

        result = self.ledger.reconcile_delivered_application_routes()

        self.assertEqual(result["outreach_correction_count"], 0)
        self.assertEqual(self.ledger.current_state(application_id), "email_sent")
        route = self.ledger.application_routes(application_id)[0]
        self.assertEqual(route["route_id"], route_id)
        self.assertEqual(route["delivery_evidence_sha256"], evidence_sha256)
        with self.assertRaises(FenceError):
            self.ledger.event_summary_rows()
        self.assertEqual(ledger_health(self.ledger.path)["status"], "unhealthy")

    def test_reconciliation_preserves_authoritative_submission_before_outreach(self):
        application_id = self._seed_authoritative_submission_before_outreach(
            "Authoritative Before",
            "https://jobs.example.test/authoritative-before",
            fence=104,
        )
        before_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        first = self.ledger.reconcile_delivered_application_routes()
        first_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]
        second = self.ledger.reconcile_delivered_application_routes()
        summary = next(
            row for row in self.ledger.event_summary_rows()
            if row["application_id"] == application_id
        )

        self.assertEqual(first["outreach_correction_count"], 0)
        self.assertEqual(second["outreach_correction_count"], 0)
        self.assertEqual(first_event_count, before_event_count + 1)
        self.assertEqual(
            self.ledger.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            first_event_count,
        )
        self.assertEqual(self.ledger.current_state(application_id), "submitted")
        events = self.ledger.events(application_id)
        self.assertEqual(events[5]["to_state"], "submitted")
        self.assertEqual((events[-1]["from_state"], events[-1]["to_state"]), ("email_sent", "submitted"))
        self.assertTrue(summary["ever_submitted"])
        self.assertEqual(ledger_health(self.ledger.path)["status"], "healthy")

    def test_reconciliation_restores_external_import_before_outreach(self):
        import_evidence = hashlib.sha256(b"external-import-confirmation").hexdigest()
        application_id = self.ledger.import_external_application(
            company="Imported Authority",
            title="AI Engineer",
            owner="dais_manual",
            source="gmail",
            source_message_id="external-import-before-outreach",
            applied_at="2026-08-13T00:00:00+00:00",
            evidence_sha256=import_evidence,
        )["application_id"]
        route_id, outreach_evidence = self._append_legacy_outreach(
            application_id, "Imported Authority", fence=106
        )
        before_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        first = self.ledger.reconcile_delivered_application_routes()
        first_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]
        second = self.ledger.reconcile_delivered_application_routes()
        summary = next(
            row for row in self.ledger.event_summary_rows()
            if row["application_id"] == application_id
        )
        restoration = self.ledger.events(application_id)[-1]
        payload = restoration["payload"]

        self.assertEqual(first["outreach_correction_count"], 0)
        self.assertEqual(second["outreach_correction_count"], 0)
        self.assertEqual(first_event_count, before_event_count + 1)
        self.assertEqual(
            self.ledger.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            first_event_count,
        )
        self.assertEqual((restoration["from_state"], restoration["to_state"]), ("email_sent", "submitted"))
        self.assertEqual(payload["route_id"], route_id)
        self.assertEqual(payload["evidence_sha256"], outreach_evidence)
        self.assertEqual(self.ledger.current_state(application_id), "submitted")
        self.assertTrue(summary["ever_submitted"])
        self.assertEqual(ledger_health(self.ledger.path)["status"], "healthy")

    def test_reconciliation_restores_delivered_alternate_official_before_outreach(self):
        ats_route_id = self._route(
            "alternate_official",
            "https://jobs.example.test/alternate-official",
            2,
            "not_applicable",
        )
        ats_evidence = hashlib.sha256(b"alternate-official-receipt").hexdigest()
        self._deliver_route(
            ats_route_id,
            fence=107,
            provider_id="ats:alternate-official",
            evidence_sha256=ats_evidence,
        )
        ats_route_before = next(
            route for route in self.ledger.application_routes(self.application_id)
            if route["route_id"] == ats_route_id
        )
        ats_events_before = self.ledger.application_route_events(ats_route_id)
        outcomes_before = self.ledger.funnel_outcomes(self.application_id)
        self._append_legacy_outreach(self.application_id, "Example", fence=108)
        before_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        first = self.ledger.reconcile_delivered_application_routes()
        first_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]
        second = self.ledger.reconcile_delivered_application_routes()
        summary = next(
            row for row in self.ledger.event_summary_rows()
            if row["application_id"] == self.application_id
        )

        self.assertEqual(first["outreach_correction_count"], 0)
        self.assertEqual(second["outreach_correction_count"], 0)
        self.assertEqual(first_event_count, before_event_count + 1)
        self.assertEqual(
            self.ledger.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            first_event_count,
        )
        self.assertEqual(self.ledger.current_state(self.application_id), "submitted")
        self.assertTrue(summary["ever_submitted"])
        self.assertEqual(ledger_health(self.ledger.path)["status"], "healthy")
        self.assertEqual(
            next(
                route for route in self.ledger.application_routes(self.application_id)
                if route["route_id"] == ats_route_id
            ),
            ats_route_before,
        )
        self.assertEqual(self.ledger.application_route_events(ats_route_id), ats_events_before)
        self.assertEqual(self.ledger.funnel_outcomes(self.application_id), outcomes_before)

    def test_reconciliation_restores_replied_canonical_ats_before_outreach(self):
        ats_route_id = self._route(
            "canonical_ats",
            "https://jobs.example.test/canonical-replied",
            1,
            "not_applicable",
        )
        self._deliver_route(
            ats_route_id,
            fence=109,
            provider_id="ats:canonical-replied",
            evidence_sha256=hashlib.sha256(b"canonical-delivered-receipt").hexdigest(),
        )
        self.ledger.record_application_route_reply(
            ats_route_id,
            provider_id="ats:canonical-reply",
            evidence_sha256=hashlib.sha256(b"canonical-reply-receipt").hexdigest(),
        )
        self._append_legacy_outreach(self.application_id, "Example", fence=110)
        before_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        first = self.ledger.reconcile_delivered_application_routes()
        first_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]
        second = self.ledger.reconcile_delivered_application_routes()
        summary = next(
            row for row in self.ledger.event_summary_rows()
            if row["application_id"] == self.application_id
        )
        ats_route = next(
            route for route in self.ledger.application_routes(self.application_id)
            if route["route_id"] == ats_route_id
        )

        self.assertEqual(first["outreach_correction_count"], 0)
        self.assertEqual(second["outreach_correction_count"], 0)
        self.assertEqual(first_event_count, before_event_count + 1)
        self.assertEqual(
            self.ledger.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            first_event_count,
        )
        self.assertEqual(ats_route["delivery_state"], "replied")
        self.assertEqual(self.ledger.current_state(self.application_id), "submitted")
        self.assertTrue(summary["ever_submitted"])
        self.assertEqual(ledger_health(self.ledger.path)["status"], "healthy")

    def test_replied_canonical_ats_preserves_restored_submission_health(self):
        ats_route_id = self._route(
            "canonical_ats",
            "https://jobs.example.test/canonical-restored",
            1,
            "not_applicable",
        )
        self._deliver_route(
            ats_route_id,
            fence=111,
            provider_id="ats:canonical-restored",
            evidence_sha256=hashlib.sha256(b"canonical-restored-receipt").hexdigest(),
        )
        self._append_legacy_outreach(self.application_id, "Example", fence=112)
        before_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        restored = self.ledger.reconcile_delivered_application_routes()
        restored_event_count = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]
        self.ledger.record_application_route_reply(
            ats_route_id,
            provider_id="ats:canonical-restored-reply",
            evidence_sha256=hashlib.sha256(b"canonical-restored-reply").hexdigest(),
        )
        summary = next(
            row for row in self.ledger.event_summary_rows()
            if row["application_id"] == self.application_id
        )

        self.assertEqual(restored["outreach_correction_count"], 0)
        self.assertEqual(restored_event_count, before_event_count + 1)
        self.assertEqual(
            self.ledger.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            restored_event_count,
        )
        self.assertEqual(self.ledger.current_state(self.application_id), "submitted")
        self.assertEqual(summary["current_state"], "submitted")
        self.assertTrue(summary["ever_submitted"])
        self.assertEqual(ledger_health(self.ledger.path)["status"], "healthy")

    def test_reconciliation_preserves_authoritative_submission_after_outreach_correction(self):
        application_id, _, _ = self._seed_legacy_outreach(
            "Authoritative After",
            "https://jobs.example.test/authoritative-after",
            fence=105,
        )
        first = self.ledger.reconcile_delivered_application_routes()
        confirmation_sha256 = hashlib.sha256(
            f"{application_id}-late-gmail-confirmation".encode()
        ).hexdigest()
        with self.ledger._transaction():
            self.ledger._append_event(
                application_id,
                "submit_unknown",
                "submitted",
                {
                    "message_id": f"late-gmail-message-{application_id}",
                    "thread_id": f"late-gmail-thread-{application_id}",
                    "evidence_sha256": confirmation_sha256,
                    "received_at": "2026-08-13T01:00:00+00:00",
                },
            )
            self.ledger.connection.execute(
                "UPDATE applications SET current_state = 'submitted' WHERE id = ?",
                (application_id,),
            )

        self.assertEqual(first["outreach_correction_count"], 1)
        summary = next(
            row
            for row in self.ledger.event_summary_rows()
            if row["application_id"] == application_id
        )
        self.assertEqual(self.ledger.current_state(application_id), "submitted")
        self.assertTrue(summary["ever_submitted"])
        self.assertTrue(summary["submission_attempted"])
        self.assertEqual(ledger_health(self.ledger.path)["status"], "healthy")

    def test_correction_rejects_accepted_email_route(self):
        self._advance_to("submit_unknown")
        route = self._deliver_route(
            self._route(
                "recruiting_email", "jobs@example.test", 3, "accepts_applications"
            ),
            fence=74,
            provider_id="gmail:accepted-email",
            evidence_sha256=hashlib.sha256(b"accepted email receipt").hexdigest(),
        )
        self._append_forged_correction(route)

        with self.assertRaises(FenceError):
            self.ledger.event_summary_rows()
        self.assertEqual(ledger_health(self.ledger.path)["status"], "unhealthy")

    def test_correction_rejects_mismatched_delivery_receipt(self):
        self._advance_to("submit_unknown")
        route = self._deliver_route(
            self._route(
                "recruiting_outreach", "talent@example.test", 4, "outreach_only"
            ),
            fence=74,
            provider_id="gmail:outreach-verified",
            evidence_sha256=hashlib.sha256(b"verified outreach receipt").hexdigest(),
        )
        with self.ledger._transaction():
            self.ledger._project_delivered_application_route_in_transaction(
                row={**route, "recipient_acceptance": "accepts_applications"},
                provider_id=str(route["provider_id"]),
                evidence_sha256=str(route["delivery_evidence_sha256"]),
            )
        self._append_forged_correction(route, provider_id="gmail:forged")

        with self.assertRaises(FenceError):
            self.ledger.event_summary_rows()
        self.assertEqual(ledger_health(self.ledger.path)["status"], "unhealthy")

    def test_guardian_requires_correction_to_follow_legacy_projection(self):
        self._advance_to("submitted")
        route = self._deliver_route(
            self._route(
                "recruiting_outreach", "talent@example.test", 4, "outreach_only"
            ),
            fence=74,
            provider_id="gmail:outreach-verified",
            evidence_sha256=hashlib.sha256(b"verified outreach receipt").hexdigest(),
        )
        self._append_forged_correction(route)
        with self.ledger._transaction():
            self.ledger._append_event(
                self.application_id,
                "submit_unknown",
                "submitted",
                {
                    "route_id": str(route["route_id"]),
                    "provider_id": str(route["provider_id"]),
                    "channel": "recruiting_outreach",
                },
            )
            self.ledger.connection.execute(
                "UPDATE applications SET current_state = 'submitted' WHERE id = ?",
                (self.application_id,),
            )

        self.assertEqual(ledger_health(self.ledger.path)["status"], "unhealthy")

    def test_transport_exception_is_unknown_and_never_retried(self):
        self._route("recruiting_outreach", "talent@example.test", 4, "outreach_only")
        calls = []

        def transport(**payload):
            calls.append(payload)
            raise TimeoutError("request outcome unknown")

        first = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=1,
            message_path=self.message,
            resume_path=self.resume,
            transport=transport,
        )
        second = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=2,
            message_path=self.message,
            resume_path=self.resume,
            transport=transport,
        )

        self.assertEqual(first["status"], "delivery_unknown")
        self.assertEqual(second["status"], "cross_route_terminal")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["route_kind"], "recruiting_email")

    def test_message_executor_does_not_skip_an_eligible_browser_route(self):
        self._route("canonical_ats", "https://jobs.example.test/role", 1, "not_applicable")
        self._route("recruiting_email", "jobs@example.test", 3, "accepts_applications")

        result = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=1,
            message_path=self.message,
            resume_path=self.resume,
            transport=lambda **payload: self.fail("email route skipped canonical ATS"),
        )

        self.assertEqual(result["status"], "browser_route_required")

    def test_unconfirmed_ats_action_routes_same_application_to_email(self):
        ats = self._route(
            "canonical_ats", "https://jobs.example.test/role", 1, "not_applicable"
        )
        self._route(
            "recruiting_email", "jobs@example.test", 3, "accepts_applications"
        )
        self.ledger.claim_application_route(
            ats,
            actor="resident_worker",
            fence=1,
            message_path=str(self.message),
            message_sha256=hashlib.sha256(self.message.read_bytes()).hexdigest(),
            resume_path=str(self.resume),
            resume_sha256=hashlib.sha256(self.resume.read_bytes()).hexdigest(),
        )
        calls = []

        def transport(**payload):
            calls.append(payload)
            return {
                "status": "delivered",
                "provider_id": "gmail:fallback-42",
                "evidence_sha256": hashlib.sha256(b"fallback sent").hexdigest(),
            }

        result = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=2,
            message_path=self.message,
            resume_path=self.resume,
            transport=transport,
        )

        self.assertEqual(result["status"], "delivered")
        self.assertEqual(result["provider_id"], "gmail:fallback-42")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["route_kind"], "recruiting_email")
        self.assertEqual(calls[0]["resume_path"], str(self.resume.resolve()))

    def test_confirmed_ats_application_does_not_send_fallback_email(self):
        ats = self._route(
            "canonical_ats", "https://jobs.example.test/role", 1, "not_applicable"
        )
        self._route(
            "recruiting_email", "jobs@example.test", 3, "accepts_applications"
        )
        self.ledger.claim_application_route(
            ats,
            actor="resident_worker",
            fence=1,
            message_path=str(self.message),
            message_sha256=hashlib.sha256(self.message.read_bytes()).hexdigest(),
            resume_path=str(self.resume),
            resume_sha256=hashlib.sha256(self.resume.read_bytes()).hexdigest(),
        )
        self.ledger.complete_application_route(
            ats,
            fence=1,
            state="delivered",
            provider_id="ashby:confirmed-42",
            evidence_sha256=hashlib.sha256(b"ATS confirmed").hexdigest(),
        )

        result = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=2,
            message_path=self.message,
            resume_path=self.resume,
            transport=lambda **payload: self.fail("confirmed ATS sent fallback email"),
        )

        self.assertEqual(result["status"], "ats_confirmed")

    def test_malformed_post_send_receipt_becomes_delivery_unknown(self):
        self._route("recruiting_email", "jobs@example.test", 3, "accepts_applications")

        result = execute_next_message_route(
            ledger=self.ledger,
            application_id=self.application_id,
            actor="resident_worker",
            fence=1,
            message_path=self.message,
            resume_path=self.resume,
            transport=lambda **payload: {"status": "delivered"},
        )

        self.assertEqual(result["status"], "delivery_unknown")
        self.assertEqual(
            self.ledger.application_routes(self.application_id)[0]["delivery_state"],
            "delivery_unknown",
        )


if __name__ == "__main__":
    unittest.main()
