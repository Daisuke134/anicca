"""Lancers must search for what the catalogue sells.

Measured 2026-09-07: Lancers applied to nothing all day. Not a form problem and not a session
problem -- the planner judged 10 fresh projects per wake and found zero it could honestly take.
The last 60 decisions were 17 `mandatory_attribute_fabrication`, 14 `mandatory_human_presence`,
14 `video_or_animation`, against a board of short-video editing, on-site filming in 錦糸町, and
Threads management.

The lane had fetched that board itself. Half of `DISCOVERY_QUERIES` was SNS and content marketing
("SNS運用", "SNS投稿", "コンテンツ制作", "X運用", "B2Bマーケティング") while all 20 catalogue
listings are system and automation build work. One query runs per pass, so most passes saw nothing
sellable. The lane was fetching work it is honest enough to refuse.

Run: python3 -m pytest apps/lancers-revenue/tests/test_queries_match_catalogue.py
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LOOP = ROOT / "skills" / "earn" / "lancers" / "scripts" / "application_loop.py"
CATALOG = ROOT / "skills" / "gig-work" / "profile" / "listings" / "catalog.json"


def _queries():
    spec = importlib.util.spec_from_file_location("lancers_loop_under_test", LOOP)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.DISCOVERY_QUERIES


def _catalogue_text() -> str:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else (data.get("listings") or data.get("items") or [])
    parts = []
    for item in items:
        parts.append(str(item.get("title_ja") or ""))
        parts.append(str(item.get("value_prop") or ""))
        parts.append(str(item.get("family") or "").replace("_", " "))
    return " ".join(parts)


@pytest.mark.parametrize("query", _queries())
def test_every_query_is_something_the_catalogue_sells(query):
    """A term with no catalogue backing fetches work the planner will refuse."""
    haystack = _catalogue_text().lower()
    assert query.lower() in haystack, (
        f"'{query}' appears nowhere in the catalogue, so it can only fetch work we decline"
    )


@pytest.mark.parametrize("banned", [
    "SNS運用", "SNS投稿", "コンテンツ制作", "X運用", "B2Bマーケティング",
])
def test_the_marketing_terms_that_caused_this_are_gone(banned):
    assert banned not in _queries()


def test_the_catalogue_really_is_build_work_only():
    """If the catalogue ever does sell video or SNS work, this test should be the thing that
    fails first -- reinstating those queries would then be correct, not a regression."""
    text = _catalogue_text()
    for absent in ("動画編集", "SNS運用", "撮影"):
        assert absent not in text


def test_a_query_is_a_noun_phrase_not_a_title():
    """The recipe: 業務自動化システムを開発 finds nothing, 業務自動化 returns a live board."""
    for query in _queries():
        assert "します" not in query and "承ります" not in query
        assert len(query) <= 12
