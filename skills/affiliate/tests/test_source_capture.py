import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "source_capture.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("affiliate_source_capture", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceCaptureTest(unittest.TestCase):
    def test_discovery_uses_agent_selected_candidate_instead_of_sitemap_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "skill"
            (root / "config" / "source-plans").mkdir(parents=True)
            state = Path(directory) / "state"
            selector = mock.Mock(return_value={
                "state": "READY",
                "decision_id": "decision-1",
                "selected_family": "speech-to-text",
                "hypothesis": "Decision-stage transcription intent will produce a measurable provider click.",
                "evidence": ["candidate family and current placement ledger"],
                "success_metric": "placement-attributed provider click delta",
            })
            sitemap = "\n".join((
                "https://elevenlabs.io/text-to-speech",
                "https://elevenlabs.io/speech-to-text",
            ))
            with (
                mock.patch.object(MODULE, "run_adapter", return_value=MODULE.DISCOVERY_SITEMAP),
                mock.patch.object(MODULE, "fetch_sitemap_xml", return_value=sitemap),
            ):
                receipt = MODULE.discover_official_plan(
                    root, state, 1000, opportunity_selector=selector,
                )

            self.assertEqual(receipt["selected_family"], "speech-to-text")
            self.assertEqual(receipt["opportunity_decision_id"], "decision-1")
            plan = json.loads((
                state / "discovered-source-plans"
                / "elevenlabs-discovered-speech-to-text-en.json"
            ).read_text())
            self.assertEqual(plan["offer_id"], "elevenlabs-speech-to-text")
            self.assertEqual(
                plan["opportunity_decision"]["decision_id"], "decision-1",
            )
            receipts = [{
                "source_id": "official-speech-to-text",
                "locator": "https://elevenlabs.io/speech-to-text",
                "evidence_class": "official_product",
                "raw_sha256": "a" * 64,
            }]
            bundle = MODULE.write_composition_bundle(state, plan, receipts)
            self.assertEqual(
                bundle["opportunity_decision"], plan["opportunity_decision"],
            )
            candidates = selector.call_args.args[2]
            self.assertEqual([row["family"] for row in candidates], [
                "text-to-speech", "speech-to-text",
            ])

    def test_failure_classes_are_explicit(self):
        self.assertIsNone(MODULE.classify_failure(0, "body"))
        self.assertEqual(MODULE.classify_failure(0, ""), "EMPTY")
        self.assertEqual(MODULE.classify_failure(1, "HTTP 429"), "RATE_LIMIT")
        self.assertEqual(MODULE.classify_failure(1, "HTTP 403"), "AUTH")
        self.assertEqual(MODULE.classify_failure(1, "boom"), "UPSTREAM")

    def test_refresh_all_plans_writes_one_daily_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "skill"
            plans = root / "config" / "source-plans"
            plans.mkdir(parents=True)
            for plan_id in ("alpha-en", "beta-en"):
                (plans / f"{plan_id}.json").write_text(json.dumps({
                    "schema_version": 1, "plan_id": plan_id, "locale": "en", "sources": [],
                }))
            state = Path(directory) / "state"
            with mock.patch.object(MODULE, "capture", return_value=[]):
                receipt = MODULE.refresh_all(root, state, now=1000, cooldown_seconds=86400)
                replay = MODULE.refresh_all(root, state, now=1001, cooldown_seconds=86400)
            self.assertEqual(receipt["state"], "COMPLETE")
            self.assertEqual([row["plan_id"] for row in receipt["plans"]], ["alpha-en", "beta-en"])
            self.assertTrue((state / "composition-inbox" / "alpha-en.json").is_file())
            self.assertEqual(replay["state"], "COOLDOWN")


if __name__ == "__main__":
    unittest.main()
