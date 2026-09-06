"""The seller form gets the same settling window as every other transient in this loop.

`_seller_snapshot_for` waited three attempts one second apart -- two seconds of settling,
the shortest window anywhere in this loop, and the one production exhausted with
`seller_form_not_fully_hydrated`. Every other reader of a transient browser condition here
waits five attempts three seconds apart. These checks hold that shape, and hold the one
condition that must never be retried: being signed out is not a transient.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import storefront_direct as direct  # noqa: E402

URL = "https://coconala.com/mypage/services/4330368"
HYDRATED = {
    "url": URL,
    "fields": [{"name": "data[Service][overview]"}, {"name": "data[Service][head]"},
               {"name": "data[Service][price]"}],
}
EMPTY = {"url": URL, "fields": []}


@pytest.fixture
def reads(monkeypatch):
    calls, sleeps = [], []
    monkeypatch.setattr(direct.time, "sleep", lambda seconds: sleeps.append(seconds))

    def install(payloads):
        queue = list(payloads)

        def fake_eval(ws_url, url, expression):
            calls.append(url)
            return queue.pop(0) if queue else EMPTY

        monkeypatch.setattr(direct.asyncio, "run", lambda coro: coro)
        monkeypatch.setattr(
            sys.modules.setdefault("listing_inventory", __import__("listing_inventory")),
            "_eval_json", fake_eval)
    return install, calls, sleeps


def test_a_form_that_hydrates_late_is_still_read(reads):
    install, calls, sleeps = reads
    install([EMPTY, EMPTY, EMPTY, HYDRATED])
    assert direct._seller_snapshot_for("ws://x", "4330368") == HYDRATED
    assert len(calls) == 4
    assert sleeps == [3, 3, 3]


def test_five_attempts_three_seconds_apart_before_giving_up(reads):
    install, calls, sleeps = reads
    install([EMPTY] * 5)
    with pytest.raises(RuntimeError, match="seller_form_not_fully_hydrated"):
        direct._seller_snapshot_for("ws://x", "4330368")
    assert len(calls) == 5
    assert sleeps == [3, 3, 3, 3]


def test_a_hydrated_form_is_returned_without_sleeping(reads):
    install, calls, sleeps = reads
    install([HYDRATED])
    assert direct._seller_snapshot_for("ws://x", "4330368") == HYDRATED
    assert len(calls) == 1
    assert sleeps == []


def test_being_signed_out_is_named_and_never_retried(reads):
    install, calls, sleeps = reads
    install([{"url": "https://coconala.com/login", "fields": []}])
    with pytest.raises(RuntimeError, match="storefront_session_expired"):
        direct._seller_snapshot_for("ws://x", "4330368")
    assert len(calls) == 1
    assert sleeps == []
