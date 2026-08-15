import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "program_registry.py"
SPEC = importlib.util.spec_from_file_location("affiliate_program_registry", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProgramRegistryTest(unittest.TestCase):
    def test_store_login_replaces_only_login_and_keeps_private_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "credentials.md"
            path.write_text(
                "## Impact\n- Login: broken-description\n- Password: keep-secret\n"
                "\n## Other\n- Login: untouched@example.com\n",
                encoding="utf-8",
            )
            path.chmod(0o600)
            result = MODULE.store_login("Impact", path, "owner@example.com")
            text = path.read_text(encoding="utf-8")
            self.assertEqual(result["private_markdown_login_state"], "VERIFIED_NONEMPTY")
            self.assertIn("- Login: owner@example.com", text)
            self.assertIn("- Password: keep-secret", text)
            self.assertIn("- Login: untouched@example.com", text)
            self.assertEqual(path.stat().st_mode & 0o077, 0)

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

    def test_store_link_adds_only_private_affiliate_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "credentials.md"
            path.write_text(
                "## ElevenLabs\n- Login: owner@example.com\n- Password: keep-secret\n",
                encoding="utf-8",
            )
            path.chmod(0o600)
            link = "https://example.test/private-referral"
            result = MODULE.store_link(
                "ElevenLabs", "ElevenAgents affiliate link", path, link,
            )
            text = path.read_text(encoding="utf-8")
            self.assertEqual(result["private_markdown_link_state"], "VERIFIED_NONEMPTY")
            self.assertNotIn(link, str(result))
            self.assertIn(f"- ElevenAgents affiliate link: {link}", text)
            self.assertIn("- Password: keep-secret", text)
            self.assertEqual(path.stat().st_mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
