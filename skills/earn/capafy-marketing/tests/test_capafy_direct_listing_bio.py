#!/usr/bin/env python3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WRAPPER = ROOT / "skills" / "earn" / "capafy-marketing" / "capafy-ig-marketing-daily.sh"


class CapafyDirectListingBioTest(unittest.TestCase):
    def test_selected_agent_campaign_url_becomes_profile_website(self):
        source = WRAPPER.read_text(encoding="utf-8")

        self.assertIn('CAMPAIGN_URL="${LANDING_URL%/}/go/${SELECTED_AGENT_ID}"', source)
        self.assertIn('--website \'"$CAMPAIGN_URL"\'', source)
        self.assertIn("include the exact campaign URL \'\"$CAMPAIGN_URL\"\'", source)
        self.assertNotIn("Never use an individual Capafy listing URL for the Website", source)


if __name__ == "__main__":
    unittest.main()
