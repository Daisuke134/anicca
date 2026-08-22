import unittest

from job_search_loop.browser_owner import probe_cdp
from job_search_loop.mercor_provider import (
    MercorListing,
    MercorProviderError,
    classify_sensitive_screen,
    listing_id_from_url,
    ready_for_submit,
)
from job_search_loop.mercor_submit_guard import classify_submit_readback


class MercorFailureFixtureTests(unittest.TestCase):
    def test_page_drift_is_not_ready(self):
        self.assertFalse(
            ready_for_submit(
                MercorListing(
                    listing_id="list-drift",
                    title="Drifted listing",
                    url="https://work.mercor.com/jobs/list-drift/drifted",
                    application_state="page_drift",
                    steps_completed=2,
                    submit_visible=False,
                    domain_expert_reused=False,
                )
            )
        )

    def test_stale_tab_outside_mercor_fails_closed(self):
        with self.assertRaises(MercorProviderError):
            listing_id_from_url("https://example.com/jobs/list-stale")

    def test_transient_cdp_failure_is_unavailable(self):
        result = probe_cdp("http://127.0.0.1:1")
        self.assertEqual(result["status"], "unavailable")

    def test_ambiguous_submit_is_unknown_and_not_retryable(self):
        self.assertEqual(
            classify_submit_readback(
                page_url="https://work.mercor.com/jobs/apply/candidate-x",
                visible_text="Loading…",
            ),
            "submit_unknown",
        )

    def test_recovery_reset_screen_is_blocked(self):
        self.assertEqual(classify_sensitive_screen("Restore account"), "blocked")
        self.assertEqual(classify_sensitive_screen("パスワードをリセット"), "blocked")
        self.assertEqual(classify_sensitive_screen("はい"), "blocked")

    def test_successful_readback_is_authoritative(self):
        self.assertEqual(
            classify_submit_readback(
                page_url="https://work.mercor.com/jobs/apply/candidate-x",
                visible_text="Your application has been submitted!",
            ),
            "submitted_pending_review",
        )


if __name__ == "__main__":
    unittest.main()
