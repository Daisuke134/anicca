import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "content.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("affiliate_content", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ContentPolicyTest(unittest.TestCase):
    def test_disclosure_source_hash_and_owned_link_gate(self):
        link = "https://try.elevenlabs.io/unit"
        markdown = f"*{MODULE.DISCLOSURE}*\n\nUseful comparison. [Try it]({link})"
        artifact = {
            "markdown": markdown,
            "content_sha256": MODULE.hashlib.sha256(markdown.encode()).hexdigest(),
            "source_hashes": {"official": "abc"},
        }
        self.assertTrue(all(MODULE.policy_checks(artifact, {"official": "abc"}, link).values()))
        artifact["markdown"] = f"[Try it]({link})\n\n{MODULE.DISCLOSURE}"
        self.assertFalse(MODULE.policy_checks(artifact, {"official": "abc"}, link)["disclosure_before_first_cta"])

    def test_elevenagents_x_artifact_fits_platform_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            publications = state / "owned-publications"
            publications.mkdir()
            slug = "elevenagents-for-customer-support"
            url = f"https://aniccaai.com/blog/{slug}"
            (publications / f"{slug}.json").write_text(
                json.dumps({"state": "LIVE", "public_url": url}), encoding="utf-8"
            )

            result = MODULE.build_x_agents(state)
            text = (state / "x-content" / "elevenagents-en-1.txt").read_text().strip()
            self.assertEqual(result["state"], "READY_FOR_X_PUBLICATION")
            self.assertLessEqual(len(text), 280)
            self.assertIn("Affiliate link", text)
            self.assertIn(url, text)


if __name__ == "__main__":
    unittest.main()
