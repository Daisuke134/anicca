from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observer.url_sanitizer import sanitize_url


class TestSanitizeUrl:
    """Tests for URL sanitization (High 8)."""

    def test_removes_path(self):
        """Path should be stripped."""
        result = sanitize_url("https://github.com/user/repo")
        assert result == "https://github.com"

    def test_removes_query_string(self):
        """Query params (may contain tokens) should be stripped."""
        result = sanitize_url("https://example.com/page?token=secret&user=me")
        assert result == "https://example.com"

    def test_removes_fragment(self):
        """Fragment should be stripped."""
        result = sanitize_url("https://docs.python.org/3/library#section")
        assert result == "https://docs.python.org"

    def test_removes_credentials(self):
        """Username:password should be stripped."""
        result = sanitize_url("https://user:password@example.com/path")
        assert result == "https://example.com"

    def test_removes_port(self):
        """Port number should be stripped."""
        result = sanitize_url("https://localhost:8080/api")
        assert result == "https://localhost"

    def test_preserves_scheme_http(self):
        """HTTP scheme should be preserved."""
        result = sanitize_url("http://example.com/path")
        assert result == "http://example.com"

    def test_preserves_scheme_https(self):
        """HTTPS scheme should be preserved."""
        result = sanitize_url("https://secure.example.com")
        assert result == "https://secure.example.com"

    def test_rejects_non_http_schemes(self):
        """Non-HTTP schemes should return empty."""
        assert sanitize_url("ftp://files.example.com") == ""
        assert sanitize_url("file:///etc/passwd") == ""
        assert sanitize_url("javascript:alert(1)") == ""

    def test_rejects_invalid_urls(self):
        """Invalid URLs should return empty."""
        assert sanitize_url("not-a-url") == ""
        assert sanitize_url("://missing-scheme.com") == ""
        assert sanitize_url("") == ""
        assert sanitize_url(None) == ""

    def test_handles_subdomains(self):
        """Subdomains should be preserved."""
        result = sanitize_url("https://api.github.com/users/octocat")
        assert result == "https://api.github.com"

    def test_oauth_code_stripped(self):
        """OAuth redirect URLs with codes should be sanitized."""
        url = "https://app.example.com/callback?code=abc123&state=xyz"
        result = sanitize_url(url)
        assert result == "https://app.example.com"
        assert "code=" not in result
        assert "abc123" not in result
