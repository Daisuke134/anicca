import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "program_registry.py"
SPEC = importlib.util.spec_from_file_location("affiliate_program_registry", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProgramRegistryTest(unittest.TestCase):
    def test_network_section_inherits_login_but_not_password(self):
        source = "## ElevenLabs\n- Login: owner@example.com\n- Password: original\n"
        result = MODULE.ensure_credential_section(
            source, "PartnerStack", "ElevenLabs",
            "keychain://ai.anicca.affiliate.provider.partnerstack/elevenlabs",
        )
        partner = result.split("## PartnerStack", 1)[1]
        self.assertIn("- Login: owner@example.com", partner)
        self.assertIn("- Password: \n", partner)
        self.assertNotIn("original", partner)


if __name__ == "__main__":
    unittest.main()
