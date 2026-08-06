import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.browser_use_ats import run_pre_submit


class BrowserUseATSRunnerTests(unittest.TestCase):
    def test_no_candidate_returns_pending_without_constructing_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefilter = root / "prefilter.json"
            prefilter.write_text(json.dumps({"candidates": []}), encoding="utf-8")
            profile = root / "profile.json"
            profile.write_text(json.dumps({"candidate": {}}), encoding="utf-8")

            result = run_pre_submit(
                owner_receipt={"endpoint": "http://127.0.0.1:9222"},
                prefilter_result=prefilter,
                profile_path=profile,
                materials_root=root / "materials",
                evidence_dir=root / "evidence",
                backend_factory=lambda *args, **kwargs: self.fail("browser must not connect"),
            )

            self.assertEqual(result["status"], "pending_verification")
            self.assertEqual(result["blocked"], ["no_ranking_ready_candidate"])
            self.assertEqual(result["executor"], "browser-use-0.13.7")


if __name__ == "__main__":
    unittest.main()
