from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "x_evaluate.py"
SPEC = importlib.util.spec_from_file_location("x_evaluate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class XEvaluateTests(unittest.TestCase):
    def test_tone_evaluation_excludes_affiliate_disclosed_rows(self) -> None:
        now = datetime.now(timezone.utc)
        posted, samples = [], []
        for tone, views in (("primary", 2), ("empathy", 10), ("affiliate_disclosed", 100)):
            for index in range(3):
                url = f"https://x.com/me/status/{tone}-{index}"
                posted.append({
                    "posted_at": now.isoformat(), "post_url": url,
                    "kind": "affiliate_original" if tone == "affiliate_disclosed" else "quote",
                    "tone": tone,
                })
                samples.append({"post_url": url, "ok": True, "age_minutes": 90, "views": views})
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            (state / "strategy.json").write_text(json.dumps({
                "reply_ratio": 0.0,
                "tone_weights": {"primary": 1.0, "empathy": 1.0, "funny": 1.0},
            }), encoding="utf-8")
            result = MODULE.evaluate_tone(
                posted, samples, now - timedelta(hours=48), state, False,
                {"ts": now.isoformat(), "window_hours": 48},
            )
        self.assertNotIn("affiliate_disclosed", result["samples"])
        self.assertEqual(result["reason"], "empathy 10 vs primary 2 early views")

    def test_original_ratio_moves_only_after_both_arms_have_three_samples(self) -> None:
        now = datetime.now(timezone.utc)
        posted, samples = [], []
        for kind, views in (("original", 30), ("quote", 10)):
            for index in range(3):
                url = f"https://x.com/me/status/{kind}-{index}"
                posted.append({"posted_at": now.isoformat(), "post_url": url, "kind": kind})
                samples.append({"post_url": url, "ok": True, "age_minutes": 90, "views": views})
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            (state / "strategy.json").write_text(
                json.dumps({"original_ratio": 0.15, "reply_ratio": 0.0}), encoding="utf-8")
            result = MODULE.evaluate_original_ratio(
                posted, samples, now - timedelta(hours=48), state, True,
                {"ts": now.isoformat(), "window_hours": 48},
            )
            strategy = json.loads((state / "strategy.json").read_text(encoding="utf-8"))
        self.assertEqual(result["verdict"], "moved")
        self.assertEqual(result["to"], 0.20)
        self.assertEqual(strategy["original_ratio"], 0.20)


if __name__ == "__main__":
    unittest.main()
