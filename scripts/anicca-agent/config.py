# DEPRECATED 2026-05-07: Blotato → Postiz migration (Daisuke direction).
# This file is a legacy stub not invoked by active cron. Env vars renamed
# (BLOTATO_* → POSTIZ_*). For new code use:
#   from postiz import PostizClient   # see anicca-project/.cursor/plans/ios/1.6.0/sns-poster/postiz.py
# Original backed up at <file>.bak.20260507-2030-pre-postiz.
"""
Anicca TikTok Agent Configuration
"""
import os

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
POSTIZ_API_KEY = os.environ.get("POSTIZ_API_KEY", "")
FAL_API_KEY = os.environ.get("FAL_API_KEY", "")
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")

# Backend API
API_BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")
API_AUTH_TOKEN = os.environ.get("API_AUTH_TOKEN", "")

# Blotato
POSTIZ_BASE_URL = "https://backend.blotato.com/v2"
TIKTOK_ACCOUNT_ID = os.environ.get("TIKTOK_ACCOUNT_ID", "28152")  # @anicca.self

# Fal.ai
FAL_BASE_URL = "https://queue.fal.run"

# Agent settings
MODEL = "gpt-4o"
MAX_RETRIES = 2
IMAGE_QUALITY_THRESHOLD = 6  # minimum score to post (1-10)

# Startup validation (called by each script with its required keys)
ALL_AGENT_KEYS = ["OPENAI_API_KEY", "POSTIZ_API_KEY", "FAL_API_KEY", "EXA_API_KEY", "API_BASE_URL", "API_AUTH_TOKEN"]
API_ONLY_KEYS = ["API_BASE_URL", "API_AUTH_TOKEN"]


def validate_env(keys):
    """Validate required environment variables. Raises EnvironmentError if any are missing."""
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
