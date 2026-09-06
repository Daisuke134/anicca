"""An empty shelf and a login wall must not report the same reason.

`observe_storefront` returns a parsed count and no url, so a session that has expired
reaches the caller as a shelf with nothing on it. Called "empty", it produced 241 wakes over
seven hours that read a login page and reported `official_inventory_empty_or_invalid`, so
nothing ever tried to log back in. The Apply lane, which names this failure, recovered on
its own next wake. The difference was the name, not the code around it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import storefront_direct as direct  # noqa: E402


@pytest.fixture
def page(monkeypatch):
    import listing_inventory

    def install(payload=None, raises=None):
        async def fake(ws_url, url, expression):
            if raises is not None:
                raise raises
            return payload
        monkeypatch.setattr(listing_inventory, "_eval_json", fake)
    return install


def test_the_login_page_is_recognised_by_its_url(page):
    page({"url": "https://coconala.com/login", "body": ""})
    assert direct._dashboard_says_signed_out("ws://x") is True


@pytest.mark.parametrize("body", ["メールアドレスでログインする", "会員登録はこちら"])
def test_the_login_page_is_recognised_by_its_own_words(page, body):
    # Coconala can serve the wall without moving the url, so the url alone is not enough.
    page({"url": "https://coconala.com/mypage/services_lists", "body": body})
    assert direct._dashboard_says_signed_out("ws://x") is True


def test_a_real_seller_page_is_not_called_signed_out(page):
    page({"url": "https://coconala.com/mypage/services_lists",
          "body": "現在の総出品数 15件\n公開 15"})
    assert direct._dashboard_says_signed_out("ws://x") is False


def test_a_browser_hiccup_is_never_mistaken_for_a_dead_session(page):
    page(raises=RuntimeError("server rejected WebSocket connection: HTTP 500"))
    assert direct._dashboard_says_signed_out("ws://x") is False


def test_the_reader_asks_before_calling_the_shelf_empty():
    source = (SCRIPTS / "storefront_direct.py").read_text(encoding="utf-8")
    block = source[source.index("def _read_official_catalog"):]
    block = block[:block.index("raise RuntimeError(failure)")]
    assert "_dashboard_says_signed_out" in block
    assert "storefront_session_expired" in block
    # A dead session is not a transient: it must stop retrying, not burn five attempts.
    assert "break" in block[block.index("_dashboard_says_signed_out"):]
