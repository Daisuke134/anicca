"""§FG' item 1: _official_readback_async must walk past page 1 and survive one hung nav.

Read-only scout measured 2026-08-09: the readback that confirms a submitted (or
quarantine-candidate) request id only ever looked at page 1 of the applied-offers list
(pages_walked hardcoded to 1, no pagination) and had no retry for a single hung
Page.navigate to an unrelated offer entry -- turning one slow neighbour's page into a hard
failure for whoever's exact-id search happened to be walking past it at the time.
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
    spec = importlib.util.spec_from_file_location("application_parent_readback_pagination", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScanSocket:
    """Fakes the CDP transport _official_readback_async drives.

    Routes by method (and, for Runtime.evaluate, by a snippet of the expression) so the same
    fake serves the applied-offers list eval, the per-offer detail eval, and the readyState
    poll. `hang_once`/`hang_forever` make a specific Page.navigate URL simulate a real hang by
    having recv() raise asyncio.TimeoutError -- exactly what _call does on a genuine 30s dead
    end, without an actual 30s wait. A page or offer-detail entry of the string "HANG" makes
    that Runtime.evaluate hang the same way.
    """

    _TIMEOUT = object()
    HANG = "HANG"

    def __init__(self, pages, offer_details, *, hang_once=(), hang_forever=()):
        self.pages = list(pages)
        self.offer_details = dict(offer_details)
        self.hang_once = set(hang_once)
        self.hang_forever = set(hang_forever)
        self._hang_once_used: set[str] = set()
        self.pending: list[object] = []
        self.navigated_urls: list[str] = []

    async def send(self, raw: str) -> None:
        request = json.loads(raw)
        request_id = request["id"]
        method = request["method"]
        params = request.get("params", {})
        if method == "Page.navigate":
            url = params["url"]
            self.navigated_urls.append(url)
            if url in self.hang_forever or (url in self.hang_once and url not in self._hang_once_used):
                if url in self.hang_once:
                    self._hang_once_used.add(url)
                self.pending.append(self._TIMEOUT)
                return
            self.pending.append(json.dumps({"id": request_id, "result": {}}))
            return
        if method == "Runtime.evaluate":
            expression = str(params.get("expression") or "")
            if "document.readyState" in expression:
                value = "complete"
            elif "OfferRequestId" in expression:
                url = self.navigated_urls[-1]
                detail = self.offer_details.get(url, {"hidden": None, "hrefs": [], "body": ""})
                if detail == self.HANG:
                    self.pending.append(self._TIMEOUT)
                    return
                value = json.dumps(detail, ensure_ascii=False)
            else:
                page = self.pages.pop(0)
                if page == self.HANG:
                    self.pending.append(self._TIMEOUT)
                    return
                value = json.dumps(page, ensure_ascii=False)
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
        item = self.pending.pop(0)
        if item is self._TIMEOUT:
            raise asyncio.TimeoutError()
        return item


class FakeConnection:
    def __init__(self, socket: ScanSocket):
        self.socket = socket

    async def __aenter__(self) -> ScanSocket:
        return self.socket

    async def __aexit__(self, *_: object) -> None:
        return None


def _effects(parent, tmp_path: Path):
    return parent.CdpParentEffects(
        ws_url="ws://127.0.0.1:9223/devtools/page/readback-scan-test",
        evidence_dir=tmp_path,
        ledger_path=tmp_path / "applied.jsonl",
        pass_id="readback-scan-test",
    )


def test_official_readback_walks_a_second_page_when_target_is_not_on_the_first(tmp_path: Path) -> None:
    parent = load_module()
    target = "95000021"
    page1 = {
        "url": parent._APPLIED_OFFERS_URL,
        "title": "応募・スカウト管理 | ココナラ",
        "offer_urls": [
            "https://coconala.com/mypage/offers/95000000",
            "https://coconala.com/mypage/offers/95000001",
        ],
        "next_href": "https://coconala.com/mypage/job_matching/applied/offers?page=2",
        "body": "page1",
        "not_found": False,
    }
    page2 = {
        "url": "https://coconala.com/mypage/job_matching/applied/offers?page=2",
        "title": "応募・スカウト管理 | ココナラ",
        "offer_urls": ["https://coconala.com/mypage/offers/1000099"],
        "next_href": None,
        "body": "page2",
        "not_found": False,
    }
    offer_details = {
        "https://coconala.com/mypage/offers/95000000": {"hidden": "95000002", "hrefs": [], "body": ""},
        "https://coconala.com/mypage/offers/95000001": {"hidden": "95000003", "hrefs": [], "body": ""},
        "https://coconala.com/mypage/offers/1000099": {"hidden": target, "hrefs": [], "body": ""},
    }
    socket = ScanSocket([page1, page2], offer_details)
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        payload, screenshot = asyncio.run(effects._official_readback_async({target}))

    assert payload["pages_walked"] == 2
    assert target in payload["request_ids"]
    assert screenshot == b"png"
    # The walk actually navigated to page 2, not just read its DOM out of thin air.
    assert page2["url"] in socket.navigated_urls


def test_official_readback_stays_on_page_one_when_no_target_id_is_requested(tmp_path: Path) -> None:
    """official_ids_for_snapshot's empty-expected_ids call must not inflate into N pages."""
    parent = load_module()
    page1 = {
        "url": parent._APPLIED_OFFERS_URL,
        "title": "t",
        "offer_urls": ["https://coconala.com/mypage/offers/95000000"],
        "next_href": "https://coconala.com/mypage/job_matching/applied/offers?page=2",
        "body": "b",
        "not_found": False,
    }
    offer_details = {
        "https://coconala.com/mypage/offers/95000000": {"hidden": "95000002", "hrefs": [], "body": ""},
    }
    # Only page 1 is supplied. If the empty-expected_ids call paginated anyway, the second
    # Runtime.evaluate for the list page would pop from an empty list and raise IndexError.
    socket = ScanSocket([page1], offer_details)
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        payload, _ = asyncio.run(effects._official_readback_async(set()))

    assert payload["pages_walked"] == 1
    assert payload["request_ids"] == ["95000002"]
    # N7: no wasted live navigate to a next page the budget will never let us consume.
    assert page1["next_href"] not in socket.navigated_urls


def test_official_readback_retries_a_single_hung_offer_navigate_once(tmp_path: Path) -> None:
    parent = load_module()
    target = "95000021"
    hung_url = "https://coconala.com/mypage/offers/95000000"
    target_url = "https://coconala.com/mypage/offers/1000099"
    page1 = {
        "url": parent._APPLIED_OFFERS_URL,
        "title": "t",
        "offer_urls": [hung_url, target_url],
        "next_href": None,
        "body": "b",
        "not_found": False,
    }
    offer_details = {
        hung_url: {"hidden": "95000002", "hrefs": [], "body": ""},
        target_url: {"hidden": target, "hrefs": [], "body": ""},
    }
    socket = ScanSocket([page1], offer_details, hang_once={hung_url})
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        payload, _ = asyncio.run(effects._official_readback_async({target}))

    assert target in payload["request_ids"]
    # One failed attempt, one retry -- the transient hang cost a retry, not the whole scan.
    assert socket.navigated_urls.count(hung_url) == 2


def test_official_readback_raises_readback_scan_timeout_when_retry_also_hangs(tmp_path: Path) -> None:
    """A dead-both-times unrelated offer page is a distinct, classifiable outcome.

    Not a generic ParentContractError: commit_decisions must be able to tell this apart from
    the candidate's OWN action failing, so it is never scored as a wedge strike against
    whichever id this readback call was actually trying to confirm.
    """
    parent = load_module()
    hung_url = "https://coconala.com/mypage/offers/95000000"
    page1 = {
        "url": parent._APPLIED_OFFERS_URL,
        "title": "t",
        "offer_urls": [hung_url],
        "next_href": None,
        "body": "b",
        "not_found": False,
    }
    socket = ScanSocket([page1], {}, hang_forever={hung_url})
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(parent.ReadbackScanTimeout):
            asyncio.run(effects._official_readback_async({"9999999"}))

    assert socket.navigated_urls.count(hung_url) == 2


def test_truncated_walk_with_a_next_link_remaining_is_inconclusive_not_absent(tmp_path: Path) -> None:
    """B1: exhausting the page budget while a next link still exists proves nothing about
    absence. Returning plain False here is the duplicate-application path: the release
    script would clear an already-applied id, and the PREPARED reconcile would retire and
    resubmit. Must raise so both consumers fail closed."""
    parent = load_module()

    def page(index: int, next_index: int | None):
        url = parent._APPLIED_OFFERS_URL if index == 1 else (
            f"{parent._APPLIED_OFFERS_URL}?page={index}"
        )
        return {
            "url": url,
            "title": "t",
            "offer_urls": [f"https://coconala.com/mypage/offers/100000{index}"],
            "next_href": (
                f"https://coconala.com/mypage/job_matching/applied/offers?page={next_index}"
                if next_index else None
            ),
            "body": "b",
            "not_found": False,
        }

    offer_details = {
        f"https://coconala.com/mypage/offers/100000{i}": {"hidden": f"500000{i}", "hrefs": [], "body": ""}
        for i in (1, 2, 3)
    }
    socket = ScanSocket([page(1, 2), page(2, 3)], offer_details)
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent, "_APPLIED_OFFERS_MAX_PAGES", 2), \
            mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(parent.ReadbackScanTimeout) as caught:
            asyncio.run(effects._official_readback_async({"9999999"}))

    assert "truncated" in str(caught.value)
    # N7: the budget was exhausted, so the page-3 link was never navigated to just to be
    # thrown away.
    assert "https://coconala.com/mypage/job_matching/applied/offers?page=3" not in socket.navigated_urls


def test_a_next_page_navigate_hang_is_a_scan_timeout_not_a_candidate_wedge(tmp_path: Path) -> None:
    """B2 site 1: the nav from page 1 to page 2 is neighbour-scan territory."""
    parent = load_module()
    page2_url = "https://coconala.com/mypage/job_matching/applied/offers?page=2"
    page1 = {
        "url": parent._APPLIED_OFFERS_URL,
        "title": "t",
        "offer_urls": ["https://coconala.com/mypage/offers/95000000"],
        "next_href": page2_url,
        "body": "b",
        "not_found": False,
    }
    offer_details = {
        "https://coconala.com/mypage/offers/95000000": {"hidden": "95000002", "hrefs": [], "body": ""},
    }
    socket = ScanSocket([page1], offer_details, hang_forever={page2_url})
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(parent.ReadbackScanTimeout):
            asyncio.run(effects._official_readback_async({"9999999"}))


def test_a_second_page_list_eval_hang_is_a_scan_timeout(tmp_path: Path) -> None:
    """B2 site 2: page 2+'s list eval happens after the first successful page eval."""
    parent = load_module()
    page1 = {
        "url": parent._APPLIED_OFFERS_URL,
        "title": "t",
        "offer_urls": [],
        "next_href": "https://coconala.com/mypage/job_matching/applied/offers?page=2",
        "body": "b",
        "not_found": False,
    }
    socket = ScanSocket([page1, ScanSocket.HANG], {})
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(parent.ReadbackScanTimeout):
            asyncio.run(effects._official_readback_async({"9999999"}))


def test_an_offer_detail_eval_hang_is_a_scan_timeout(tmp_path: Path) -> None:
    """B2 site 3: the detail eval on a neighbour's offer page, after a successful nav."""
    parent = load_module()
    hung_url = "https://coconala.com/mypage/offers/95000000"
    page1 = {
        "url": parent._APPLIED_OFFERS_URL,
        "title": "t",
        "offer_urls": [hung_url],
        "next_href": None,
        "body": "b",
        "not_found": False,
    }
    socket = ScanSocket([page1], {hung_url: ScanSocket.HANG})
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(parent.ReadbackScanTimeout):
            asyncio.run(effects._official_readback_async({"9999999"}))


def test_a_page_one_list_eval_hang_stays_a_plain_error(tmp_path: Path) -> None:
    """The first list eval right after the candidate's own submit is genuine renderer-death
    evidence -- it must keep striking, not be reclassified as a neighbour's problem."""
    parent = load_module()
    socket = ScanSocket([ScanSocket.HANG], {})
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(parent.ParentContractError) as caught:
            asyncio.run(effects._official_readback_async({"9999999"}))

    assert not isinstance(caught.value, parent.ReadbackScanTimeout)


def test_official_readback_still_raises_plain_error_when_the_list_page_itself_is_wrong(
    tmp_path: Path,
) -> None:
    """A bad route on the applied-offers list itself is NOT a readback-scan classification.

    Distinguishes "the readback route is broken" from "one neighbour's page hung": only the
    per-row scan loop gets reclassified as ReadbackScanTimeout.
    """
    parent = load_module()
    page1 = {
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "title": "404",
        "offer_urls": [],
        "next_href": None,
        "body": "not found",
        "not_found": True,
    }
    socket = ScanSocket([page1], {})
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(parent.ParentContractError) as caught:
            asyncio.run(effects._official_readback_async({"9999999"}))

    assert not isinstance(caught.value, parent.ReadbackScanTimeout)
    assert "official_readback_route_invalid" in str(caught.value)


@pytest.mark.parametrize("title", ["403 Forbidden", "Access Denied"])
def test_official_readback_access_denied_is_never_treated_as_exact_id_absence(
    tmp_path: Path, title: str
) -> None:
    parent = load_module()
    page1 = {
        "url": parent._APPLIED_OFFERS_URL,
        "title": title,
        "offer_urls": [],
        "next_href": None,
        "body": title,
        "access_denied": True,
        "not_found": False,
    }
    socket = ScanSocket([page1], {})
    effects = _effects(parent, tmp_path)

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        with pytest.raises(
            parent.ParentContractError, match="official_readback_access_denied"
        ):
            asyncio.run(effects._official_readback_async({"9999999"}))
