"""
Anicca X Agent Configuration
"""
import os

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
BLOTATO_API_KEY = os.environ.get("BLOTATO_API_KEY", "")
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")

# Backend API
API_BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")
API_AUTH_TOKEN = os.environ.get("API_AUTH_TOKEN", "")

# Blotato
BLOTATO_BASE_URL = "https://backend.blotato.com/v2"
# X/Twitter account — uses same Blotato platform but different account
X_ACCOUNT_ID = os.environ.get("X_ACCOUNT_ID", "")

# Agent settings
MODEL = "gpt-4o"
MAX_POSTS_PER_RUN = 1  # one post per slot (morning/evening)

REQUIRED_KEYS = ["BLOTATO_API_KEY", "API_BASE_URL", "API_AUTH_TOKEN", "X_ACCOUNT_ID"]


def validate_env(required_keys=None):
    """Validate required environment variables."""
    keys = required_keys or REQUIRED_KEYS
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
