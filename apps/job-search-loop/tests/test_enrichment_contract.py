import unittest

from job_search_loop.enrichment_contract import build_enrichment_receipt


class EnrichmentContractTests(unittest.TestCase):
    def test_receipt_is_bounded_canonical_and_provenance_preserving(self):
        receipt = build_enrichment_receipt(
            candidate_url="https://jobs.example/roles/7?utm_source=search",
            source_url="https://jobs.example/roles/7?ref=detail",
            provider="smart_extract:json_ld",
            extraction={
                "full_description": "x" * 10_000,
                "application_url": "https://jobs.example/roles/7/apply?utm_source=detail",
            },
        )

        self.assertEqual(receipt["candidate_url"], "https://jobs.example/roles/7")
        self.assertEqual(receipt["source_url"], "https://jobs.example/roles/7")
        self.assertEqual(receipt["application_url"], "https://jobs.example/roles/7/apply")
        self.assertEqual(receipt["provider"], "smart_extract:json_ld")
        self.assertEqual(len(receipt["full_description"]), 4_000)
        self.assertRegex(receipt["content_sha256"], r"^[0-9a-f]{64}$")

    def test_model_success_claims_and_unsafe_apply_urls_are_discarded(self):
        receipt = build_enrichment_receipt(
            candidate_url="https://jobs.example/roles/8",
            source_url="https://jobs.example/roles/8",
            provider="smart_extract:api_response",
            extraction={
                "description": "Build useful AI systems.",
                "application_url": "javascript:submit()",
                "status": "applied",
                "applied": True,
                "provider_message_id": "invented",
            },
        )

        self.assertIsNone(receipt["application_url"])
        self.assertNotIn("status", receipt)
        self.assertNotIn("applied", receipt)
        self.assertNotIn("provider_message_id", receipt)
        self.assertEqual(receipt["version"], 1)

    def test_non_http_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "source_url"):
            build_enrichment_receipt(
                candidate_url="https://jobs.example/roles/9",
                source_url="file:///private/profile.json",
                provider="smart_extract:json_ld",
                extraction={"description": "text"},
            )


if __name__ == "__main__":
    unittest.main()
