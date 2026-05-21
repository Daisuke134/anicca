"""
Unit Tests for TikTok → Instagram Cross-Poster

Tests RSS parsing, Apify scraping, Instagram posting, state management,
scheduling logic, and the full flow with mocks.
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Add parent to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import TIKTOK_ONLY_HASHTAGS
from rss_parser import fetch_new_posts, _get_media_url
from instagram_poster import strip_tiktok_hashtags
from state import load_processed_ids, save_processed_id, STATE_FILE
from cross_post_tiktok_to_ig import next_posting_slot, process_account

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# =============================================================================
# RSS Feed Tests
# =============================================================================

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>TikTok @anicca.en</title>
    <item>
      <title>#selfimprovement #mentalhealth</title>
      <link>https://www.tiktok.com/@anicca.en/video/111</link>
      <pubDate>Sat, 01 Feb 2026 06:00:00 GMT</pubDate>
      <media:content url="https://cdn.tiktok.com/thumb1.jpg" medium="image"/>
    </item>
    <item>
      <title>Old post caption</title>
      <link>https://www.tiktok.com/@anicca.en/video/222</link>
      <pubDate>Mon, 26 Jan 2026 06:00:00 GMT</pubDate>
      <media:content url="https://cdn.tiktok.com/thumb2.jpg" medium="image"/>
    </item>
    <item>
      <title>Recent post</title>
      <link>https://www.tiktok.com/@anicca.en/video/333</link>
      <pubDate>Fri, 31 Jan 2026 18:00:00 GMT</pubDate>
      <media:content url="https://cdn.tiktok.com/thumb3.jpg" medium="image"/>
    </item>
  </channel>
</rss>"""


@patch("rss_parser.requests.get")
def test_parse_rss_feed(mock_get):
    """Test: RSS feed is parsed correctly with all fields."""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_RSS
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    since = datetime(2026, 1, 1, tzinfo=UTC)
    posts = fetch_new_posts("https://rss.app/feeds/test.xml", since)

    assert len(posts) == 3
    assert posts[0]["link"] == "https://www.tiktok.com/@anicca.en/video/111"
    assert posts[0]["title"] == "#selfimprovement #mentalhealth"
    assert posts[0]["thumbnail"] == "https://cdn.tiktok.com/thumb1.jpg"


@patch("rss_parser.requests.get")
def test_filter_posts_since(mock_get):
    """Test: Only posts after `since` are returned."""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_RSS
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    # Since Jan 31 12:00 UTC → should get video/111 (Feb 1) and video/333 (Jan 31 18:00)
    since = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)
    posts = fetch_new_posts("https://rss.app/feeds/test.xml", since)

    assert len(posts) == 2
    links = {p["link"] for p in posts}
    assert "https://www.tiktok.com/@anicca.en/video/111" in links
    assert "https://www.tiktok.com/@anicca.en/video/333" in links
    assert "https://www.tiktok.com/@anicca.en/video/222" not in links


@patch("rss_parser.requests.get")
def test_rss_fetch_error(mock_get):
    """Test: RSS fetch error raises exception."""
    mock_get.side_effect = Exception("Connection timeout")

    with pytest.raises(Exception, match="Connection timeout"):
        fetch_new_posts("https://rss.app/feeds/broken.xml", datetime.now(UTC))


# =============================================================================
# State Management Tests
# =============================================================================

def test_skip_processed_posts(tmp_path, monkeypatch):
    """Test: Processed IDs are loaded and new IDs are saved."""
    state_file = tmp_path / "processed_ids.json"
    monkeypatch.setattr("state.STATE_FILE", state_file)

    # Initially empty
    ids = load_processed_ids()
    assert ids == set()

    # Save some IDs
    save_processed_id("url1")
    save_processed_id("url2")

    ids = load_processed_ids()
    assert ids == {"url1", "url2"}

    # Duplicate save is idempotent
    save_processed_id("url1")
    ids = load_processed_ids()
    assert ids == {"url1", "url2"}


# =============================================================================
# Apify Scraper Tests
# =============================================================================

SAMPLE_APIFY_RESPONSE = [
    {
        "webVideoUrl": "https://www.tiktok.com/@anicca.en/video/111",
        "isSlideshow": True,
        "slideshowImageLinks": [
            {"tiktokLink": "https://cdn1.jpg", "downloadLink": "https://dl1.jpg"},
            {"tiktokLink": "https://cdn2.jpg", "downloadLink": "https://dl2.jpg"},
            {"tiktokLink": "https://cdn3.jpg", "downloadLink": "https://dl3.jpg"},
        ],
    },
    {
        "webVideoUrl": "https://www.tiktok.com/@anicca.en/video/444",
        "isSlideshow": False,
    },
    {
        "webVideoUrl": "https://www.tiktok.com/@anicca.en/video/333",
        "isSlideshow": True,
        "slideshowImageLinks": [
            {"tiktokLink": "https://cdn4.jpg", "downloadLink": ""},
            {"tiktokLink": "https://cdn5.jpg"},
        ],
    },
]


@patch("tiktok_scraper._fetch_dataset")
@patch("tiktok_scraper.requests.post")
def test_scrape_profile_slideshows(mock_post, mock_dataset):
    """Test: Profile scrape returns slideshow images for target URLs."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {"defaultDatasetId": "ds123"}}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp
    mock_dataset.return_value = SAMPLE_APIFY_RESPONSE

    from tiktok_scraper import scrape_profile_slideshows

    result = scrape_profile_slideshows(
        "anicca.en",
        [
            "https://www.tiktok.com/@anicca.en/video/111",
            "https://www.tiktok.com/@anicca.en/video/333",
        ],
    )

    # video/111 → 3 images (downloadLink preferred)
    assert "https://www.tiktok.com/@anicca.en/video/111" in result
    assert result["https://www.tiktok.com/@anicca.en/video/111"] == [
        "https://dl1.jpg", "https://dl2.jpg", "https://dl3.jpg"
    ]

    # video/333 → 2 images (fallback to tiktokLink when downloadLink empty)
    assert "https://www.tiktok.com/@anicca.en/video/333" in result
    assert result["https://www.tiktok.com/@anicca.en/video/333"] == [
        "https://cdn4.jpg", "https://cdn5.jpg"
    ]


@patch("tiktok_scraper._fetch_dataset")
@patch("tiktok_scraper.requests.post")
def test_skip_video_post(mock_post, mock_dataset):
    """Test: Video posts (non-slideshow) are excluded from results."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {"defaultDatasetId": "ds123"}}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp
    mock_dataset.return_value = SAMPLE_APIFY_RESPONSE

    from tiktok_scraper import scrape_profile_slideshows

    result = scrape_profile_slideshows(
        "anicca.en",
        ["https://www.tiktok.com/@anicca.en/video/444"],  # video, not slideshow
    )

    assert "https://www.tiktok.com/@anicca.en/video/444" not in result


@patch("tiktok_scraper.requests.post")
def test_apify_error_continues(mock_post):
    """Test: Apify error raises exception (handled by caller)."""
    mock_post.side_effect = Exception("Apify quota exceeded")

    from tiktok_scraper import scrape_profile_slideshows

    with pytest.raises(Exception, match="Apify quota exceeded"):
        scrape_profile_slideshows("anicca.en", ["https://example.com/video/1"])


# =============================================================================
# Instagram Poster Tests
# =============================================================================

@patch("instagram_poster.requests.post")
def test_upload_images_to_blotato(mock_post):
    """Test: Images are uploaded to Blotato storage."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"url": "https://database.blotato.com/uploaded.jpg"}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    from instagram_poster import upload_image_to_blotato

    result = upload_image_to_blotato("https://cdn.tiktok.com/temp.jpg")
    assert result == "https://database.blotato.com/uploaded.jpg"

    call_args = mock_post.call_args
    assert call_args.kwargs["json"] == {"url": "https://cdn.tiktok.com/temp.jpg"}


@patch("instagram_poster.requests.post")
def test_post_carousel_to_instagram(mock_post):
    """Test: Carousel is posted with correct Blotato payload."""
    upload_resp = MagicMock()
    upload_resp.json.return_value = {"url": "https://database.blotato.com/img.jpg"}
    upload_resp.raise_for_status = MagicMock()

    post_resp = MagicMock()
    post_resp.json.return_value = {"postSubmissionId": "sub123"}
    post_resp.raise_for_status = MagicMock()

    mock_post.side_effect = [upload_resp, upload_resp, post_resp]

    from instagram_poster import upload_and_post_carousel

    result = upload_and_post_carousel(
        account_id="28896",
        caption="Test caption",
        image_urls=["https://img1.jpg", "https://img2.jpg"],
        scheduled_time="2026-02-01T00:00:00+00:00",
    )

    assert result == {"postSubmissionId": "sub123"}

    # Verify the final post call
    final_call = mock_post.call_args_list[-1]
    payload = final_call.kwargs["json"]
    assert payload["post"]["accountId"] == "28896"
    assert payload["post"]["content"]["platform"] == "instagram"
    assert len(payload["post"]["content"]["mediaUrls"]) == 2
    assert "mediaType" not in payload["post"]["target"]
    assert payload["scheduledTime"] == "2026-02-01T00:00:00+00:00"


@patch("instagram_poster.requests.post")
def test_blotato_error_continues(mock_post):
    """Test: Blotato API error raises exception (handled by caller)."""
    mock_post.side_effect = Exception("Blotato 429 rate limit")

    from instagram_poster import upload_image_to_blotato

    with pytest.raises(Exception, match="429 rate limit"):
        upload_image_to_blotato("https://example.com/img.jpg")


# =============================================================================
# Caption Processing Tests
# =============================================================================

def test_strip_tiktok_hashtags():
    """Test: TikTok-specific hashtags are removed, others preserved."""
    caption = "#selfimprovement #mentalhealth #fyp #foryou #viral #anicca"
    result = strip_tiktok_hashtags(caption)
    assert "#fyp" not in result
    assert "#foryou" not in result
    assert "#viral" not in result
    assert "#selfimprovement" in result
    assert "#mentalhealth" in result
    assert "#anicca" in result


def test_strip_tiktok_hashtags_case_insensitive():
    """Test: Hashtag stripping is case-insensitive."""
    caption = "Hello #FYP #Viral world"
    result = strip_tiktok_hashtags(caption)
    assert "#FYP" not in result
    assert "#Viral" not in result
    assert "Hello" in result
    assert "world" in result


def test_strip_tiktok_hashtags_preserves_clean():
    """Test: Caption without TikTok hashtags is unchanged."""
    caption = "This is a clean caption #mindfulness"
    result = strip_tiktok_hashtags(caption)
    assert result == "This is a clean caption #mindfulness"


# =============================================================================
# Scheduling Tests
# =============================================================================

def test_next_posting_slot():
    """Test: Next slot is calculated correctly for 9:00/21:00 JST."""
    # 15:00 JST (06:00 UTC) → next slot is 21:00 JST (12:00 UTC)
    now = datetime(2026, 2, 1, 6, 0, 0, tzinfo=UTC)
    slot = next_posting_slot(now, slot_index=0)
    expected = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC).isoformat()
    assert slot == expected


def test_next_posting_slot_morning():
    """Test: Early morning gets 9:00 JST slot."""
    # 01:00 JST (16:00 UTC prev day) → next slot is 09:00 JST (00:00 UTC)
    now = datetime(2026, 1, 31, 16, 0, 0, tzinfo=UTC)
    slot = next_posting_slot(now, slot_index=0)
    expected = datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC).isoformat()
    assert slot == expected


def test_next_posting_slot_after_all_slots():
    """Test: After 21:00 JST → next day 9:00 JST."""
    # 23:00 JST (14:00 UTC) → next is 09:00 JST tomorrow (00:00 UTC next day)
    now = datetime(2026, 2, 1, 14, 0, 0, tzinfo=UTC)
    slot = next_posting_slot(now, slot_index=0)
    expected = datetime(2026, 2, 2, 0, 0, 0, tzinfo=UTC).isoformat()
    assert slot == expected


def test_stagger_posting_slots():
    """Test: Multiple posts are staggered by 30 minutes."""
    now = datetime(2026, 2, 1, 6, 0, 0, tzinfo=UTC)  # 15:00 JST

    slot0 = next_posting_slot(now, slot_index=0)  # 21:00 JST
    slot1 = next_posting_slot(now, slot_index=1)  # 21:30 JST
    slot2 = next_posting_slot(now, slot_index=2)  # 22:00 JST

    t0 = datetime.fromisoformat(slot0)
    t1 = datetime.fromisoformat(slot1)
    t2 = datetime.fromisoformat(slot2)

    assert (t1 - t0).total_seconds() == 30 * 60
    assert (t2 - t1).total_seconds() == 30 * 60


# =============================================================================
# Account Mapping Tests
# =============================================================================

def test_account_mapping():
    """Test: EN and JP accounts are correctly mapped."""
    from config import ACCOUNT_MAPPING

    en = ACCOUNT_MAPPING["en"]
    assert en["tiktok_username"] == "anicca.en"
    assert en["ig_account_id"] == "28896"
    assert en["lang"] == "EN"
    assert "rss.app" in en["rss_url"]

    jp = ACCOUNT_MAPPING["jp"]
    assert jp["tiktok_username"] == "anicca.jp"
    assert jp["ig_account_id"] == "28897"
    assert jp["lang"] == "JP"


# =============================================================================
# Full Flow Test (E2E with mocks)
# =============================================================================

@patch("cross_post_tiktok_to_ig.upload_and_post_carousel")
@patch("cross_post_tiktok_to_ig.scrape_profile_slideshows")
@patch("cross_post_tiktok_to_ig.fetch_new_posts")
def test_full_cross_post_flow(mock_rss, mock_apify, mock_ig, tmp_path, monkeypatch):
    """Test: Full flow from RSS detection to Instagram posting."""
    # Setup state file in tmp
    state_file = tmp_path / "processed_ids.json"
    monkeypatch.setattr("state.STATE_FILE", state_file)
    monkeypatch.setattr("cross_post_tiktok_to_ig.load_processed_ids",
                        lambda: set())
    monkeypatch.setattr("cross_post_tiktok_to_ig.save_processed_id",
                        lambda x: None)

    # Mock RSS: 2 new posts
    mock_rss.return_value = [
        {"id": "url1", "title": "Post 1 #fyp #mindfulness", "link": "url1", "pub_date": "2026-02-01T06:00:00+00:00", "thumbnail": ""},
        {"id": "url2", "title": "Post 2 #selfcare", "link": "url2", "pub_date": "2026-02-01T07:00:00+00:00", "thumbnail": ""},
    ]

    # Mock Apify: url1 is slideshow, url2 is video
    mock_apify.return_value = {
        "url1": ["https://img1.jpg", "https://img2.jpg"],
    }

    # Mock Instagram poster
    mock_ig.return_value = {"postSubmissionId": "sub123"}

    config = {
        "rss_url": "https://rss.app/feeds/test.xml",
        "tiktok_username": "anicca.en",
        "ig_account_id": "28896",
        "lang": "EN",
    }

    now = datetime(2026, 2, 1, 6, 0, 0, tzinfo=UTC)
    stats = process_account("en", config, now)

    assert stats["detected"] == 2
    assert stats["posted"] == 1  # url1 (slideshow)
    assert stats["skipped"] == 1  # url2 (video, not in apify results)
    assert stats["errors"] == 0

    # Verify Instagram was called with stripped caption
    mock_ig.assert_called_once()
    call_kwargs = mock_ig.call_args.kwargs
    assert call_kwargs["account_id"] == "28896"
    assert "#fyp" not in call_kwargs["caption"]
    assert "#mindfulness" in call_kwargs["caption"]
    assert len(call_kwargs["image_urls"]) == 2
