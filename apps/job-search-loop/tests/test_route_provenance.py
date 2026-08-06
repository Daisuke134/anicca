import hashlib
import unittest

from job_search_loop.route_provenance import (
    ProvenanceError,
    verify_official_url_route,
    verify_recipient_route,
)


class RouteProvenanceTests(unittest.TestCase):
    def _verify(self, text, *, source_url="https://careers.example.com/contact"):
        return verify_recipient_route(
            source_url=source_url,
            source_text=text,
            source_sha256=hashlib.sha256(text.encode()).hexdigest(),
            recipient="jobs@example.com",
            employer_domains=["example.com"],
            official_provider_domains=["jobs.ashbyhq.com"],
        )

    def test_explicit_apply_by_email_language_is_application_acceptance(self):
        result = self._verify(
            "To apply, email your resume to jobs@example.com. We review every application."
        )

        self.assertEqual(result["route_kind"], "recruiting_email")
        self.assertEqual(result["recipient_acceptance"], "accepts_applications")
        self.assertIn("jobs@example.com", result["source_span"])

    def test_public_recruiting_address_without_apply_instruction_is_outreach_only(self):
        result = self._verify(
            "Questions about careers can be sent to jobs@example.com."
        )

        self.assertEqual(result["route_kind"], "recruiting_outreach")
        self.assertEqual(result["recipient_acceptance"], "outreach_only")

    def test_third_party_source_or_address_missing_from_source_is_rejected(self):
        with self.assertRaises(ProvenanceError):
            self._verify(
                "To apply, email your resume to jobs@example.com.",
                source_url="https://directory.example.net/example-company",
            )
        with self.assertRaises(ProvenanceError):
            self._verify("Apply by email using the address in this directory.")

    def test_source_hash_and_exact_domain_boundaries_are_required(self):
        text = "To apply, email your resume to jobs@example.com."
        with self.assertRaises(ProvenanceError):
            verify_recipient_route(
                source_url="https://careers.example.com.evil.test/contact",
                source_text=text,
                source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                recipient="jobs@example.com",
                employer_domains=["example.com"],
                official_provider_domains=[],
            )

    def test_alternate_url_must_be_exactly_linked_from_an_authorized_source(self):
        target = "https://jobs.ashbyhq.com/example/role-42"
        text = f'<a href="{target}">Apply</a>'
        result = verify_official_url_route(
            source_url="https://careers.example.com/jobs",
            source_text=text,
            source_sha256=hashlib.sha256(text.encode()).hexdigest(),
            target_url=target,
            employer_domains=["example.com"],
            official_provider_domains=["jobs.ashbyhq.com"],
        )
        self.assertEqual(result["route_kind"], "alternate_official")
        self.assertEqual(result["endpoint"], target)

        with self.assertRaises(ProvenanceError):
            verify_official_url_route(
                source_url="https://careers.example.com/jobs",
                source_text=text,
                source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                target_url="https://jobs.ashbyhq.com.evil.test/example/role-42",
                employer_domains=["example.com"],
                official_provider_domains=["jobs.ashbyhq.com"],
            )
        with self.assertRaises(ProvenanceError):
            verify_recipient_route(
                source_url="https://careers.example.com/contact",
                source_text=text,
                source_sha256="0" * 64,
                recipient="jobs@example.com",
                employer_domains=["example.com"],
                official_provider_domains=[],
            )


if __name__ == "__main__":
    unittest.main()
