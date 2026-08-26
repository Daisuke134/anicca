import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_provider import (
    MercorListing,
    MercorProviderError,
    build_pass_prompt,
    choose_ready_listing,
    listing_id_from_url,
    ready_for_submit,
)


class MercorProviderTests(unittest.TestCase):
    def _ready(self, listing_id: str = "list-ready") -> MercorListing:
        return MercorListing(
            listing_id=listing_id,
            title="Software Evaluator",
            url=f"https://work.mercor.com/explore?listingId={listing_id}",
            application_state="ready_to_submit",
            steps_completed=3,
            submit_visible=True,
            domain_expert_reused=True,
        )

    def test_listing_id_supports_explore_and_job_urls(self):
        self.assertEqual(
            listing_id_from_url(
                "https://work.mercor.com/explore?listingId=list_abc&returnPath=/explore"
            ),
            "list_abc",
        )
        self.assertEqual(
            listing_id_from_url("https://work.mercor.com/jobs/list_xyz/title"),
            "list_xyz",
        )

    def test_missing_listing_id_fails_closed(self):
        with self.assertRaises(MercorProviderError):
            listing_id_from_url("https://work.mercor.com/explore")

    def test_ready_gate_requires_every_live_condition(self):
        self.assertTrue(ready_for_submit(self._ready()))
        self.assertFalse(
            ready_for_submit(
                MercorListing(
                    listing_id="list-no",
                    title="No",
                    url="https://work.mercor.com/jobs/list-no/no",
                    application_state="ready_to_submit",
                    steps_completed=2,
                    submit_visible=True,
                    domain_expert_reused=True,
                )
            )
        )

    def test_choose_ready_skips_private_ledger_ids(self):
        first = self._ready("list-already")
        second = self._ready("list-new")
        self.assertEqual(
            choose_ready_listing([first, second], {"list-already"}).listing_id,
            "list-new",
        )
        self.assertIsNone(choose_ready_listing([first], {"list-already"}))

    def test_prompt_binds_bounded_json_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / "prompt.md"
            prompt.write_text("model-led prompt", encoding="utf-8")
            result = build_pass_prompt(
                prompt_path=prompt,
                context={"operator": "synthetic", "submitted_ids": ["list-1"]},
            )
            self.assertIn("model-led prompt", result)
            self.assertIn('"submitted_ids": ["list-1"]', result)


if __name__ == "__main__":
    unittest.main()
