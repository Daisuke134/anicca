"""The conditional post-submit terms modal must be clicked through, never fought.

Measured 2026-08-10 (gig-pass-1786284005-38359, 96000004-submit-attempt.png): after our
submit click Coconala conditionally shows a terms-confirmation modal -- title
投稿前にご確認ください, ToS bullets, and a green 応募する button. The old flow never
clicked it: the retry loop kept matching the form's identical 応募する UNDER the overlay
and clicking the backdrop, so the application never reached the server, the exact-id
readback correctly said absent, and the candidate ate an own-action wedge strike
(96000004 / 96000000 ¥80k / 96000001 / 96000003, two passes in a row) while modal-free
submits (96000002, 96000005) succeeded in the same passes.
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "application_parent.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("application_parent_submit_modal", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FORM_URL = "https://coconala.com/offers/add/96000004"
APPLIED_URL = "https://coconala.com/mypage/job_matching/applied/offers"


class SubmitSocket:
    """Drives _click_button_async end to end: button search, clicks, modal probe, settle.

    scenario:
      "none"              -- no modal; first click lands the submit (the 96000002 path)
      "modal"             -- first click opens the terms modal; its confirm click lands
      "modal_unclickable" -- modal opens but its button never becomes clickable
    """

    def __init__(self, scenario: str):
        self.scenario = scenario
        self.releases = 0
        self.modal_open = False
        self.landed = False
        self.pending: list[str] = []

    def _page(self) -> dict[str, object]:
        return {
            "url": APPLIED_URL if self.landed else FORM_URL,
            "body": "応募・スカウト管理" if self.landed else "応募内容を確認する",
        }

    async def send(self, raw: str) -> None:
        request = json.loads(raw)
        request_id = request["id"]
        method = request["method"]
        if method == "Input.dispatchMouseEvent":
            if request["params"]["type"] == "mouseReleased":
                self.releases += 1
                if self.releases == 1:
                    if self.scenario == "none":
                        self.landed = True
                    else:
                        self.modal_open = True
                elif self.releases == 2 and self.modal_open:
                    self.modal_open = False
                    self.landed = True
            self.pending.append(json.dumps({"id": request_id, "result": {}}))
            return
        if method == "Runtime.evaluate":
            expression = str(request.get("params", {}).get("expression") or "")
            if "投稿前にご確認ください" in expression:
                if self.modal_open:
                    button = None if self.scenario == "modal_unclickable" else {"x": 640, "y": 480}
                    value = json.dumps({"modal": True, "button": button, **self._page()}, ensure_ascii=False)
                else:
                    value = json.dumps({"modal": False, **self._page()}, ensure_ascii=False)
            elif "controls.map(describe)" in expression:
                value = json.dumps({
                    "url": FORM_URL,
                    "button": {"x": 320, "y": 420, "tag": "button", "label": "応募する", "role": None, "href": None},
                }, ensure_ascii=False)
            else:  # the settle read: url + body tail
                value = json.dumps(self._page(), ensure_ascii=False)
            self.pending.append(json.dumps({"id": request_id, "result": {"result": {"value": value}}}))
            return
        if method == "Page.captureScreenshot":
            self.pending.append(json.dumps({
                "id": request_id,
                "result": {"data": base64.b64encode(b"png").decode("ascii")},
            }))
            return
        self.pending.append(json.dumps({"id": request_id, "result": {}}))

    async def recv(self) -> str:
        return self.pending.pop(0)


class FakeConnection:
    def __init__(self, socket: SubmitSocket):
        self.socket = socket

    async def __aenter__(self) -> SubmitSocket:
        return self.socket

    async def __aexit__(self, *_: object) -> None:
        return None


def _effects(parent, tmp_path: Path):
    return parent.CdpParentEffects(
        ws_url="ws://127.0.0.1:9223/devtools/page/submit-modal-test",
        evidence_dir=tmp_path,
        ledger_path=tmp_path / "applied.jsonl",
        pass_id="modal-test",
    )


def test_the_terms_modal_is_confirmed_and_the_submit_still_lands(tmp_path: Path) -> None:
    parent = load_module()
    assert "e=>visible(e)&&e.children.length===0" in parent.CdpParentEffects._TERMS_MODAL_JS
    assert "title.closest('.js_components-modal" in parent.CdpParentEffects._TERMS_MODAL_JS
    assert "while(node&&node!==document.body" not in parent.CdpParentEffects._TERMS_MODAL_JS
    socket = SubmitSocket("modal")
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        effects.click_submit("96000004")

    # Two real clicks: the form's submit, then the modal's confirm.
    assert socket.releases == 2
    assert effects._submitted_paths["96000004"] == tmp_path / "gig-modal-test-B2-96000004-submitted.png"
    # Evidence that the modal was seen and clicked, for future sessions.
    assert (tmp_path / "gig-modal-test-B2-96000004-modal-confirmed.png").read_bytes() == b"png"


def test_a_modal_free_submit_is_unchanged_and_leaves_no_modal_evidence(tmp_path: Path) -> None:
    parent = load_module()
    socket = SubmitSocket("none")
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        effects.click_submit("96000004")

    assert socket.releases == 1
    assert "96000004" in effects._submitted_paths
    assert not (tmp_path / "gig-modal-test-B2-96000004-modal-confirmed.png").exists()


def test_a_modal_whose_button_never_appears_fails_explicitly_not_as_a_navigate_timeout(
    tmp_path: Path,
) -> None:
    # This test pays the real 3s poll budget once; that is the price of pinning the
    # deadline path rather than a mocked clock.
    parent = load_module()
    socket = SubmitSocket("modal_unclickable")
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(parent.ParentContractError, match="submit_confirm_modal_failed"):
            effects.click_submit("96000004")

    # The failure is the modal's own name -- cdp_wedged_row must NOT read it as a wedge.
    assert not parent.cdp_wedged_row({
        "request_id": "96000004",
        "status": "submission_failed:submit_confirm_modal_failed",
    })
