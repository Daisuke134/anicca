import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


class RecordingSpan:
    recording = True
    def __init__(self, name): self.name, self.attributes = name, {}
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def set_attributes(self, attributes): self.attributes.update(attributes)


class RecordingTelemetry:
    def __init__(self): self.spans = []
    def span(self, name, attributes=None):
        span = RecordingSpan(name); span.attributes.update(attributes or {}); self.spans.append(span)
        return span


class TraceBackend:
    def __init__(self, telemetry): self.telemetry, self.connected = telemetry, False
    def connect(self): self.connected = True
    def close(self): self.connected = False
    def navigate(self, _url): pass
    def snapshot(self): return snapshot(*FORM, url="https://jobs.ashbyhq.com/acme/role/application")
    def screenshot(self): return b"png"


class BrowserUseATSRunnerTests(unittest.TestCase):
    def test_candidate_route_surface_and_form_share_one_private_safe_trace(self):
        telemetry = RecordingTelemetry()
        captured = {}
        def backend_factory(_endpoint, *, allowed_domains, telemetry):
            captured["telemetry"] = telemetry
            return TraceBackend(telemetry)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefilter = root / "prefilter.json"; prefilter.write_text("{}")
            profile = root / "profile.json"; profile.write_text('{"candidate": {}}')
            resume = root / "resume.pdf"; resume.write_bytes(b"pdf")
            candidate = {"official_url": "https://jobs.ashbyhq.com/acme/role?secret=x",
                         "provider": "ashby", "role_family": "engineering", "language": "en"}
            with patch("job_search_loop.browser_use_ats.ranked_pre_submit_candidates", return_value=[candidate]), \
                 patch("job_search_loop.browser_use_ats.select_resume", return_value={"resume_path": str(resume), "resume_sha256": "a" * 64}), \
                 patch("job_search_loop.browser_use_ats.build_non_submit_fill_plan", return_value=[]), \
                 patch("job_search_loop.browser_use_ats.execute_non_submit_fill_plan", return_value={"status": "claim_ready", "blockers": []}):
                run_pre_submit(
                    owner_receipt={"endpoint": "http://127.0.0.1:9222", "lease_id": "lease", "fence": 1, "holder_pid": 2},
                    prefilter_result=prefilter, profile_path=profile, materials_root=root,
                    evidence_dir=root / "evidence", backend_factory=backend_factory,
                    telemetry=telemetry,
                )

        self.assertIs(captured["telemetry"], telemetry)
        names = [span.name for span in telemetry.spans]
        for expected in ("candidate", "route", "surface.classify", "form.snapshot", "form.fill"):
            self.assertIn(expected, names)
        self.assertNotIn("secret", json.dumps([span.attributes for span in telemetry.spans]))
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

    def test_waits_for_delayed_controls_and_form_after_one_open(self):
        adapter = SurfaceAdapter([
            snapshot(), snapshot(), snapshot(APPLICATION),
            snapshot(APPLICATION), snapshot(APPLICATION), snapshot(*FORM),
        ])
        waits = []
        with tempfile.TemporaryDirectory() as directory:
            resolved = resolve_application_surface(
                adapter, Path(directory), sleeper=lambda seconds: waits.append(seconds)
            )
        self.assertTrue(resolved["evaluation"]["claim_ready"])
        self.assertEqual(adapter.opens, [(0, 0)])
        self.assertGreaterEqual(len(waits), 3)

    def test_keeps_observing_a_realistically_slow_ashby_render(self):
        adapter = SurfaceAdapter([snapshot()] * 20 + [snapshot(*FORM)])
        waits = []
        with tempfile.TemporaryDirectory() as directory:
            resolved = resolve_application_surface(
                adapter, Path(directory), sleeper=lambda seconds: waits.append(seconds)
            )
        self.assertTrue(resolved["evaluation"]["claim_ready"])
        self.assertEqual(len(waits), 20)

    def test_fails_closed_when_no_application_surface_appears(self):
        adapter = SurfaceAdapter([snapshot({"tag": "a", "text": "Company"})])
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "application surface"):
                resolve_application_surface(adapter, evidence)
            raw = json.loads((evidence / "application-surface-snapshot.json").read_text())
            self.assertEqual(raw["frames"][0]["controls"][0]["text"], "Company")
            self.assertEqual(raw["classification"]["surface"], "none")

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
