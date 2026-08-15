import importlib.util
import sys
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


if __name__ == "__main__":
    unittest.main()
