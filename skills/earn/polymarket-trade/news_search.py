"""news_search.py — give the betting brain EYES on the world.

Why this file exists (2026-07-12, Dais): `pick.py` asked the model to price a market
while showing it ONLY the market's own question and the market's own current price.
A model with zero outside information cannot beat a price that thousands of traders
already set — so it either WAITs forever or coin-flips. Every dollar claude-p has
actually earned came from directional bets (+$9.91) whose reasoning was, in truth,
luck: 4 bets, 4 wins, no evidence. Edge comes from KNOWING something the price does
not yet reflect. That means searching.

This module does exactly one thing: run a web search and hand back the raw text plus
the URLs it came from. It makes NO judgment about what the news means — that is the
model's job (see ~/.claude/rules/building-effective-ai-agents.md: judgment belongs to
the model, never to a regex or an if-else). The regex here only PARSES URLs out of a
fixed CLI output format, which is not judgment.

Failure is never fatal: a search that errors, times out, or returns nothing yields
("", []) and the pass proceeds exactly as it did before this file existed. It can only
add information, never remove it.
"""
import os
import re
import subprocess

FIRECRAWL_BIN = os.environ.get("FIRECRAWL_BIN", "firecrawl")
NEWS_LIMIT = int(os.environ.get("NEWS_SEARCH_LIMIT", "4"))
NEWS_TIMEOUT_S = int(os.environ.get("NEWS_SEARCH_TIMEOUT_S", "75"))
# Hard cap on what we paste into the prompt. Keeps token cost bounded and predictable.
NEWS_MAX_CHARS = int(os.environ.get("NEWS_SEARCH_MAX_CHARS", "2400"))

_URL_RE = re.compile(r"https?://[^\s)>\]]+")


def _default_runner(argv, timeout_s):
    """Effectful seam. Tests inject their own runner; nothing here touches the network."""
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""


def search_news(query, limit=None, runner=None, timeout_s=None):
    """Search the web for what this market is actually about.

    Returns (text, urls). On ANY failure returns ("", []) — never raises, never
    blocks the trading pass. An empty result means the model simply prices the
    market the way it did before: with no outside information.
    """
    if not query or not str(query).strip():
        return "", []
    run = runner or _default_runner
    argv = [
        FIRECRAWL_BIN,
        "search",
        str(query),
        "--limit",
        str(limit or NEWS_LIMIT),
    ]
    try:
        out = run(argv, timeout_s or NEWS_TIMEOUT_S)
    except Exception:
        return "", []
    if not out or not out.strip():
        return "", []
    text = out.strip()[:NEWS_MAX_CHARS]
    urls = _URL_RE.findall(text)
    return text, urls


def build_question_with_news(question, news_text):
    """Fold the search result into the question handed to the model.

    Deliberately does NOT tell the model what to conclude — it hands over the raw
    findings and reminds it that the market price may not yet reflect them. The
    model forms its own probability; that is the whole point of having an edge.
    """
    if not news_text:
        return question
    return (
        f"{question}\n\n"
        "WEB SEARCH RESULTS (fetched moments ago — the market price may not yet "
        "reflect these):\n"
        f"{news_text}\n\n"
        "Weigh this evidence yourself. If it tells you nothing the price already "
        "knows, say so with low confidence."
    )
