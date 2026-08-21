"""Shared parser for the rendered X Article shell-title identity contract."""

from __future__ import annotations

import re
from typing import Any


_TCO_URL = re.compile(r"https://t\.co/[A-Za-z0-9]+", re.IGNORECASE)
_HTTP_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_SHELL_TITLE = re.compile(
    r"^(.*?)([「『“\"']?)(https://t\.co/[A-Za-z0-9]+)([」』”\"']?)\s*/\s*X$",
    re.IGNORECASE | re.DOTALL,
)
_QUOTE_PAIRS = {
    "「": "」",
    "『": "』",
    "“": "”",
    '"': '"',
    "'": "'",
}


def is_link_only_x_article_shell_title(value: Any) -> bool:
    """Return whether an X shell title contains exactly one standalone t.co URL.

    X may prefix the quoted URL with a localized user label. That prefix must be
    only a label ending in a colon; it cannot contain any URL. The payload before
    ``/ X`` is one t.co URL, optionally wrapped in a matched quote pair, with no
    adjacent URL token or trailing text.
    """

    if not isinstance(value, str):
        return False
    title = value.strip()
    if len(_TCO_URL.findall(title)) != 1:
        return False
    match = _SHELL_TITLE.fullmatch(title)
    if match is None:
        return False

    prefix, opening, url, closing = match.groups()
    if prefix and re.fullmatch(r".*?[：:]\s*", prefix, re.DOTALL) is None:
        return False
    if _HTTP_URL.search(prefix):
        return False
    if opening:
        if not closing or _QUOTE_PAIRS.get(opening) != closing:
            return False
    elif closing:
        return False
    return _TCO_URL.fullmatch(url) is not None
