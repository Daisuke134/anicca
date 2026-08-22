import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_provider import MercorListing
from job_search_loop.mercor_submit_guard import (
    MercorSubmitGuardError,
    claim_ready_submission,
    classify_submit_readback,
)


class MercorSubmitGuardTests(unittest.TestCase):
    def _listing(self) -> MercorListing:
        return MercorListing(
            listing_id="list-new",
            title="Software / AI / IT / data Evaluator",
            url="https://work.mercor.com/explore?listingId=list-new",
            application_state="ready_to_submit",
            steps_completed=3,
            submit_visible=True,
            domain_expert_reused=True,
        )

    def test_claim_requires_ready_state_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "pre.json"
            evidence.write_text('{"observed":true}\n', encoding="utf-8")
            claim = claim_ready_submission(
                self._listing(), submitted_listing_ids=set(), pre_submit_evidence=evidence
            )
            self.assertIsNotNone(claim)
            self.assertEqual(len(claim.claim_token), 64)

    def test_duplicate_is_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "pre.json"
            evidence.write_text('{"observed":true}\n', encoding="utf-8")
            self.assertIsNone(
                claim_ready_submission(
                    self._listing(), submitted_listing_ids={"list-new"}, pre_submit_evidence=evidence
                )
            )

    def test_missing_evidence_fails_closed(self):
        with self.assertRaises(MercorSubmitGuardError):
            claim_ready_submission(
                self._listing(),
                submitted_listing_ids=set(),
                pre_submit_evidence=Path("/tmp/no-such-mercor-evidence.json"),
            )

    def test_readback_is_authoritative_or_unknown(self):
        self.assertEqual(
            classify_submit_readback(
                page_url="https://work.mercor.com/jobs/apply/candidate-x",
                visible_text="Your application has been submitted!",
            ),
            "submitted_pending_review",
        )
        self.assertEqual(
            classify_submit_readback(
                page_url="https://work.mercor.com/jobs/apply/candidate-x",
                visible_text="Loading...",
            ),
            "submit_unknown",
        )


if __name__ == "__main__":
    unittest.main()
