import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = REPO_ROOT / "skills/earn/lancers/scripts/telegram_report.py"


def _load_report():
    spec = importlib.util.spec_from_file_location("test_lancers_telegram_report", REPORT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical_report_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _snapshot(report, application, *, pending=0, verified=14, storefront=None, blocker=None):
    return report.build_snapshot(
        application=application,
        pending_count=pending,
        cumulative_verified=verified,
        storefront=storefront or {"published": 4, "paused": 0, "hidden": 0, "draft": 0},
        source_observed_at="2026-08-13T09:00:00Z",
        official_readback_observed_at="2026-08-13T08:59:00Z",
        provider_event_time=None,
        blocker=blocker,
    )


class TelegramReportTests(unittest.TestCase):
    def test_acquisition_stages_pending_verified_and_blocker_are_separate(self):
        report = _load_report()
        message = report.render_snapshot(_snapshot(report, {
            "observed_count": 13, "eligible_count": 1, "submitted": False,
            "verified_count": 0, "error": "submission_uncertain",
        }, pending=1, blocker="submission_uncertain"))
        for value in ("observed 13", "qualified 1", "submitted 0", "newly verified 0", "pending 1", "cumulative verified 14", "submission_uncertain"):
            self.assertIn(value, message)

    def test_no_eligible_does_not_turn_receipts_into_revenue(self):
        report = _load_report()
        message = report.render_snapshot(_snapshot(report, {
            "observed_count": 13, "eligible_count": 0, "submitted": False,
            "verified_count": 0, "reason": "no_eligible_project",
        }))
        self.assertIn("blocker none", message)
        self.assertIn("売上: unknown", message)
        self.assertNotIn("売上: 14", message)

    def test_storefront_states_are_separate_and_mismatch_is_warning(self):
        report = _load_report()
        message = report.render_snapshot(_snapshot(report, {"observed_count": 1}, storefront={
            "published": 6, "paused": 0, "hidden": 0, "draft": 0,
            "error": "listing_readback_mismatch",
        }))
        self.assertIn("⚠️", message)
        for label in ("受付中", "受付休止中", "非表示", "下書き"):
            self.assertIn(label, message)
        self.assertNotIn("未処理", message)
        self.assertNotIn("✅", message)

    def test_timestamps_and_actual_cost_are_explicitly_unknown_or_labeled(self):
        report = _load_report()
        message = report.render_snapshot(_snapshot(report, {"observed_count": 1}))
        self.assertIn("source_observed_at", message)
        self.assertIn("official_readback_observed_at", message)
        self.assertIn("provider event time: unknown", message)
        self.assertIn("AI処理費: unknown (meter未接続)", message)
        self.assertNotIn("qualification cost", message)
        self.assertNotIn("file mtime", message)

    def test_semantic_dedupe_is_daily_and_state_change_sensitive(self):
        report = _load_report()
        first = _snapshot(report, {"observed_count": 13}, pending=0)
        changed = _snapshot(report, {"observed_count": 13}, pending=1, blocker="submission_uncertain")
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "telegram.sqlite3"
            day = datetime.fromisoformat("2026-08-13T09:00:00+09:00")
            self.assertTrue(report.enqueue_snapshot(database, first, day))
            self.assertFalse(report.enqueue_snapshot(database, first, day.replace(hour=10)))
            self.assertTrue(report.enqueue_snapshot(database, changed, day.replace(hour=11)))
            self.assertTrue(report.enqueue_snapshot(database, first, day.replace(day=14)))

    def test_delivery_requires_provider_id_and_quarantines_uncertain_send(self):
        report = _load_report()
        snapshot = _snapshot(report, {"observed_count": 1})
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "telegram.sqlite3"
            self.assertTrue(report.enqueue_snapshot(database, snapshot, "2026-08-13T00:00:00Z"))
            result = report.deliver_pending(database, lambda _message: report.SendResult(True, "77"), "2026-08-13T00:00:01Z")
            self.assertEqual(result.delivered, 1)
            self.assertTrue(report.enqueue_snapshot(database, _snapshot(report, {"observed_count": 2}), "2026-08-13T00:00:02Z"))
            uncertain = report.deliver_pending(database, lambda _message: report.SendResult(True, None), "2026-08-13T00:00:03Z")
            self.assertEqual(uncertain.delivery_uncertain, 1)
            self.assertEqual(report.deliver_pending(database, lambda _message: report.SendResult(True, "88"), "2026-08-13T00:00:04Z").attempted, 0)

    def test_official_reader_parses_only_four_myplan_anchors_under_injected_lock(self):
        report = _load_report()

        class Anchor:
            def __init__(self, text, href): self.text, self.href = text, href
            def is_visible(self): return True
            def inner_text(self): return self.text
            def get_attribute(self, name): return self.href if name == "href" else None

        class Anchors:
            def __init__(self, values): self.values = values
            def count(self): return len(self.values)
            def nth(self, index): return self.values[index]

        class Page:
            url = "https://www.lancers.jp/myplan"
            def goto(self, *_args, **_kwargs): pass
            def locator(self, selector):
                self.assert_selector = selector
                return Anchors([Anchor(f"{label} ({count}件)", href) for label, count, href in (("受付中", 6, "/myplan"), ("受付休止中", 0, "/myplan/paused"), ("非表示", 0, "/myplan/archived"), ("下書き", 0, "/myplan/draft"))])

        class Browser:
            def __init__(self): self.contexts = [self]
            def new_page(self): return Page()

        class Lock:
            def __enter__(self): self.entered = True
            def __exit__(self, *_args): self.exited = True

        lock = Lock()
        self.assertEqual(report.read_storefront(Path("/tmp/application.json"), browser_factory=lambda _url: Browser(), lock=lambda _path: lock), {"published": 6, "paused": 0, "hidden": 0, "draft": 0})
        self.assertTrue(lock.entered)

    def test_malformed_sources_are_unknown_warning_not_fabricated_zero(self):
        report = _load_report()
        message = report.render_snapshot(report.build_snapshot(
            application=None, pending_count=None, cumulative_verified=None,
            storefront=None, source_observed_at=None,
            official_readback_observed_at=None, provider_event_time=None,
        ))
        self.assertIn("⚠️", message)
        self.assertIn("unknown", message)
        self.assertNotIn("✅", message)
        self.assertNotIn("0件", message)


if __name__ == "__main__":
    unittest.main()
