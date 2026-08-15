#!/usr/bin/env python3
"""The reading half of the approval gate, checked without a browser."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import telegram_web_read as reader  # noqa: E402


def _target(**overrides):
    base = {
        "type": "page",
        "url": "https://web.telegram.org/k/",
        "webSocketDebuggerUrl": "ws://127.0.0.1:1/devtools/page/A",
    }
    base.update(overrides)
    return base


def test_shared_workers_are_not_pages():
    # 18 telegram targets were live and only 2 were pages; the rest cannot be evaluated in.
    targets = [_target(), {"type": "shared_worker", "url": "https://web.telegram.org/k/",
                           "webSocketDebuggerUrl": "ws://x"}]
    assert reader.logged_in_targets(targets) == [_target()]


def test_target_without_websocket_is_dropped():
    assert reader.logged_in_targets([_target(webSocketDebuggerUrl=None)]) == []


def test_foreign_origin_is_dropped():
    assert reader.logged_in_targets([_target(url="https://example.com/")]) == []


def test_row_script_quotes_the_title():
    # A title carrying a quote must not end the JS string literal.
    script = reader.chat_row_script('Life"Bot')
    assert '"Life\\"Bot"' in script


def test_outgoing_bubbles_belong_to_the_owner():
    # The browser is logged in as Dais, so is-out is Dais -- not the loop.
    payload = json.dumps({"bubbles": [
        {"outgoing": True, "text": "/panel core8d"},
        {"outgoing": False, "text": "パネルを開きました"},
    ]})
    rows = reader.parse_bubbles(payload)
    assert rows == [
        {"from": "dais", "text": "/panel core8d"},
        {"from": "peer", "text": "パネルを開きました"},
    ]


def test_service_bubbles_are_dropped():
    payload = {"bubbles": [{"outgoing": False, "text": "   "}, {"outgoing": True, "text": "OK"}]}
    assert reader.parse_bubbles(payload) == [{"from": "dais", "text": "OK"}]


def test_unparseable_payload_reads_as_nothing():
    assert reader.parse_bubbles("not json") == []
    assert reader.parse_bubbles(None) == []


def test_authorship_survives_the_round_trip():
    """Who said it is the only thing this reader has to get right.

    Nothing downstream asks Dais for permission -- the loop earns without a human in it,
    and check_draft already refuses the drafts that break platform rules. What reading is
    for is the opposite direction: catching an instruction Dais typed unprompted. That is
    only usable if the loop can tell his words from its own.
    """
    payload = json.dumps({"bubbles": [
        {"outgoing": False, "text": "レポート: 応募 4 件"},
        {"outgoing": True, "text": "109613284 のスレッドは止めて"},
    ]})
    assert reader.parse_bubbles(payload) == [
        {"from": reader.PEER, "text": "レポート: 応募 4 件"},
        {"from": reader.OWNER, "text": "109613284 のスレッドは止めて"},
    ]
