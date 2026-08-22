import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "x_post_cli.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("affiliate_x_post", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class XPostContractTest(unittest.TestCase):
    def test_disclosure_owned_url_and_stable_placement_are_required(self):
        text = "My notes on voice workflows. Affiliate link: https://aniccaai.com/blog/voice-workflows"
        self.assertEqual(MODULE.validate_content(text), text)
        self.assertEqual(MODULE.content_fingerprint(text), MODULE.content_fingerprint(text))
        with tempfile.TemporaryDirectory() as root:
            expected = Path(root) / "x-posts" / "elevenlabs-en-1.json"
            self.assertEqual(MODULE.placement_path(Path(root), "elevenlabs-en-1"), expected)
        with self.assertRaises(MODULE.XPostError):
            MODULE.validate_content("Read https://aniccaai.com/blog/voice-workflows")
        with self.assertRaises(MODULE.XPostError):
            MODULE.validate_content("#ad https://example.com/not-owned")

    def test_live_owned_article_receipt_is_required(self):
        text = "Affiliate link: https://aniccaai.com/blog/voice-workflows"
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            with self.assertRaises(MODULE.XPostError):
                MODULE.require_live_owned_article(state, text)
            path = state / "owned-publications" / "voice-workflows.json"
            path.parent.mkdir()
            path.write_text(json.dumps({
                "state": "LIVE",
                "public_url": "https://aniccaai.com/blog/voice-workflows",
            }))
            self.assertIsNone(MODULE.require_live_owned_article(state, text))

    def test_x_short_url_is_reconciled_to_owned_article(self):
        text = "Affiliate link: https://aniccaai.com/blog/voice-workflows"
        rows = [{
            "text": "Affiliate link: https://\naniccaai.com/blog/voice-work…",
            "url": "https://x.com/selawmqt/status/123",
            "outbound": ["https://t.co/unit"],
        }]
        self.assertEqual(
            MODULE.find_exact(rows, text, resolver=lambda _: "https://aniccaai.com/blog/voice-workflows"),
            "https://x.com/selawmqt/status/123",
        )
        self.assertEqual(MODULE.find_exact(rows, text, resolver=lambda _: "https://example.com/wrong"), "")

    def test_public_ssr_profile_reconciles_exact_owned_post(self):
        text = "Affiliate link: https://aniccaai.com/blog/voice-workflows"
        markup = '''
        <article data-tweet-id="123">
          <span>Affiliate link: </span>
          <a href="https://aniccaai.com/blog/voice-workflows">aniccaai.com/blog/voice…</a>
        </article>
        <article data-tweet-id="456">
          <span>Affiliate link: </span>
          <a href="https://aniccaai.com/blog/wrong">wrong</a>
        </article>
        '''
        self.assertEqual(
            MODULE.find_exact_public_markup(markup, text, "selawmqt"),
            "https://x.com/selawmqt/status/123",
        )


if __name__ == "__main__":
    unittest.main()
