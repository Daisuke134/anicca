import json
import plistlib
import re
import unittest
from pathlib import Path


GIG_ROOT = Path(__file__).resolve().parents[1]
PASS = GIG_ROOT / "gig_pass.sh"
PLIST = GIG_ROOT / "launchd/ai.anicca.hf-gig-pass.plist"
REGISTRY = GIG_ROOT / "config/launchd/agents/gig.json"

# Production pass 1785282568-41648 stopped at one application because B0/B1
# consumed two shared calls and B2 could use only five more. B2 now owns a
# separate 40-call volume ceiling. Its observed charged-call average is about
# 79k; include the preceding B0/B1 142,023 tokens and keep the breaker above the
# resulting normal-volume estimate.
MEASURED_AVG_B2_CALL = 79_000
REQUIRED_B2_MODEL_SLOTS = 40
MEASURED_B0_B1_TOKENS = 142_023
EXPECTED_PASS_BREAKER = 4_194_304
EXPECTED_DAILY_BREAKER = 33_554_432


class RevenuePassBudgetTest(unittest.TestCase):
    def test_pass_breaker_cannot_starve_the_fourth_revenue_call(self):
        with PLIST.open("rb") as handle:
            plist = plistlib.load(handle)
        actual = int(plist["EnvironmentVariables"]["GIG_PASS_TOKEN_BUDGET"])
        self.assertGreaterEqual(
            actual,
            MEASURED_AVG_B2_CALL * REQUIRED_B2_MODEL_SLOTS
            + MEASURED_B0_B1_TOKENS,
        )
        self.assertEqual(actual, EXPECTED_PASS_BREAKER)

    def test_shell_registry_and_live_manifest_have_one_value(self):
        shell = PASS.read_text()
        match = re.search(
            r'ANICCA_PASS_TOKEN_BUDGET="\$\{GIG_PASS_TOKEN_BUDGET:-(\d+)\}"',
            shell,
        )
        self.assertIsNotNone(match)
        with PLIST.open("rb") as handle:
            plist = plistlib.load(handle)
        registry = json.loads(REGISTRY.read_text())
        values = {
            int(match.group(1)),
            int(plist["EnvironmentVariables"]["GIG_PASS_TOKEN_BUDGET"]),
            int(registry["agents"]["ai.anicca.hf-gig-pass"]["token_budget"]["pass_tokens"]),
        }
        self.assertEqual(values, {EXPECTED_PASS_BREAKER})

    def test_daily_breaker_is_not_removed(self):
        with PLIST.open("rb") as handle:
            plist = plistlib.load(handle)
        self.assertEqual(
            int(plist["EnvironmentVariables"]["GIG_DAILY_TOKEN_BUDGET"]),
            EXPECTED_DAILY_BREAKER,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
