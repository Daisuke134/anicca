from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


# The application lane's real blocker, visible for the first time on 2026-08-05 after B2-2
# stopped discarding error text: TimeoutError at application_parent.py:384, twice in a row.
#
# Line 384 is `await asyncio.wait_for(ws.recv(), timeout=30)` inside _call — a CDP request
# went to the browser and nothing came back for thirty seconds. asyncio's TimeoutError
# carries no message, which is exactly why it used to arrive as error:"".
#
# Naming the type was not enough. Every CDP call in this file goes through _call, so
# "TimeoutError" still does not say whether the tab hung on a navigate, an evaluate, or a
# screenshot — and those have different causes. The loop already knows: a domain-skill entry
# records that Page.navigate from a filled composer stops the renderer and takes CDP down
# with it. The error has to carry the method for that knowledge to be usable.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "application_parent.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("application_parent", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SilentSocket:
    """A CDP peer that accepts the request and never answers."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, payload: str) -> None:
        self.sent.append(payload)

    async def recv(self) -> str:
        await asyncio.sleep(3600)
        raise AssertionError("unreachable")


class WrongIdSocket(SilentSocket):
    """Answers, but always for a different call id — the loop keeps waiting."""

    async def recv(self) -> str:
        return '{"id": 999999, "result": {}}'


def call(module, ws, method: str, timeout: float):
    parent = object.__new__(module.CdpParentEffects)
    return asyncio.run(parent._call(ws, method, {}, 1, timeout_seconds=timeout))


def test_a_timeout_names_the_method_that_hung() -> None:
    m = load_module()
    with pytest.raises(m.ParentContractError) as caught:
        call(m, SilentSocket(), "Page.navigate", 0.05)
    assert "Page.navigate" in str(caught.value)


def test_the_error_says_it_was_a_timeout_not_something_else() -> None:
    m = load_module()
    with pytest.raises(m.ParentContractError) as caught:
        call(m, SilentSocket(), "Runtime.evaluate", 0.05)
    assert "timeout" in str(caught.value).lower()


def test_the_waited_seconds_are_stated() -> None:
    # 30s of silence and 2s of silence are different problems.
    m = load_module()
    with pytest.raises(m.ParentContractError) as caught:
        call(m, SilentSocket(), "Page.captureScreenshot", 0.05)
    assert "0.05" in str(caught.value)


def test_answers_for_another_call_still_time_out_by_name() -> None:
    # The loop skips responses whose id does not match, so a chatty-but-wrong peer looks
    # identical to a silent one from the outside.
    m = load_module()
    with pytest.raises(m.ParentContractError) as caught:
        call(m, WrongIdSocket(), "Target.activateTarget", 0.05)
    assert "Target.activateTarget" in str(caught.value)


def test_a_normal_answer_still_returns_the_result() -> None:
    class Answering(SilentSocket):
        async def recv(self) -> str:
            return '{"id": 1, "result": {"ok": true}}'

    m = load_module()
    assert call(m, Answering(), "Page.enable", 1.0) == {"ok": True}
