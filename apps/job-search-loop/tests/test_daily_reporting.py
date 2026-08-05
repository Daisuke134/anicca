import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.daily_reporting import deliver_pipeline_report, render_pipeline


def summary():
    value = {
        "version": 2,
        "day": "2026-08-05",
        "counts": {"submitted": 3, "submit_unknown": 3},
        "owners": {"agent": 5, "dais_manual": 1},
        "ats_progress": {
            "required_adapters": ["ashby", "workday"],
            "confirmed_adapters": [],
            "complete": False,
            "adapters": {},
        },
        "funnel": {
            "confirmed_application_rate": {"numerator": 0, "denominator": 6, "rate": 0.0},
            "recruiter_reply_rate": {"numerator": 0, "denominator": 0, "rate": None},
            "interview_rate": {"numerator": 0, "denominator": 0, "rate": None},
            "final_round_rate": {"numerator": 0, "denominator": 0, "rate": None},
            "offer_rate": {"numerator": 0, "denominator": 0, "rate": None},
            "acceptance_rate": {"numerator": 0, "denominator": 0, "rate": None},
        },
    }
    value["projection_sha256"] = hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    return value


class DailyReportingTests(unittest.TestCase):
    def test_render_uses_explicit_summary_numerators_and_denominators(self):
        message = render_pipeline(summary())
        for phrase in (
            "応募確認: 0/6 (0.0%)",
            "採用担当返信: 0/0 (母数なし)",
            "面接: 0/0 (母数なし)",
            "オファー: 0/0 (母数なし)",
            "Agent 5 / Dais手動 1",
            "Ashby・Workdayの確認済み応募: 0/2",
        ):
            self.assertIn(phrase, message)

    def test_delivery_rejects_tampered_projection_before_sender(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "summary.v2.json"
            value = summary()
            value["counts"]["submitted"] = 99
            path.write_text(json.dumps(value), encoding="utf-8")
            calls = []
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                deliver_pipeline_report(
                    summary_path=path,
                    outbox_path=root / "outbox.sqlite3",
                    sender=lambda **kwargs: calls.append(kwargs),
                )
            self.assertEqual(calls, [])

    def test_delivery_passes_day_and_deterministic_message_to_outbox_sender(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "summary.v2.json"
            path.write_text(json.dumps(summary()), encoding="utf-8")
            calls = []
            receipt = deliver_pipeline_report(
                summary_path=path,
                outbox_path=root / "outbox.sqlite3",
                sender=lambda **kwargs: calls.append(kwargs) or {
                    "status": "sent", "message_id": "700", "event_key": "daily"
                },
            )
            self.assertEqual(receipt["message_id"], "700")
            self.assertEqual(calls[0]["japan_day"], "2026-08-05")
            self.assertEqual(calls[0]["message"], render_pipeline(summary()))


if __name__ == "__main__":
    unittest.main()
