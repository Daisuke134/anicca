from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import time
from pathlib import Path


# 2026-08-08: every B2 official readback raised official_readback_route_invalid with
# zero evidence of what the browser saw. A live read-only probe (readback-probe,
# gig-readback-evidence worktree) found the actual page was perfectly valid -- correct
# title, correct URL, 20 offer links -- but a job description on it literally contained
# "...404エラーを解消してください", and the not_found check scanned document.body text
# (arbitrary client content) instead of document.title (site-controlled), so it false
# positived on every single pass. These tests pin: (1) a route/not_found failure now
# persists evidence before raising, (2) the not_found check is title-only again, and
# (3) the wedge quarantine decays instead of exiling a request id forever.

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

PARENT_SCRIPT = SCRIPTS / "application_parent.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeConnection:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *args):
        return None


def _build_effects(tmp_path: Path, parent):
    return parent.CdpParentEffects(
        ws_url="ws://127.0.0.1:9223/devtools/page/fake",
        evidence_dir=tmp_path / "evidence",
        ledger_path=tmp_path / "ledger.jsonl",
        pass_id="gig-pass-readback-test",
    )


def test_route_mismatch_persists_unexpected_route_evidence_then_raises(tmp_path):
    parent = _load(PARENT_SCRIPT, "application_parent_readback_evidence")
    effects = _build_effects(tmp_path, parent)

    async def fake_call(ws, method, params, call_id, timeout_seconds=30):
        if method in ("Page.enable", "Page.navigate"):
            return {}
        if method == "Runtime.evaluate":
            expression = params.get("expression", "")
            if expression == "document.readyState":
                return {"result": {"value": "complete"}}
            payload = json.dumps({
                "url": "https://coconala.com/login",
                "title": "ログイン | ココナラ",
                "offer_urls": [],
                "body": "ログインしてください",
                "not_found": False,
            })
            return {"result": {"value": payload}}
        if method == "Page.captureScreenshot":
            return {"data": "aGVsbG8="}  # base64 of b"hello"
        raise AssertionError(f"unexpected method {method}")

    effects._call = fake_call
    original_connect = parent.websockets.connect
    parent.websockets.connect = lambda *a, **k: FakeConnection()
    try:
        try:
            asyncio.run(effects._official_readback_async(set()))
            raised = False
        except parent.ParentContractError as error:
            raised = True
            assert str(error) == "official_readback_route_invalid"
    finally:
        parent.websockets.connect = original_connect

    assert raised, "route mismatch must still raise"
    evidence_dir = tmp_path / "evidence"
    files = sorted(evidence_dir.glob("parent-B2-applied-readback-unexpected-route-*.json"))
    assert len(files) == 1, f"expected exactly one evidence file, found {files}"
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["landed_url"] == "https://coconala.com/login"
    assert payload["title"] == "ログイン | ココナラ"
    screenshot_path = Path(payload["screenshot_path"])
    assert screenshot_path.exists()
    assert screenshot_path.read_bytes() == b"hello"


def test_route_mismatch_evidence_survives_screenshot_failure(tmp_path):
    """Dead-renderer scenario: captureScreenshot raising must not (a) skip the evidence
    JSON or (b) replace official_readback_route_invalid with a cdp_*_timeout error that
    cdp_wedged_row() would miscount as a wedge against an innocent listing."""
    parent = _load(PARENT_SCRIPT, "application_parent_readback_evidence_no_screenshot")
    effects = _build_effects(tmp_path, parent)

    async def fake_call(ws, method, params, call_id, timeout_seconds=30):
        if method in ("Page.enable", "Page.navigate"):
            return {}
        if method == "Runtime.evaluate":
            if params.get("expression") == "document.readyState":
                return {"result": {"value": "complete"}}
            payload = json.dumps({
                "url": "https://coconala.com/login",
                "title": "ログイン | ココナラ",
                "offer_urls": [],
                "body": "",
                "not_found": False,
            })
            return {"result": {"value": payload}}
        if method == "Page.captureScreenshot":
            raise parent.ParentContractError("cdp_Page.captureScreenshot_timeout_after_30s")
        raise AssertionError(f"unexpected method {method}")

    effects._call = fake_call
    original_connect = parent.websockets.connect
    parent.websockets.connect = lambda *a, **k: FakeConnection()
    try:
        try:
            asyncio.run(effects._official_readback_async(set()))
            raised = None
        except parent.ParentContractError as error:
            raised = str(error)
    finally:
        parent.websockets.connect = original_connect

    assert raised == "official_readback_route_invalid"
    files = sorted((tmp_path / "evidence").glob("parent-B2-applied-readback-unexpected-route-*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["screenshot_path"] is None
    assert not list((tmp_path / "evidence").glob("*.png"))


def test_not_found_check_uses_title_only_not_body_text():
    """The 2026-08-08 fix: not_found must not scan document.body.innerText. Applied-offers
    job descriptions are free-form client text that can legitimately contain "404" (a
    client asking for help fixing THEIR OWN site's 404 page) -- concatenating body into
    the test scored a fully valid, fully loaded page as not_found on every single pass."""
    source = PARENT_SCRIPT.read_text(encoding="utf-8")
    start = source.index("async def _official_readback_async")
    end = source.index("\n    def _official_readback(", start)
    section = source[start:end]
    assert "not_found:/404|ページが見つかりません|お探しのページ/.test(document.title)}" in section
    assert "document.title+' '+(document.body" not in section


def test_wedge_quarantine_fresh_entry_holds(tmp_path):
    parent = _load(PARENT_SCRIPT, "application_parent_wedge_fresh")
    store = parent.fence.IntentStore(tmp_path / "intents")
    parent.save_wedge_counts(store, {"91000032": parent.WEDGE_QUARANTINE_THRESHOLD})
    counts = parent.load_wedge_counts(store)
    assert counts.get("91000032") == parent.WEDGE_QUARANTINE_THRESHOLD


def test_wedge_quarantine_expires_after_ttl(tmp_path):
    parent = _load(PARENT_SCRIPT, "application_parent_wedge_expiry")
    store = parent.fence.IntentStore(tmp_path / "intents")
    path = parent._wedge_counts_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    stale_at = time.time() - parent.WEDGE_QUARANTINE_TTL_SECONDS - 60
    path.write_text(
        json.dumps({"91000033": {"count": parent.WEDGE_QUARANTINE_THRESHOLD, "updated_at": stale_at}}),
        encoding="utf-8",
    )
    counts = parent.load_wedge_counts(store)
    assert "91000033" not in counts


def test_wedge_quarantine_legacy_bare_int_revives_immediately(tmp_path):
    """The request ids stuck dead before decay existed (measured live 2026-08-08:
    37 entries, 18 at threshold) were bare ints with no timestamp at all. They must
    revive on the next load rather than being trusted as still-fresh forever."""
    parent = _load(PARENT_SCRIPT, "application_parent_wedge_legacy")
    store = parent.fence.IntentStore(tmp_path / "intents")
    path = parent._wedge_counts_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"91000034": parent.WEDGE_QUARANTINE_THRESHOLD}), encoding="utf-8")
    counts = parent.load_wedge_counts(store)
    assert "91000034" not in counts


def test_wedge_quarantine_malformed_entry_stays_quarantined(tmp_path):
    """Fail-closed: a malformed entry might be corruption hiding a live wedge, so it
    is kept quarantined (not silently forgiven) and logged."""
    parent = _load(PARENT_SCRIPT, "application_parent_wedge_malformed")
    store = parent.fence.IntentStore(tmp_path / "intents")
    path = parent._wedge_counts_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"91000035": {"count": "not-a-number", "updated_at": time.time()}}),
        encoding="utf-8",
    )
    counts = parent.load_wedge_counts(store)
    assert counts.get("91000035") == parent.WEDGE_QUARANTINE_THRESHOLD


def test_wedge_quarantine_save_preserves_timestamp_for_unchanged_ids(tmp_path):
    """Saving after id A wedges must not reset id B's clock -- otherwise any wedge
    anywhere would keep every quarantined id perpetually fresh."""
    parent = _load(PARENT_SCRIPT, "application_parent_wedge_preserve")
    store = parent.fence.IntentStore(tmp_path / "intents")
    parent.save_wedge_counts(store, {"91000036": 2})
    raw_first = json.loads(parent._wedge_counts_path(store).read_text(encoding="utf-8"))
    first_stamp = raw_first["91000036"]["updated_at"]

    time.sleep(0.01)
    # id B wedges; A's count is unchanged in this same save call.
    parent.save_wedge_counts(store, {"91000036": 2, "91000037": 1})
    raw_second = json.loads(parent._wedge_counts_path(store).read_text(encoding="utf-8"))
    assert raw_second["91000036"]["updated_at"] == first_stamp
    assert raw_second["91000037"]["updated_at"] > first_stamp


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
