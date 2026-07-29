"""One natural day, one listing count -- across all three reporting systems.

Why this file exists: on 2026-07-27 the same JST day had three different answers for
"how many listings do we have" -- 日報=7, funnel=4, 台帳=11 -- because each system
invented its own projection over ~/gig/shuppin.jsonl:

  日報   counted publish *rows* (no dedup): one listing republished 4x looked like 4
  funnel counted distinct published service_id: 4
  台帳   counted every service_id token ever seen, placeholders included: 11

strategy.json keep/revert and the X8 bandit learn from these numbers, so three answers
means learning from a number that does not exist. This locks all three onto
listing_ledger.py's taxonomy and asserts they agree on the same fixture, and pins the
three boundaries that produced the disagreement (day edge, duplicate, unpublished).
"""

import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RUNNER_CONFIG = Path(__file__).resolve().parents[2] / "agent-runner" / "config.json"

JST = timezone(timedelta(hours=9))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def jsonl(path: Path, rows) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class ListingLedgerTaxonomyTest(unittest.TestCase):
    """The taxonomy itself: what counts as a listing, and when."""

    def setUp(self):
        self.ledger = load(SCRIPTS / "listing_ledger.py", "listing_ledger")
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "shuppin.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def test_duplicate_publish_rows_collapse_to_one_listing(self):
        """The exact 7-vs-4 gap: service 4312985 republished four times is ONE listing."""
        jsonl(self.path, [
            {"action": "shuppin_published", "service_id": "4312985", "ts": 1784372127.07},
            {"action": "shuppin_published", "service_id": "4312985", "ts": 1784452885.56},
            {"action": "shuppin_published", "service_id": "4312985", "ts": 1784541332},
            {"action": "shuppin_published", "service_id": "4312985", "ts": 1784685537},
        ])
        counts = self.ledger.count_ledger(self.path)
        self.assertEqual(counts.published_listings, 1)
        self.assertEqual(counts.published_events, 4)

    def test_unpublished_states_never_count_as_published(self):
        """Draft-created and blocked attempts are known but not live."""
        jsonl(self.path, [
            {"action": "shuppin_created", "service_id": "111", "ts": 1784372127},
            {"action": "shuppin_blocked", "service_id": "222", "ts": 1784372128},
            {"action": "shuppin_edited", "service_id": "333", "ts": 1784372129},
            {"action": "shuppin_published", "service_id": "444", "ts": 1784372130},
        ])
        counts = self.ledger.count_ledger(self.path)
        self.assertEqual(counts.published_listings, 1)
        self.assertEqual(counts.created_listings, 1)
        self.assertEqual(counts.blocked_events, 1)
        self.assertEqual(counts.known_listings, 4)

    def test_jst_natural_day_boundary_not_utc(self):
        """00:30 JST on the 27th belongs to the 27th, though it is 15:30 UTC on the 26th."""
        just_after_midnight_jst = datetime(2026, 7, 27, 0, 30, tzinfo=JST).timestamp()
        just_before_midnight_jst = datetime(2026, 7, 26, 23, 30, tzinfo=JST).timestamp()
        jsonl(self.path, [
            {"action": "shuppin_published", "service_id": "early", "ts": just_after_midnight_jst},
            {"action": "shuppin_published", "service_id": "late", "ts": just_before_midnight_jst},
        ])
        start, end = self.ledger.jst_day_bounds("2026-07-27")
        counts = self.ledger.count_ledger(self.path, since=start, until=end)
        self.assertEqual(counts.published_listings, 1)
        prev_start, prev_end = self.ledger.jst_day_bounds("2026-07-26")
        prev = self.ledger.count_ledger(self.path, since=prev_start, until=prev_end)
        self.assertEqual(prev.published_listings, 1)

    def test_iso8601_string_ts_is_honored_not_dropped(self):
        """26 live rows carry ISO ts; the old isinstance(ts,(int,float)) check ate them."""
        jsonl(self.path, [
            {"action": "shuppin_published", "service_id": "4302213",
             "ts": "2026-07-11T14:57:59.461722+00:00"},
            {"action": "shuppin_published", "service_id": "4244912",
             "ts": "2026-07-11T15:31:52.000000Z"},
        ])
        counts = self.ledger.count_ledger(self.path, since=0)
        self.assertEqual(counts.published_listings, 2)

    def test_placeholder_and_composite_service_ids(self):
        """'N/A' is not a listing; a comma-joined cell is several listings, not one."""
        jsonl(self.path, [
            {"action": "shuppin_edited", "service_id": "N/A", "ts": 1784372127},
            {"action": "shuppin_edited", "service_id": "4302213,4244912,4244556",
             "ts": 1784372128},
        ])
        counts = self.ledger.count_ledger(self.path)
        self.assertEqual(counts.known_listings, 3)

    def test_publish_without_service_id_is_quarantined_not_counted(self):
        """An unidentifiable publish cannot be deduped, so it is surfaced, never summed."""
        jsonl(self.path, [
            {"action": "shuppin_published", "ts": 1784372127},
            {"action": "shuppin_published", "service_id": "4312985", "ts": 1784372128},
        ])
        counts = self.ledger.count_ledger(self.path)
        self.assertEqual(counts.published_listings, 1)
        self.assertEqual(counts.unidentified_publish_events, 1)


class ThreeSystemsAgreeTest(unittest.TestCase):
    """日報 / funnel / 台帳 read the same ledger through the same taxonomy."""

    #  Same fixture for all three systems. Deliberately contains every trap that
    #  produced the original 7/4/11 split.
    DAY = "2026-07-27"

    def setUp(self):
        self.ledger = load(SCRIPTS / "listing_ledger.py", "listing_ledger")
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.gig_dir = self.root / "gig"
        self.gig_dir.mkdir()
        self.connector_db = self.root / "connector.sqlite3"
        self.telegram_db = self.root / "telegram.sqlite3"

        day_noon = datetime(2026, 7, 27, 12, 0, tzinfo=JST).timestamp()
        prev_day = datetime(2026, 7, 26, 23, 30, tzinfo=JST).timestamp()
        jsonl(self.gig_dir / "shuppin.jsonl", [
            # three real listings published today (one of them reported twice)
            {"action": "shuppin_published", "service_id": "5000001", "ts": day_noon},
            {"action": "shuppin_published", "service_id": "5000001", "ts": day_noon + 60},
            {"action": "shuppin_published", "service_id": "5000002",
             "ts": datetime.fromtimestamp(day_noon + 120, timezone.utc).isoformat()},
            {"action": "shuppin_published", "service_id": "5000003", "ts": day_noon + 180},
            # noise that must not inflate the count
            {"action": "shuppin_created", "service_id": "5000009", "ts": day_noon + 200},
            {"action": "shuppin_blocked", "service_id": "5000010", "ts": day_noon + 210},
            {"action": "shuppin_edited", "service_id": "N/A", "ts": day_noon + 220},
            # yesterday, JST
            {"action": "shuppin_published", "service_id": "4999999", "ts": prev_day},
        ])
        (self.gig_dir / "applied.jsonl").write_text("", encoding="utf-8")
        (self.gig_dir / "earnings.jsonl").write_text("", encoding="utf-8")
        with sqlite3.connect(self.connector_db) as connection:
            connection.execute("""CREATE TABLE connector_actions(
                action_id INTEGER,thread_id TEXT,state TEXT,revision INTEGER,
                created_at INTEGER,updated_at INTEGER,seller_sent_at INTEGER
            )""")

    def tearDown(self):
        self.temp.cleanup()

    def test_all_three_systems_report_the_same_listing_count(self):
        expected_today = 3      # 5000001 (deduped), 5000002, 5000003
        expected_all_time = 4   # + 4999999 from the previous JST day

        start, end = self.ledger.jst_day_bounds(self.DAY)
        canonical_today = self.ledger.count_ledger(
            self.gig_dir / "shuppin.jsonl", since=start, until=end
        ).published_listings
        canonical_all_time = self.ledger.count_ledger(
            self.gig_dir / "shuppin.jsonl"
        ).published_listings
        self.assertEqual(canonical_today, expected_today)
        self.assertEqual(canonical_all_time, expected_all_time)

        # 1. funnel
        os.environ["GIG_STATE_DIR"] = str(self.gig_dir)
        funnel = load(ROOT / "gig_funnel.py", "gig_funnel_under_test")
        funnel_row = funnel.build_funnel("pass-test")
        self.assertEqual(funnel_row["listings_live"], canonical_all_time)
        self.assertEqual(funnel_row["listings_published_today"], canonical_today)

        # 2. 台帳 (lane productivity)
        productivity = load(SCRIPTS / "lane_productivity.py", "lane_productivity_under_test")
        self.assertEqual(
            productivity.count_list_published(start, end), canonical_today
        )

        # 3. 日報
        report = load(SCRIPTS / "telegram_report.py", "telegram_report_under_test")
        outbox_module = load(SCRIPTS / "telegram_outbox.py", "telegram_outbox_under_test")
        message = report.daily_message(
            gig_dir=self.gig_dir,
            connector_database=self.connector_db,
            telegram_outbox=outbox_module.TelegramOutbox(self.telegram_db),
            route=report.composition_route(RUNNER_CONFIG),
            now=datetime(2026, 7, 27, 9, 7, tzinfo=JST),
        )
        self.assertIn(
            f"出品公開:{canonical_all_time}(+{canonical_today})", message
        )


if __name__ == "__main__":
    unittest.main()
