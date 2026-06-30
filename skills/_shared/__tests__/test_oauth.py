"""PROP-A-oauth (required:true, Tier 0) — anchored OAuth URL extraction, anti-phishing.

Spec: behavioral-spec.md REQ-A3 + regex `^https://claude\\.com/cai/oauth/authorize\\?[a-z0-9_=&%+\\.\\-]+$`.
Closes FIND-005 phishing.
"""
import pytest

from lib.healthcheck import extract_oauth_url  # FAIL until 2b


# ── happy paths ────────────────────────────────────────────────────────
def test_extracts_canonical_oauth_url():
    pane = (
        "Browser didn't open? Use the url below to sign in (c to copy)\n"
        "https://claude.com/cai/oauth/authorize?code=true&client_id=9d1c250a-e61b-44d9-88ed-5944d1962f5e"
        "&response_type=code&redirect_uri=https%3A%2F%2Fplatform.claude.com%2Foauth%2Fcode%2Fcallback"
        "&scope=org%3Acreate_api_key+user%3Aprofile\n"
        "Paste code here if prompted >"
    )
    url = extract_oauth_url(pane)
    assert url is not None
    assert url.startswith("https://claude.com/cai/oauth/authorize?")


# ── phishing rejections (FIND-005 attack corpus) ──────────────────────
@pytest.mark.parametrize(
    "evil",
    [
        # subdomain look-alike
        "https://claude.com.evil.tld/cai/oauth/authorize?code=x",
        # homograph (Cyrillic 'а')
        "https://clаude.com/cai/oauth/authorize?code=x",
        # javascript scheme
        "javascript:alert(1)//https://claude.com/cai/oauth/authorize?code=x",
        # data scheme
        "data:text/html,<script>...</script>",
        # http (not https)
        "http://claude.com/cai/oauth/authorize?code=x",
        # path traversal in query
        "https://claude.com/cai/oauth/authorize?code=../../etc/passwd",
        # extra path segment after authorize
        "https://claude.com/cai/oauth/authorize/extra?code=x",
        # IP literal
        "https://192.0.2.1/cai/oauth/authorize?code=x",
    ],
)
def test_rejects_phishing_lookalikes(evil):
    pane = f"Click here: {evil}\nMore text"
    assert extract_oauth_url(pane) is None


# ── boundary ──────────────────────────────────────────────────────────
def test_empty_pane_returns_none():
    assert extract_oauth_url("") is None


def test_pane_without_url_returns_none():
    assert extract_oauth_url("Logged in successfully. Press Enter.") is None


def test_only_returns_a_string_https_claude_com_host():
    """Non-empty https URL alone is not enough — host must be exactly claude.com."""
    pane = "Try https://api.anthropic.com/something"
    assert extract_oauth_url(pane) is None
