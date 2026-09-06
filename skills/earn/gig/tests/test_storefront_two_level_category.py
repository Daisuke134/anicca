"""Coconala's category form only has a third (type) level for some sub categories.

Production evidence: `storefront_category_type_absent:813:...` fired repeatedly (813 x4, 361 x2)
and killed the wake, while `category-child-agent` evidence for other sub values shows the model
fabricating a type_value (`0` seven times, plus `686`, `000000`, `00000000`, `231`) because it was
never given a real option list -- one rationale literally says
「公式カテゴリタイプの候補は提供されていないため」. The failing observation is always
`data[Service][master_category_type_id]:1D` -- one valueless placeholder option, select disabled.

An earlier fix inferred "no type options yet" as "this category has no third level" and returned
early with the type left unset. That was wrong for a genuinely three-level category still
hydrating: every publication was rejected with 「カテゴリタイプを正しく選択してください」. Commit
3f5b4848e replaced that early return with the wait-then-raise this file guards.

The fix: only DISABLED-and-empty, observed after the full wait, may be read as "no third level".
ENABLED-and-empty must keep raising, exactly as before the fix.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_two_level_category.py
"""
from __future__ import annotations

import asyncio as real_asyncio
import json
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import storefront_draft as sdraft  # noqa: E402
import storefront_direct as direct  # noqa: E402


MASTER = "11"
SUB = "813"


# ---------------------------------------------------------------------------
# Harness: fake CDP transport for `_read_category_children_async`.
#
# `_call`/`_evaluate` are plain module functions called by name from
# `_read_category_children_async` and `_wait_for_option`, so patching them on the module
# intercepts every browser round trip without simulating the websocket wire format. The
# function's own polling loop reads real wall-clock time via `asyncio.get_running_loop().time()`,
# so `asyncio` is also replaced with a fake clock driven by `sleep()` -- otherwise a full-wait
# scenario would cost 12 real seconds per test.
# ---------------------------------------------------------------------------


class _FakeLoop:
    def __init__(self) -> None:
        self.t = 0.0

    def time(self) -> float:
        return self.t


class _FakeAsyncio:
    def __init__(self) -> None:
        self.loop = _FakeLoop()

    def get_running_loop(self):
        return self.loop

    async def sleep(self, seconds: float) -> None:
        self.loop.t += seconds
        await real_asyncio.sleep(0)


def _install_fake_transport(monkeypatch, evaluate):
    async def fake_call(_ws, _method, _params, cid):
        return {}

    async def fake_evaluate(_ws, expression, cid):
        return evaluate(expression), cid + 1

    class _FakeConn:
        async def __aenter__(self):
            return "fake-ws"

        async def __aexit__(self, *_args):
            return False

    fake_websockets = types.SimpleNamespace(connect=lambda *_a, **_k: _FakeConn())
    monkeypatch.setitem(sys.modules, "websockets", fake_websockets)
    monkeypatch.setattr(sdraft, "_call", fake_call)
    monkeypatch.setattr(sdraft, "_evaluate", fake_evaluate)
    monkeypatch.setattr(sdraft, "asyncio", _FakeAsyncio())


def _children_payload(sub_options, type_options):
    return json.dumps({
        "data[Service][master_sub_category]": sub_options,
        "data[Service][master_category_type_id]": type_options,
    })


def _make_evaluate(*, type_polls):
    """`type_polls` is consumed once per loop iteration: (type_options, type_disabled)."""
    state = {"poll": 0}

    def evaluate(expression: str):
        if "master_category]" in expression and ".some(o=>o.value===" in expression:
            return True  # master option present
        if "master_category]" in expression and "s.value=" in expression:
            return True  # master applied
        if "master_sub_category]" in expression and ".some(o=>o.value===" in expression:
            return True  # sub option present
        if "master_sub_category]" in expression and "s.value=" in expression:
            return True  # sub applied
        if "Object.fromEntries" in expression:
            idx = min(state["poll"], len(type_polls) - 1)
            type_options, _disabled = type_polls[idx]
            state["poll"] += 1
            return _children_payload([{"value": SUB, "label": "sub"}], type_options)
        if "master_category_type_id" in expression and "!!s.disabled" in expression:
            idx = min(state["poll"] - 1, len(type_polls) - 1)
            idx = max(idx, 0)
            return type_polls[idx][1]
        if "querySelectorAll('select')" in expression:
            return "data[Service][master_category_type_id]:1D"
        raise AssertionError(f"unexpected expression: {expression}")

    return evaluate


def _read_children(monkeypatch, type_polls):
    _install_fake_transport(monkeypatch, _make_evaluate(type_polls=type_polls))
    return real_asyncio.run(
        sdraft._read_category_children_async("ws://fake", MASTER, SUB)
    )


# ---------------------------------------------------------------------------
# (1) Disabled + empty, observed after the wait -> reported, not raised.
# ---------------------------------------------------------------------------


def test_disabled_and_empty_after_the_wait_returns_absence_marker(monkeypatch):
    # Every poll during the 12s wait sees zero valued options and a disabled select --
    # this is Coconala's own way of saying "not applicable" (same as fix_limit/proposal_limit).
    children = _read_children(monkeypatch, type_polls=[([], True)])
    assert children["data[Service][master_category_type_id]"] == []
    assert children["master_category_type_absent"] is True
    assert children["data[Service][master_sub_category]"] == [{"value": SUB, "label": "sub"}]


# ---------------------------------------------------------------------------
# (2) Enabled + empty -> keep raising (the past-bug guard).
# ---------------------------------------------------------------------------


def test_enabled_and_empty_still_raises_type_absent(monkeypatch):
    children = [([], False)]  # never disabled, never populated
    with pytest.raises(RuntimeError, match=f"storefront_category_type_absent:{SUB}:"):
        _read_children(monkeypatch, type_polls=children)


# ---------------------------------------------------------------------------
# (3) Select missing entirely -> keep raising.
# ---------------------------------------------------------------------------


def test_type_select_missing_entirely_still_raises(monkeypatch):
    def evaluate(expression: str):
        if "master_category]" in expression and ".some(o=>o.value===" in expression:
            return True
        if "master_category]" in expression and "s.value=" in expression:
            return True
        if "master_sub_category]" in expression and ".some(o=>o.value===" in expression:
            return True
        if "master_sub_category]" in expression and "s.value=" in expression:
            return True
        if "Object.fromEntries" in expression:
            # The type <select> does not exist on this rendered form at all.
            return json.dumps({
                "data[Service][master_sub_category]": [{"value": SUB, "label": "sub"}],
                "data[Service][master_category_type_id]": [],
            })
        if "master_category_type_id" in expression and "!!s.disabled" in expression:
            return False  # `!!s` is false when the element is missing
        if "querySelectorAll('select')" in expression:
            return "data[Service][master_sub_category]:2"
        raise AssertionError(f"unexpected expression: {expression}")

    _install_fake_transport(monkeypatch, evaluate)
    with pytest.raises(RuntimeError, match=f"storefront_category_type_absent:{SUB}:"):
        real_asyncio.run(sdraft._read_category_children_async("ws://fake", MASTER, SUB))


# ---------------------------------------------------------------------------
# (4) Enabled and populated -> normal shape, no absence marker.
# ---------------------------------------------------------------------------


def test_enabled_and_populated_returns_options_without_absence_marker(monkeypatch):
    populated = [{"value": "2274", "label": "type"}]
    children = _read_children(monkeypatch, type_polls=[(populated, False)])
    assert children["data[Service][master_category_type_id]"] == populated
    assert "master_category_type_absent" not in children


# ---------------------------------------------------------------------------
# (5) The absence marker propagates: category["type"] becomes None and the writer skips it.
# ---------------------------------------------------------------------------


def test_absent_type_makes_writer_skip_the_type_field():
    fields = {"overview_input": "o", "catchphrase": "c", "head": "h",
              "price_option_value": "3300", "delivery_days": 5, "order_limit": 1, "body": "b"}
    three_level = {"public_fields": fields, "category": {
        "master": {"value": MASTER}, "sub": {"value": SUB}, "type": {"value": "2274"}}}
    two_level = {"public_fields": fields, "category": {
        "master": {"value": MASTER}, "sub": {"value": SUB}, "type": None}}
    assert "data[Service][master_category_type_id]" in sdraft._expected_values(three_level)
    assert "data[Service][master_category_type_id]" not in sdraft._expected_values(two_level)


# ---------------------------------------------------------------------------
# (6) Schema accepts type_value: null and still rejects a non-numeric string.
# ---------------------------------------------------------------------------


def test_schema_accepts_null_type_value_and_rejects_non_numeric():
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (SCRIPTS.parent / "schemas" / "storefront_category_child.schema.json").read_text(
            encoding="utf-8"))
    validator = Draft202012Validator(schema)

    ok = {"sub_value": "813", "type_value": None, "rationale": "no third level offered"}
    assert not list(validator.iter_errors(ok))

    still_required = {"sub_value": "813", "rationale": "missing type_value key entirely"}
    assert list(validator.iter_errors(still_required))

    bad = {"sub_value": "813", "type_value": "abc", "rationale": "not numeric"}
    assert list(validator.iter_errors(bad))

    numeric = {"sub_value": "813", "type_value": "2274", "rationale": "still accepted"}
    assert not list(validator.iter_errors(numeric))


# ---------------------------------------------------------------------------
# (7) `_validate_category_choice` is unchanged for an empty list.
# ---------------------------------------------------------------------------


def test_validate_category_choice_still_raises_on_empty_options():
    with pytest.raises(RuntimeError, match="storefront_category_options_unobserved:type"):
        direct._validate_category_choice("2274", [], "type")
