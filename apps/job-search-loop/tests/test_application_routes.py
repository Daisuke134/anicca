import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import FenceError, Ledger


class ApplicationRouteLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.tempdir.name) / "ledger.sqlite3")
        self.application_id = self.ledger.add_application(
            "Example, Inc.",
            "AI Deployment Engineer (Tokyo)",
            "https://jobs.example.test/role",
        )
        self.source_sha = hashlib.sha256(b"official source").hexdigest()

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def _route(self, kind, endpoint, ordinal, *, acceptance="not_applicable"):
        return self.ledger.register_application_route(
            self.application_id,
            route_kind=kind,
            endpoint=endpoint,
            ordinal=ordinal,
            source_url="https://careers.example.test/contact",
            source_sha256=self.source_sha,
            recipient_acceptance=acceptance,
        )

    def test_routes_share_cross_route_key_and_are_returned_in_ladder_order(self):
        self._route("recruiting_outreach", "recruiter@example.test", 4)
        self._route("canonical_ats", "https://jobs.example.test/role", 1)
        self._route("alternate_official", "https://careers.example.test/role", 2)
        self._route(
            "recruiting_email",
            "jobs@example.test",
            3,
            acceptance="accepts_applications",
        )

        routes = self.ledger.application_routes(self.application_id)

        self.assertEqual([route["ordinal"] for route in routes], [1, 2, 3, 4])
        self.assertEqual(len({route["cross_route_key"] for route in routes}), 1)
        self.assertEqual(routes[0]["cross_route_key"], "example::ai deployment engineer")

    def test_ats_and_email_have_independent_at_most_once_action_fences(self):
        ats = self._route("canonical_ats", "https://jobs.example.test/role", 1)
        alternate_ats = self._route(
            "alternate_official", "https://careers.example.test/role", 2
        )
        email = self._route(
            "recruiting_email",
            "jobs@example.test",
            3,
            acceptance="accepts_applications",
        )
        second_email = self._route(
            "recruiting_email",
            "talent@example.test",
            4,
            acceptance="accepts_applications",
        )
        message_sha = hashlib.sha256(b"exact message").hexdigest()
        resume_sha = hashlib.sha256(b"resume").hexdigest()
        self.ledger.claim_application_route(
            ats,
            actor="resident_worker",
            fence=1,
            message_path="/private/message.txt",
            message_sha256=message_sha,
            resume_path="/private/resume.pdf",
            resume_sha256=resume_sha,
        )
        with self.assertRaises(FenceError):
            self.ledger.claim_application_route(
                alternate_ats,
                actor="resident_worker",
                fence=2,
                message_path="/private/message.txt",
                message_sha256=message_sha,
                resume_path="/private/resume.pdf",
                resume_sha256=resume_sha,
            )
        self.ledger.claim_application_route(
            email,
            actor="resident_worker",
            fence=2,
            message_path="/private/message.txt",
            message_sha256=message_sha,
            resume_path="/private/resume.pdf",
            resume_sha256=resume_sha,
        )
        with self.assertRaises(FenceError):
            self.ledger.claim_application_route(
                second_email,
                actor="resident_worker",
                fence=3,
                message_path="/private/message.txt",
                message_sha256=message_sha,
                resume_path="/private/resume.pdf",
                resume_sha256=resume_sha,
            )
        self.ledger.complete_application_route(
            ats,
            fence=1,
            state="failed",
            provider_id="ashby:block",
            evidence_sha256=hashlib.sha256(b"ats failed").hexdigest(),
        )
        self.ledger.complete_application_route(
            email,
            fence=2,
            state="delivery_unknown",
            provider_id="gmail:request-started",
            evidence_sha256=hashlib.sha256(b"unknown").hexdigest(),
        )

        with self.assertRaises(FenceError):
            self.ledger.claim_application_route(
                ats,
                actor="resident_worker",
                fence=3,
                message_path="/private/message.txt",
                message_sha256=message_sha,
                resume_path="/private/resume.pdf",
                resume_sha256=resume_sha,
            )
        route = self.ledger.application_routes(self.application_id)[2]
        self.assertEqual(route["delivery_state"], "delivery_unknown")
        self.assertEqual(route["provider_id"], "gmail:request-started")
        self.assertEqual(route["message_sha256"], message_sha)
        self.assertEqual(route["resume_sha256"], resume_sha)

    def test_reply_evidence_is_append_only_and_rebuildable(self):
        route = self._route(
            "recruiting_email",
            "jobs@example.test",
            3,
            acceptance="accepts_applications",
        )
        message_sha = hashlib.sha256(b"message").hexdigest()
        resume_sha = hashlib.sha256(b"resume").hexdigest()
        self.ledger.claim_application_route(
            route,
            actor="resident_worker",
            fence=1,
            message_path="/private/message.txt",
            message_sha256=message_sha,
            resume_path="/private/resume.pdf",
            resume_sha256=resume_sha,
        )
        self.ledger.complete_application_route(
            route,
            fence=1,
            state="delivered",
            provider_id="gmail:message-42",
            evidence_sha256=hashlib.sha256(b"sent").hexdigest(),
        )
        reply_sha = hashlib.sha256(b"reply").hexdigest()
        self.ledger.record_application_route_reply(
            route,
            provider_id="gmail:reply-99",
            evidence_sha256=reply_sha,
        )

        rebuilt = self.ledger.application_routes(self.application_id)[0]
        self.assertEqual(rebuilt["delivery_state"], "replied")
        self.assertEqual(rebuilt["reply_provider_id"], "gmail:reply-99")
        self.assertEqual(rebuilt["reply_evidence_sha256"], reply_sha)
        events = self.ledger.application_route_events(route)
        self.assertEqual([event["to_state"] for event in events], ["eligible", "action_started", "delivered", "replied"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.ledger.connection.execute(
                "UPDATE application_route_events SET to_state = 'failed' WHERE route_id = ?",
                (route,),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.ledger.connection.execute(
                "DELETE FROM application_route_events WHERE route_id = ?", (route,)
            )


if __name__ == "__main__":
    unittest.main()
