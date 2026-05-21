from urllib.parse import urlparse


def sanitize_url(url: str) -> str:
    """Sanitize URL to scheme://host only."""
    if not url or not isinstance(url, str):
        return ""

    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ""
        if parsed.scheme not in ("http", "https"):
            return ""

        host = parsed.hostname
        if not host:
            return ""

        return f"{parsed.scheme}://{host}"
    except Exception:
        return ""
