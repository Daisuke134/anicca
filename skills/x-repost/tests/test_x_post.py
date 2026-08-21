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
    def __init__(self, text: str, visible_url: str) -> None:
        self.text, self.visible_url = text, visible_url

    def query_selector(self, selector: str):
        if selector == 'div[data-testid="tweetText"]':
            return Node(text=self.text)
        if 'status/' in selector:
            return Node(href="/selawmqt/status/123")
        return None

    def query_selector_all(self, selector: str):
        return [Node(text=self.visible_url, href="https://t.co/example")]


class Page:
    def __init__(self, articles) -> None:
        self.articles = articles

    def query_selector_all(self, selector: str):
        return self.articles


class XPostTests(unittest.TestCase):
    def test_multiline_original_requires_exact_prefix_and_owned_url(self) -> None:
        text = "Before paying for an AI workflow: voice isolator.\n\nAffiliate link disclosure:\nhttps://aniccaai.com/blog/voice-isolator"
        found = MODULE.scan_timeline(
            Page([Article(text, "aniccaai.com/blog/voice-isolator")]), "selawmqt",
            "Before paying for an AI workflow: voice isolator.",
            "https://aniccaai.com/blog/voice-isolator", text,
        )
        self.assertEqual(found, "https://x.com/selawmqt/status/123")

    def test_original_rejects_similar_prefix_or_longer_url(self) -> None:
        text = "Before paying for an AI workflow: voice isolator.\n\nAffiliate link disclosure:\nhttps://aniccaai.com/blog/voice-isolator"
        found = MODULE.scan_timeline(
            Page([Article(
                "Before paying for an AI workflow: voice isolator. extra\n\nAffiliate link disclosure:\nhttps://aniccaai.com/blog/voice-isolator-plus",
                "aniccaai.com/blog/voice-isolator-plus",
            )]), "selawmqt", "Before paying for an AI workflow: voice isolator.",
            "https://aniccaai.com/blog/voice-isolator", text,
        )
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
