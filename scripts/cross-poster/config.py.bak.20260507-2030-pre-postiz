"""
TikTok → Instagram Cross-Poster Configuration

Account mapping, RSS feeds, posting schedule.
"""
import os

# API Keys
BLOTATO_API_KEY = os.environ.get("BLOTATO_API_KEY", "")
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_METRICS_WEBHOOK_URL", "")

# Blotato API
BLOTATO_BASE_URL = "https://backend.blotato.com/v2"

# Account mapping: RSS feed → TikTok profile → Instagram account
# RSS feeds monitor ReelFarm-managed TikTok accounts
# Instagram accounts are connected in Blotato
ACCOUNT_MAPPING = {
    "en": {
        "tiktok_username": "anicca.en",
        "ig_account_id": "28896",  # @anicca.ai (Instagram)
        "lang": "EN",
    },
    "jp": {
        "tiktok_username": "anicca.jp",
        "ig_account_id": "28897",  # @anicca.japan (Instagram)
        "lang": "JP",
    },
}

# Posting schedule (JST hours)
POSTING_SLOTS_JST = [9, 21]
STAGGER_MINUTES = 30

# Apify
APIFY_ACTOR_ID = "clockworks~tiktok-scraper"
APIFY_RESULTS_PER_PAGE = 10

# Lookback window (hours) - slightly more than cron interval for safety
LOOKBACK_HOURS = 14

# TikTok-specific hashtags to strip from Instagram captions
TIKTOK_ONLY_HASHTAGS = {
    "#fyp", "#foryou", "#foryoupage", "#tiktok", "#viral",
    "#xyzbca", "#trending", "#blowthisup", "#tiktokviral",
}

# Startup validation
REQUIRED_KEYS = ["BLOTATO_API_KEY", "APIFY_API_TOKEN"]


def validate_env(keys=None):
    """Validate required environment variables."""
    keys = keys or REQUIRED_KEYS
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
