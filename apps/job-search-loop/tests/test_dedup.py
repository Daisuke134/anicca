import unittest


class DedupParityTests(unittest.TestCase):
    def test_url_dedup_strips_tracking_but_preserves_identity_parameters(self):
        from job_search_loop.state import canonical_url

        base = "https://jobs.example/roles/7"
        self.assertEqual(
            canonical_url(base + "?utm_source=x&rltr=volatile"),
            base,
        )
        self.assertNotEqual(
            canonical_url(base + "?gh_jid=1"),
            canonical_url(base + "?gh_jid=2"),
        )

    def test_company_role_key_folds_location_suffix_but_not_specialty(self):
        from job_search_loop.dedup import company_role_key

        self.assertEqual(
            company_role_key("Acme, Inc.", "AI Deployment Engineer (Tokyo)"),
            company_role_key("Acme Inc", "AI Deployment Engineer [Remote]"),
        )
        self.assertNotEqual(
            company_role_key("Acme Inc", "AI Deployment Engineer, Cyber"),
            company_role_key("Acme Inc", "AI Deployment Engineer, Startups"),
        )

    def test_simhash_requires_substantial_text_and_matches_near_verbatim_jds(self):
        from job_search_loop.dedup import fingerprint_text, fingerprint_similarity

        body = " ".join(
            ["Build production AI systems with customers and deploy reliable models"]
            * 12
        )
        near = body + " in Tokyo"
        unrelated = " ".join(
            ["Manage enterprise finance operations procurement audit and reporting"]
            * 12
        )
        self.assertEqual(fingerprint_text("short description"), "")
        self.assertRegex(fingerprint_text(body), r"^[0-9a-f]{16}$")
        self.assertGreaterEqual(
            fingerprint_similarity(fingerprint_text(body), fingerprint_text(near)),
            0.92,
        )
        self.assertLess(
            fingerprint_similarity(fingerprint_text(body), fingerprint_text(unrelated)),
            0.92,
        )


if __name__ == "__main__":
    unittest.main()
