import hashlib
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger
from job_search_loop.route_executor import execute_next_message_route


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
