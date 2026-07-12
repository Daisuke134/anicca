"""Tests for news_search — the module that gives the betting brain eyes.

No network: the subprocess call is injected. What these lock down is the contract
pick.py depends on — a search failure must never stop a trading pass, and a bet's
evidence must survive into the emitted decision.
"""
import news_search
from news_search import build_question_with_news, search_news

FIRECRAWL_OUT = """Hanwha Life Esports vs Bilibili Gaming in League of Legends MSI ...
  URL: https://www.sportskeeda.com/esports/hle-vs-blg-msi-2026-final
  BLG should have the upper hand over HLE if both teams enter the Grand Final ...

Hanwha Life Esports vs. Bilibili Gaming / MSI 2026 - Reddit
  URL: https://www.reddit.com/r/leagueoflegends/comments/1urkd7m/hle_vs_blg/
  Winner: Bilibili Gaming in 24m.
"""


def test_returns_text_and_urls_from_search():
    def runner(argv, timeout_s):
        assert argv[1] == "search"
        assert "Bilibili" in argv[2]
        return FIRECRAWL_OUT

    text, urls = search_news("Who wins Bilibili Gaming vs Hanwha Life?", runner=runner)

    assert "upper hand" in text
    assert urls == [
        "https://www.sportskeeda.com/esports/hle-vs-blg-msi-2026-final",
        "https://www.reddit.com/r/leagueoflegends/comments/1urkd7m/hle_vs_blg/",
    ]


def test_search_failure_never_raises_and_never_blocks_the_pass():
    def exploding_runner(argv, timeout_s):
        raise RuntimeError("firecrawl is down / no API key / timed out")

    text, urls = search_news("anything", runner=exploding_runner)

    assert (text, urls) == ("", [])


def test_empty_search_result_yields_no_news():
    text, urls = search_news("anything", runner=lambda argv, t: "   \n ")
    assert (text, urls) == ("", [])


def test_blank_query_is_not_searched():
    def must_not_run(argv, timeout_s):
        raise AssertionError("search must not run on a blank question")

    assert search_news("", runner=must_not_run) == ("", [])


def test_output_is_capped_so_prompt_cost_stays_bounded(monkeypatch):
    monkeypatch.setattr(news_search, "NEWS_MAX_CHARS", 50)
    text, _ = search_news("q", runner=lambda argv, t: "x" * 5000)
    assert len(text) == 50


def test_question_carries_the_evidence_to_the_model():
    q = build_question_with_news("Will BLG win?", FIRECRAWL_OUT)

    assert "Will BLG win?" in q
    assert "upper hand" in q
    # The model must be told the price may not reflect this yet — that gap IS the edge.
    assert "may not yet" in q


def test_question_is_untouched_when_there_is_no_news():
    assert build_question_with_news("Will BLG win?", "") == "Will BLG win?"
