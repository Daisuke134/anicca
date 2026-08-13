import hashlib
import inspect
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


def browser_result(
    *,
    submitted=None,
    submit_unknown=None,
    remaining_unverified_count=0,
    status="pending_verification",
):
    return {
        "status": status,
        "discovered_link_count": 2,
        "verified_link_count": 2,
        "remaining_unverified_count": remaining_unverified_count,
        "submitted": submitted or [],
        "submit_unknown": submit_unknown or [],
        "blocked": [],
    }


class DailyReportingTests(unittest.TestCase):
    def test_delivery_accepts_release_and_browser_material_evidence(self):
        self.assertIn(
            "release_manifest_path",
            inspect.signature(deliver_pipeline_report).parameters,
        )
        self.assertIn(
            "browser_result_path",
            inspect.signature(deliver_pipeline_report).parameters,
        )

    def test_material_change_produces_new_digest_while_exact_replay_dedupes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_path = root / "summary.v2.json"
            release_path = root / "RELEASE.json"
            browser_path = root / "browser-worker-result.json"
            summary_path.write_text(json.dumps(summary()), encoding="utf-8")
            release_path.write_text(json.dumps({"commit": "commit-a"}), encoding="utf-8")
            browser_path.write_text(
                json.dumps(
                    {
                        "status": "pending_verification",
                        "discovered_link_count": 50,
                        "verified_link_count": 40,
                        "remaining_unverified_count": 10,
                        "submitted": [],
                        "submit_unknown": [],
                        "blocked": ["legal_answer_missing"],
                        "report_message_id": "old-message-id-must-not-affect-material",
                    }
                ),
                encoding="utf-8",
            )
            calls = []

            def deliver():
                return deliver_pipeline_report(
                    summary_path=summary_path,
                    outbox_path=root / "outbox.sqlite3",
                    release_manifest_path=release_path,
                    browser_result_path=browser_path,
                    sender=lambda **kwargs: calls.append(kwargs)
                    or {"status": "sent", "message_id": str(len(calls))},
                )

            deliver()
            deliver()
            self.assertIn("material_digest", calls[0])
            self.assertEqual(calls[0]["material_digest"], calls[1]["material_digest"])
            self.assertEqual(len(calls[0]["material_digest"]), 64)
            self.assertNotIn(calls[0]["material_digest"], calls[0]["message"])

            release_path.write_text(json.dumps({"commit": "commit-b"}), encoding="utf-8")
            deliver()
            self.assertNotEqual(calls[1]["material_digest"], calls[2]["material_digest"])
            self.assertNotIn("old-message-id", calls[0]["material_digest"])

    def test_render_uses_explicit_summary_numerators_and_denominators(self):
        message = render_pipeline(summary())
        for phrase in (
            "応募確認: 0/6 (0.0%)",
            "採用担当返信: 0/0 (母数なし)",
            "面接: 0/0 (母数なし)",
            "オファー: 0/0 (母数なし)",
        ):
            self.assertIn(phrase, message)

    def test_render_rejects_invalid_browser_shape_and_counts(self):
        invalid = browser_result()
        invalid["submitted"] = {}
        cases = [invalid]
        for key in ("discovered_link_count", "verified_link_count", "remaining_unverified_count"):
            invalid = browser_result()
            invalid[key] = True
            cases.append(invalid)
            invalid = browser_result()
            invalid[key] = -1
            cases.append(invalid)
        for browser in cases:
            with self.subTest(browser=browser):
                with self.assertRaises(ValueError):
                    render_pipeline(summary(), browser)

    def test_render_describes_five_browser_wake_outcomes_without_internal_terms(self):
        cases = (
            (
                browser_result(submitted=[{"id": "one"}]),
                ("正式な応募完了を確認できた求人は1件", "先にお送りした応募ごとの報告"),
            ),
            (
                browser_result(submit_unknown=[{"id": "one"}]),
                ("応募済みには数えず", "メールと応募履歴"),
            ),
            (
                browser_result(remaining_unverified_count=3),
                ("3件の候補", "役割や条件の確認", "次回の自動確認"),
            ),
            (
                {
                    **browser_result(remaining_unverified_count=3),
                    "blocked": [
                        "Salesforce Technical Architect - MuleSoft "
                        f"({'a' * 64}): internal browser detail"
                    ],
                },
                (
                    "応募を完了できなかった求人は1件",
                    "Salesforce Technical Architect - MuleSoft",
                    "正式な完了確認",
                    "応募済みには数えていません",
                    "このほか3件",
                ),
            ),
            (
                browser_result(),
                ("新たに応募対象として確認できる求人はありませんでした", "次回の自動検索"),
            ),
            (
                None,
                ("新しい応募処理は必要ありませんでした", "次回の確認"),
            ),
        )
        for browser, expected in cases:
            with self.subTest(browser=browser):
                message = render_pipeline(summary(), browser)
                for phrase in expected:
                    self.assertIn(phrase, message)
                for banned in (
                    "Agent", "Dais", "ATS", "provider", "adapters", "submit_unknown",
                    "blocked", "status", "commit", "hash", "digest", "SHA", "GPT", "model",
                ):
                    self.assertNotIn(banned, message)

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
