import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "revenue_cli.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("affiliate_revenue", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RevenueCliTest(unittest.TestCase):
    def test_japanese_overview_values_preserve_unknown_money_states(self):
        cards = {
            "クリック数": "1", "登録数": "0", "有料会員登録": "0",
            "コンバージョン率": "0%", "収益": "$0.00",
            "支払い待ちのコミッション": "$0.00",
            "支払い済みコミッション": "$0.00",
            "クリックあたりの収益": "$0.00",
        }
        metrics = MODULE.parse_cards(cards)
        self.assertEqual(metrics["clicks"], 1)
        self.assertEqual(metrics["pending_minor"], 0)
        self.assertIsNone(metrics["approved_minor"])
        self.assertIsNone(metrics["reversed_minor"])

    def test_later_observation_preserves_baseline_and_reports_delta(self):
        baseline = MODULE.parse_cards({
            "Clicks": "1", "Signups": "0", "Paid signups": "0",
            "Conversion rate": "0%", "Revenue": "$0.00",
            "Commissions pending payment": "$0.00",
            "Commissions paid": "$0.00", "Earnings per click": "$0.00",
        })
        first = MODULE.build_receipt(baseline, {}, "first")
        current = dict(baseline, clicks=3, signups=1)
        later = MODULE.build_receipt(current, first, "later")
        self.assertEqual(later["baseline_metrics"], baseline)
        self.assertEqual(later["baseline_observed_at"], "first")
        self.assertEqual(later["delta_from_baseline"]["clicks"], 2)
        self.assertEqual(later["delta_from_baseline"]["signups"], 1)

    def test_extracts_value_when_comparison_labels_surround_click_total(self):
        text = """クリック数
Last 30 days
Previous 30 days
クリック数
Total
0
クリック数
1
100%
登録数
0
有料会員登録
0
コンバージョン率
0%
収益
$0.00
支払い待ちのコミッション
$0.00
支払い済みコミッション
$0.00
クリックあたりの収益
$0.00"""
        cards = MODULE.extract_cards(text)
        self.assertEqual(MODULE.parse_cards(cards)["clicks"], 1)

    def test_report_schema_requires_commission_key_and_attribution_fields(self):
        text = "\n".join(aliases[0] for aliases in MODULE.COMMISSION_FIELDS.values())
        fields = MODULE.present_fields(text, MODULE.COMMISSION_FIELDS)
        self.assertIn("commission_key", fields)
        self.assertIn("sub_id_1", fields)
        self.assertNotIn("transaction_id", fields)


if __name__ == "__main__":
    unittest.main()
