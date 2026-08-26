from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "post_contract.py"
SPEC = importlib.util.spec_from_file_location("post_contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PostContractTests(unittest.TestCase):
    def test_japanese_slot_requires_japanese_text(self) -> None:
        self.assertTrue(MODULE.language_matches("ja", "これは次に試せる手順です"))
        self.assertFalse(MODULE.language_matches("ja", "Try this next."))
        self.assertFalse(MODULE.language_matches("ja", "Try this whole English paragraph next. 日本語"))
        self.assertFalse(MODULE.language_matches(
            "ja", "これは日本語の導入です。This entire English sentence must never leak into the post."
        ))
        self.assertFalse(MODULE.language_matches(
            "ja", "比較条件を一つに固定して、結果を記録すると判断しやすくなります。Use this workflow now."
        ))
        self.assertFalse(MODULE.language_matches(
            "ja", "比較条件を固定して記録すると判断しやすくなります。Use this, workflow now."
        ))
        self.assertFalse(MODULE.language_matches(
            "ja", "比較条件を固定して記録すると判断しやすくなります。Use this: workflow now."
        ))
        self.assertTrue(MODULE.language_matches("ja", "AIツールは、まず小さく比較してから選ぶ。"))
        self.assertTrue(MODULE.language_matches("ja", "Y Combinatorの話も、まず一次情報を確認する。"))
        self.assertFalse(MODULE.language_matches("ja", "人工智能产品增长"))

    def test_english_slot_rejects_japanese_text(self) -> None:
        self.assertTrue(MODULE.language_matches("en", "Try this next."))
        self.assertFalse(MODULE.language_matches("en", "次はこれを試す。"))
        self.assertFalse(MODULE.language_matches("en", "12345"))
        self.assertFalse(MODULE.language_matches("en", "Попробуйте это"))


if __name__ == "__main__":
    unittest.main()
