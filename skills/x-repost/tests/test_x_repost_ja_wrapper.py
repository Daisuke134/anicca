import pathlib
import tomllib
import unittest


ROOT = pathlib.Path(__file__).parents[3]
WRAPPER = ROOT / "skills/x-repost/x-repost-ja-cli.sh"
MAIN = ROOT / "skills/x-repost/x-repost-cli.sh"


class JapaneseDiceLoopContractTests(unittest.TestCase):
    def test_wrapper_owns_dice_identity_and_japanese_any_source_policy(self):
        text = WRAPPER.read_text()
        for contract in (
            'X_REPOST_BROWSER_IDENTITY="x:diceai0"',
            'X_REPOST_ACCOUNT_HANDLE="@diceai0"',
            'X_REPOST_FORCE_LANGUAGE="ja"',
            'X_REPOST_SOURCE_LANGUAGE_POLICY="any"',
            'X_REPOST_FORCE_KIND="quote"',
            'X_REPOST_PUBLISH_TRANSPORT="browser"',
        ):
            self.assertIn(contract, text)

    def test_prompt_allows_english_source_but_requires_japanese_output(self):
        text = MAIN.read_text()
        self.assertIn("日本語・英語どちらの候補も選べる", text)
        self.assertIn("英語sourceは自然な日本語の付加価値へ翻訳", text)
        self.assertIn('registry_enforce_or_exit "$LOOP_NAME"', text)

    def test_launchd_contract_is_half_hourly_and_offset(self):
        loop = tomllib.loads((ROOT / "loops/x-repost-ja/loop.toml").read_text())
        self.assertEqual(loop["jobs"]["pass"]["calendars"], [{"minute": 5}, {"minute": 35}])
        self.assertEqual(loop["jobs"]["healthcheck"]["env"]["X_LOOP_LABEL"],
                         "ai.anicca.x-repost-ja-pass")


if __name__ == "__main__":
    unittest.main()
