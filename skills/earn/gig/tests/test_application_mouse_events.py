from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("application_parent", SCRIPTS / "application_parent.py")
assert SPEC and SPEC.loader
application_parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(application_parent)


class _Connection:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *_args):
        return None


def _run_submit_click(tmp_path, monkeypatch, *, confirm_modal: bool) -> list[dict[str, object]]:
    request_id = "123"
    expected_url = f"https://coconala.com/offers/add/{request_id}"
    states = iter([
        {"url": expected_url, "button": {"x": 10, "y": 20}},
        *([{"modal": True, "button": {"x": 30, "y": 40}}] if confirm_modal else []),
        {"url": expected_url, "body": ""},
    ])
    events: list[dict[str, object]] = []
    effects = application_parent.CdpParentEffects(
        ws_url="ws://example.invalid/devtools/page/1",
        evidence_dir=tmp_path,
        ledger_path=tmp_path / "ledger.jsonl",
        pass_id="test-pass",
    )

    async def call(_ws, method, params, _call_id):
        if method == "Input.dispatchMouseEvent":
            events.append(params)
        return {}

    async def evaluate(_ws, _expression, call_id):
        return next(states), call_id + 1

    async def screenshot(_ws, call_id):
        return b"png", call_id + 1

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(application_parent.websockets, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(effects, "_call", call)
    monkeypatch.setattr(effects, "_eval_json", evaluate)
    monkeypatch.setattr(effects, "_screenshot", screenshot)
    monkeypatch.setattr(application_parent.asyncio, "sleep", no_sleep)

    asyncio.run(effects._click_button_async(request_id, "応募する", confirm_modal=confirm_modal))
    return events


def test_submit_click_dispatches_complete_left_button_sequence(tmp_path, monkeypatch):
    events = _run_submit_click(tmp_path, monkeypatch, confirm_modal=False)

    assert events == [
        {"type": "mouseMoved", "x": 10.0, "y": 20.0, "button": "none", "buttons": 0, "clickCount": 0},
        {"type": "mousePressed", "x": 10.0, "y": 20.0, "button": "left", "buttons": 1, "clickCount": 1},
        {"type": "mouseReleased", "x": 10.0, "y": 20.0, "button": "left", "buttons": 0, "clickCount": 1},
    ]


def test_terms_modal_dispatches_the_same_complete_left_button_sequence(tmp_path, monkeypatch):
    events = _run_submit_click(tmp_path, monkeypatch, confirm_modal=True)

    assert events == [
        {"type": "mouseMoved", "x": 10.0, "y": 20.0, "button": "none", "buttons": 0, "clickCount": 0},
        {"type": "mousePressed", "x": 10.0, "y": 20.0, "button": "left", "buttons": 1, "clickCount": 1},
        {"type": "mouseReleased", "x": 10.0, "y": 20.0, "button": "left", "buttons": 0, "clickCount": 1},
        {"type": "mouseMoved", "x": 30.0, "y": 40.0, "button": "none", "buttons": 0, "clickCount": 0},
        {"type": "mousePressed", "x": 30.0, "y": 40.0, "button": "left", "buttons": 1, "clickCount": 1},
        {"type": "mouseReleased", "x": 30.0, "y": 40.0, "button": "left", "buttons": 0, "clickCount": 1},
    ]
