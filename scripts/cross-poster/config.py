# DEPRECATED 2026-05-07: Blotato → Postiz migration (Daisuke direction).
# This file is a legacy stub not invoked by active cron. Env vars renamed
# (BLOTATO_* → POSTIZ_*). For new code use:
#   from postiz import PostizClient   # see anicca-project/.cursor/plans/ios/1.6.0/sns-poster/postiz.py
# Original backed up at <file>.bak.20260507-2030-pre-postiz.
"""
TikTok → Instagram Cross-Poster Configuration

Account mapping, RSS feeds, posting schedule.
"""
import os

# API Keys
POSTIZ_API_KEY = os.environ.get("POSTIZ_API_KEY", "")
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_METRICS_WEBHOOK_URL", "")

# Blotato API
POSTIZ_BASE_URL = "https://backend.blotato.com/v2"

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
REQUIRED_KEYS = ["POSTIZ_API_KEY", "APIFY_API_TOKEN"]


def validate_env(keys=None):
    """Validate required environment variables."""
    keys = keys or REQUIRED_KEYS
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
