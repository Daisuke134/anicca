#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "lm-self-improve" / "daily.py"
SPEC = importlib.util.spec_from_file_location("lm_marketing_self_improve", MODULE_PATH)
self_improve = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(self_improve)


def distribution_pair(creative_id="A03"):
    common = {
        "status": "published",
        "creative_id": creative_id,
        "video_sha256": "vhash",
        "caption_sha256": "chash",
    }
    return [
        {
            **common,
            "platform": "instagram",
            "public_url": "https://www.instagram.com/reel/IGREAL/",
        },
        {
            **common,
            "platform": "tiktok",
            "public_url": "https://www.tiktok.com/@life/video/123",
        },
    ]


class SelfImproveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "self-improve.jsonl"
        self.bank = self.root / "bank.jsonl"
        self.bank.write_text(
            "\n".join(
                json.dumps(
                    {
                        "id": creative_id,
                        "pain": f"pain-{creative_id}",
                        "moment": f"moment-{creative_id}",
                        "punchline": f"punchline-{creative_id}",
                        "material_hint": "hint",
                    }
                )
                for creative_id in ("A03", "A04", "A05", "A06", "B01", "B02", "B03", "B04")
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_day_one_records_both_urls_metrics_and_next_change_reason(self):
        metrics = {
            "instagram": {"views": 12, "likes": 2, "comments": 0},
            "tiktok": {"views": 20, "likes": 3, "comments": 1},
        }
        row = self_improve.record_day(
            date="2026-07-24",
            distribution_rows=distribution_pair(),
            metrics=metrics,
            bank_path=self.bank,
            ledger_path=self.ledger,
        )
        self.assertEqual(row["status"], "started")
        self.assertEqual(row["day_index"], 1)
        self.assertEqual(row["creative_id"], "A03")
        self.assertEqual({item["platform"] for item in row["platforms"]}, {"instagram", "tiktok"})
        self.assertTrue(all(item["url"].startswith("https://") for item in row["platforms"]))
        self.assertIn("A04", row["next_change_reason"])
        self.assertEqual(row["unavailable_metrics"], ["clicks", "completion_rate", "signups", "watch_time"])

    def test_same_day_is_idempotent(self):
        kwargs = dict(
            date="2026-07-24",
            distribution_rows=distribution_pair(),
            metrics={
                "instagram": {"views": 1, "likes": 0, "comments": 0},
                "tiktok": {"views": 2, "likes": 0, "comments": 0},
            },
            bank_path=self.bank,
            ledger_path=self.ledger,
        )
        first = self_improve.record_day(**kwargs)
        second = self_improve.record_day(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(len(self.ledger.read_text().splitlines()), 1)

    def test_requires_exact_ig_tt_hash_pair_and_numeric_views(self):
        broken = distribution_pair()
        broken[1]["video_sha256"] = "other"
        with self.assertRaises(self_improve.SelfImproveError):
            self_improve.record_day(
                date="2026-07-24",
                distribution_rows=broken,
                metrics={
                    "instagram": {"views": 1, "likes": 0, "comments": 0},
                    "tiktok": {"views": 2, "likes": 0, "comments": 0},
                },
                bank_path=self.bank,
                ledger_path=self.ledger,
            )
        with self.assertRaises(self_improve.SelfImproveError):
            self_improve.record_day(
                date="2026-07-24",
                distribution_rows=distribution_pair(),
                metrics={
                    "instagram": {"views": None, "likes": None, "comments": None},
                    "tiktok": {"views": 2, "likes": 0, "comments": 0},
                },
                bank_path=self.bank,
                ledger_path=self.ledger,
            )

    def test_seventh_consecutive_real_day_auto_completes(self):
        dates = [f"2026-07-{day:02d}" for day in range(18, 25)]
        final = None
        for index, date in enumerate(dates):
            final = self_improve.record_day(
                date=date,
                distribution_rows=distribution_pair(creative_id=("A03", "A04", "A05", "A06", "B01", "B02", "B03")[index]),
                metrics={
                    "instagram": {"views": index + 1, "likes": 0, "comments": 0},
                    "tiktok": {"views": index + 2, "likes": 0, "comments": 0},
                },
                bank_path=self.bank,
                ledger_path=self.ledger,
            )
        self.assertEqual(final["day_index"], 7)
        self.assertEqual(final["status"], "done")
        self.assertEqual(final["streak_dates"], dates)

    def test_gap_resets_streak_and_never_backfills(self):
        for date in ("2026-07-20", "2026-07-22"):
            row = self_improve.record_day(
                date=date,
                distribution_rows=distribution_pair(),
                metrics={
                    "instagram": {"views": 1, "likes": 0, "comments": 0},
                    "tiktok": {"views": 1, "likes": 0, "comments": 0},
                },
                bank_path=self.bank,
                ledger_path=self.ledger,
            )
        self.assertEqual(row["day_index"], 1)
        self.assertEqual(row["streak_dates"], ["2026-07-22"])


if __name__ == "__main__":
    unittest.main()
