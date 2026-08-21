from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "x_post.py"
SPEC = importlib.util.spec_from_file_location("x_post", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Node:
    def __init__(self, *, text: str = "", href: str = "") -> None:
        self.text, self.href = text, href

    def inner_text(self) -> str:
        return self.text

    def get_attribute(self, name: str) -> str:
        return self.href if name == "href" else ""


class Article:
    def query_selector(self, selector: str):
        if selector == 'div[data-testid="tweetText"]':
            return Node(text="Before paying for an AI workflow: voice isolator.\n\nAffiliate link disclosure:\nhttps://aniccaai.com/blog/voice-isolator")
        if 'status/' in selector:
            return Node(href="/selawmqt/status/123")
        return None

    def query_selector_all(self, selector: str):
        return [Node(text="aniccaai.com/blog/voice-isolator", href="https://t.co/example")]


class Page:
    def query_selector_all(self, selector: str):
        return [Article()]


class XPostTests(unittest.TestCase):
    def test_multiline_original_requires_exact_prefix_and_owned_url(self) -> None:
        found = MODULE.scan_timeline(
            Page(), "selawmqt", "Before paying for an AI workflow: voice isolator.",
            "https://aniccaai.com/blog/voice-isolator",
        )
        self.assertEqual(found, "https://x.com/selawmqt/status/123")


if __name__ == "__main__":
    unittest.main()
