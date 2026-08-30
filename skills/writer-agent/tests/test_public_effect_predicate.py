import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/writer-agent/scripts"))

import article_generation_state as generation
import quality_feedback_recovery as feedback
import quality_repair_control as repair


class PublicEffectPredicateTest(unittest.TestCase):
    def test_pending_and_malformed_rows_are_not_public_effects(self):
        run_id = "20260829-165022"
        rows = [
            {
                "run_id": run_id,
                "platform": platform,
                "lang": lang,
                "published": False,
                "live_url": None,
                "state": state,
                "reality_gate": None,
            }
            for platform, lang, state in (
                ("note", "ja", "pending:required-media-generator-script-missing"),
                (
                    "substack",
                    "ja",
                    "pending:required-media-generator-script-missing; browser unavailable",
                ),
                (
                    "substack",
                    "en",
                    "pending:required-media-generator-script-missing; browser unavailable",
                ),
                (
                    "x-article",
                    "ja",
                    "pending:required-media-generator-script-missing; browser unavailable",
                ),
            )
        ]
        rows.append(
            {
                "run_id": run_id,
                "published": "true",
                "live_url": 123,
                "state": ["live"],
                "reality_gate": True,
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "articles.jsonl"
            ledger.write_text(
                "not-json\n" + "\n".join(map(json.dumps, rows)) + "\n",
                encoding="utf-8",
            )
            self.assertFalse(generation.ledger_has_public_effect(ledger, run_id))
            self.assertFalse(repair.ledger_has_public_effect(ledger, run_id))
            self.assertFalse(feedback.ledger_has_public_effect(ledger, run_id))
            self.assertIs(repair.ledger_has_public_effect, feedback.ledger_has_public_effect)

    def test_each_real_effect_shape_is_public(self):
        run_id = "20260829-165022"
        shapes = (
            {"published": True},
            {"live_url": "https://publisher.example/post"},
            {"state": "live"},
            {"reality_gate": "PASS"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "articles.jsonl"
            for shape in shapes:
                with self.subTest(shape=shape):
                    ledger.write_text(
                        json.dumps({"run_id": run_id, **shape}) + "\n",
                        encoding="utf-8",
                    )
                    self.assertTrue(generation.ledger_has_public_effect(ledger, run_id))


if __name__ == "__main__":
    unittest.main()
