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
    def __init__(self, text: str, visible_url: str, article_links=None, quote_cards=None) -> None:
        self.text, self.visible_url = text, visible_url
        self.article_links = article_links or [Node(text=visible_url, href="https://t.co/example")]
        self.quote_cards = quote_cards or []

    def query_selector(self, selector: str):
        if selector == 'div[data-testid="tweetText"]':
            return Node(text=self.text)
        if 'status/' in selector:
            for link in self.article_links:
                if "/selawmqt/status/" in link.href:
                    return link
            return Node(href="/selawmqt/status/123")
        return None

    def query_selector_all(self, selector: str):
        if selector == 'div[data-testid="tweetText"] a':
            return [Node(text=self.visible_url, href="https://t.co/example")]
        if selector == "a":
            return self.article_links
        if selector == 'div[role="link"]':
            return self.quote_cards
        return []


class Page:
    def __init__(self, articles) -> None:
        self.articles = articles

    def query_selector_all(self, selector: str):
        return self.articles


class XPostTests(unittest.TestCase):
    def test_public_ssr_reconciles_exact_owned_post(self) -> None:
        text = "Affiliate link: https://aniccaai.com/blog/voice-changer"
        markup = '''<article data-tweet-id="2091088320772346136">
        <span>Affiliate link: </span>
        <a href="https://aniccaai.com/blog/voice-changer">article</a></article>'''
        self.assertEqual(
            MODULE.find_exact_public_markup(
                markup, text, "https://aniccaai.com/blog/voice-changer", "selawmqt"
            ),
            "https://x.com/selawmqt/status/2091088320772346136",
        )

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

    def test_source_backed_original_reads_x_quote_card_outside_tweet_text(self) -> None:
        source = "https://x.com/jun_song/status/2091114049954283855"
        body = "Pair cloud orchestration with local execution, then compare one task."
        text = f"{body}\n{source}"
        article = Article(
            body, "", article_links=[
                Node(href="/selawmqt/status/456"),
                Node(href="/jun_song/status/2091114049954283855"),
            ],
        )
        self.assertEqual(
            MODULE.scan_timeline(Page([article]), "selawmqt", body, source, text),
            "https://x.com/selawmqt/status/456",
        )

    def test_source_backed_original_reads_non_anchor_x_quote_card(self) -> None:
        source = "https://x.com/jun_song/status/2091114049954283855"
        body = "Pair cloud orchestration with local execution, then compare one task."
        text = f"{body}\n{source}"
        article = Article(
            body, "", article_links=[Node(href="/selawmqt/status/789")],
            quote_cards=[Node(text="Jun Song\n@jun_song\n2h\nExact quoted source body")],
        )
        self.assertEqual(
            MODULE.scan_timeline(Page([article]), "selawmqt", body, source, text),
            "https://x.com/selawmqt/status/789",
        )

    def test_source_backed_original_rejects_wrong_non_anchor_quote_card(self) -> None:
        source = "https://x.com/jun_song/status/2091114049954283855"
        body = "Pair cloud orchestration with local execution, then compare one task."
        text = f"{body}\n{source}"
        article = Article(
            body, "", article_links=[Node(href="/selawmqt/status/789")],
            quote_cards=[Node(text="Different author\n@jun_song_fan\n2h\nSimilar source body")],
        )
        self.assertIsNone(
            MODULE.scan_timeline(Page([article]), "selawmqt", body, source, text)
        )


if __name__ == "__main__":
    unittest.main()
