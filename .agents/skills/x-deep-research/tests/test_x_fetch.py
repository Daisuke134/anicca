from pathlib import Path
import sys

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from x_fetch import build_command, normalize_payload, validate_url  # noqa: E402


def test_rejects_non_x_url():
    with pytest.raises(ValueError, match="canonical X status URL"):
        validate_url("https://example.com/status/1")


def test_rejects_x_url_without_status_id():
    with pytest.raises(ValueError, match="canonical X status URL"):
        validate_url("https://x.com/search?q=agents")


def test_command_pins_reviewed_upstream_commit():
    assert build_command("https://x.com/a/status/1") == [
        "uvx",
        "--from",
        "git+https://github.com/ythx-101/x-tweet-fetcher.git@085b931f53557da9e25c0d2e6aa5b3b980513125",
        "xtf",
        "--url",
        "https://x.com/a/status/1",
    ]


def test_article_payload_is_marked_complete():
    raw = {
        "tweet": {
            "text": "",
            "is_article": True,
            "article": {"title": "T", "full_text": "full body"},
        }
    }
    got = normalize_payload("https://x.com/a/status/1", raw)
    assert got["kind"] == "article"
    assert got["complete"] is True
    assert got["error_code"] is None


def test_empty_article_body_is_not_complete():
    raw = {
        "tweet": {
            "text": "",
            "is_article": True,
            "article": {"title": "T", "full_text": ""},
        }
    }
    got = normalize_payload("https://x.com/a/status/1", raw)
    assert got["complete"] is False
    assert got["error_code"] == "empty_article_body"


def test_regular_post_requires_nonempty_text():
    raw = {"tweet": {"text": "hello", "is_article": False, "article": None}}
    got = normalize_payload("https://x.com/a/status/1", raw)
    assert got["kind"] == "post"
    assert got["complete"] is True


def test_missing_tweet_object_is_machine_readable_failure():
    got = normalize_payload("https://x.com/a/status/1", {"error": "not found"})
    assert got["complete"] is False
    assert got["error_code"] == "missing_tweet"

