import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.browser_use_adapter import BrowserUsePolicyError
from job_search_loop.browser_use_ats import resolve_application_surface, run_pre_submit


def snapshot(*controls, committed=True, url="https://jobs.ashbyhq.com/acme/role"):
    return {"version": 1, "url": url, "navigation_committed": committed,
            "frames": [{"url": url, "controls": list(controls)}]}


FORM = ({"tag": "input", "type": "email"}, {"tag": "input", "type": "file"},
        {"tag": "button", "type": "submit", "text": "Submit Application"})
APPLICATION = {"tag": "a", "role": "tab", "text": "Application"}


class SurfaceAdapter:
    def __init__(self, snapshots, *, stale_once=False):
        self.snapshots, self.opens, self.stale_once = iter(snapshots), [], stale_once
    def snapshot(self): return next(self.snapshots)

    def open_application(self, frame_index, control_index):
        self.opens.append((frame_index, control_index))
        if self.stale_once:
            self.stale_once = False
            raise BrowserUsePolicyError("Browser Use control index is stale")


class BrowserUseATSRunnerTests(unittest.TestCase):
    def test_resolves_blank_delayed_overview_and_direct_form_states(self):
        cases = (
            ([snapshot(committed=False), snapshot(*FORM)], 0),
            ([snapshot(), snapshot(*FORM)], 0),
            ([snapshot({"tag": "a", "text": "Apply for this Job"}), snapshot(*FORM)], 1),
            ([snapshot(*FORM, url="https://jobs.ashbyhq.com/acme/role/application")], 0),
        )
        for snapshots, expected_opens in cases:
            with self.subTest(expected_opens=expected_opens), tempfile.TemporaryDirectory() as directory:
                adapter = SurfaceAdapter(snapshots)
                resolved = resolve_application_surface(adapter, Path(directory))
                self.assertEqual(resolved["evaluation"]["surface"], "ashby_application")
                self.assertEqual(len(adapter.opens), expected_opens)
                persisted = json.loads((Path(directory) / "application-surface.json").read_text())
                self.assertEqual(persisted["after"]["surface"], "ashby_application")

    def test_refreshes_once_when_application_control_index_is_stale(self):
        adapter = SurfaceAdapter(
            [snapshot(APPLICATION), snapshot(APPLICATION), snapshot(*FORM)], stale_once=True
        )
        with tempfile.TemporaryDirectory() as directory:
            resolved = resolve_application_surface(adapter, Path(directory))
        self.assertTrue(resolved["evaluation"]["claim_ready"])
        self.assertEqual(adapter.opens, [(0, 0), (0, 0)])

    def test_fails_closed_when_no_application_surface_appears(self):
        adapter = SurfaceAdapter([snapshot({"tag": "a", "text": "Company"})])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "application surface"):
                resolve_application_surface(adapter, Path(directory))

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
