from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from browser_search import (  # noqa: E402
    choose_search_page,
    classify_page,
    dedupe_results,
    stop_reason,
)


class Page:
    def __init__(self, url: str):
        self.url = url


def test_article_editor_is_never_selected_for_search():
    editor = Page("https://x.com/compose/articles/edit/2081491516254830592")
    assert choose_search_page([editor]) is None


def test_existing_search_page_wins_over_editor_and_blank():
    editor = Page("https://x.com/compose/articles/edit/2081491516254830592")
    blank = Page("about:blank")
    search = Page("https://x.com/search?q=agents&src=typed_query")
    assert choose_search_page([editor, blank, search]) is search


def test_blank_page_is_safe_fallback():
    blank = Page("about:blank")
    assert choose_search_page([blank]) is blank


def test_messages_settings_and_intents_are_protected():
    assert classify_page("https://x.com/messages") == "protected"
    assert classify_page("https://x.com/settings/account") == "protected"
    assert classify_page("https://x.com/intent/like?tweet_id=1") == "protected"


def test_duplicate_status_urls_keep_one_result():
    rows = [
        {"url": "https://x.com/a/status/1", "text": "one"},
        {"url": "https://x.com/a/status/1/analytics", "text": "one repeated"},
        {"url": "https://x.com/b/status/2", "text": "two"},
    ]
    assert dedupe_results(rows) == [
        {"url": "https://x.com/a/status/1", "text": "one"},
        {"url": "https://x.com/b/status/2", "text": "two"},
    ]


def test_requested_count_marks_complete():
    assert (
        stop_reason(
            result_count=20,
            requested_count=20,
            scrolls=4,
            max_scrolls=30,
            stagnant=0,
        )
        is None
    )


def test_stagnation_is_explicit_partial_reason():
    assert (
        stop_reason(
            result_count=8,
            requested_count=20,
            scrolls=7,
            max_scrolls=30,
            stagnant=3,
        )
        == "stagnant_after_3_scrolls"
    )


def test_scroll_cap_is_explicit_partial_reason():
    assert (
        stop_reason(
            result_count=18,
            requested_count=20,
            scrolls=30,
            max_scrolls=30,
            stagnant=0,
        )
        == "max_scrolls_reached"
    )

