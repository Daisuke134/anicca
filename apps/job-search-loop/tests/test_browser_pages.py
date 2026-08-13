import tempfile
import unittest
from pathlib import Path

from job_search_loop.browser_pages import PageOwnership, registered_created_target


class PageOwnershipTests(unittest.TestCase):
    def test_only_created_nonbaseline_page_can_be_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            ownership = PageOwnership(
                baseline={"human-tab", "mail-tab"},
                receipt_path=Path(directory) / "pages.json",
                lease_id="lease-1",
                fence=7,
            )
            ownership.register_created("job-tab")
            self.assertEqual(
                ownership.closable({"human-tab", "mail-tab", "job-tab", "popup"}),
                ["job-tab"],
            )

    def test_baseline_or_unregistered_target_is_never_adopted(self):
        with tempfile.TemporaryDirectory() as directory:
            ownership = PageOwnership(
                baseline={"human-tab"}, receipt_path=Path(directory) / "pages.json",
                lease_id="lease-1", fence=7,
            )
            with self.assertRaisesRegex(ValueError, "baseline"):
                ownership.register_created("human-tab")
            self.assertEqual(ownership.closable({"human-tab", "unknown"}), [])

    def test_receipt_is_private_and_contains_hashes_not_target_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "pages.json"
            ownership = PageOwnership(
                baseline={"private-human-tab"}, receipt_path=receipt,
                lease_id="lease-secret", fence=7,
            )
            ownership.register_created("private-job-tab")
            text = receipt.read_text()
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("private-human-tab", text)
            self.assertNotIn("private-job-tab", text)
            self.assertNotIn("lease-secret", text)

    def test_replay_with_different_fence_cannot_close_prior_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "pages.json"
            first = PageOwnership({"human"}, receipt, "lease-1", 7)
            first.register_created("old-job-tab")
            second = PageOwnership({"human", "old-job-tab"}, receipt, "lease-2", 8)
            self.assertEqual(second.closable({"human", "old-job-tab"}), [])


class PageClosureTests(unittest.IsolatedAsyncioTestCase):
    async def test_cdp_close_commands_contain_only_registered_created_ids(self):
        class Session:
            def __init__(self):
                self.calls = []

            async def send(self, method, params):
                self.calls.append((method, params))
                return {"success": True}

        with tempfile.TemporaryDirectory() as directory:
            ownership = PageOwnership(
                {"human-tab"}, Path(directory) / "pages.json", "lease-1", 7
            )
            ownership.register_created("job-tab")
            session = Session()
            closed = await ownership.close_owned(
                session, {"human-tab", "job-tab", "unregistered-popup"}
            )
            self.assertEqual(closed, ["job-tab"])
            self.assertEqual(
                session.calls,
                [("Target.closeTarget", {"targetId": "job-tab"})],
            )

    def test_driver_cleanup_accepts_only_matching_created_target(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "pages.json"
            ownership = PageOwnership({"human-tab"}, receipt, "lease-1", 7)
            ownership.register_created("job-tab")
            value = __import__("json").loads(receipt.read_text())
            self.assertEqual(registered_created_target(
                {"lease_id": "lease-1", "fence": 7}, value,
                {"target_id": "job-tab", "lease_id": "lease-1", "fence": 7},
            ), "job-tab")
            with self.assertRaises(ValueError):
                registered_created_target(
                    {"lease_id": "lease-1", "fence": 7}, value,
                    {"target_id": "human-tab", "lease_id": "lease-1", "fence": 7},
                )


if __name__ == "__main__":
    unittest.main()
