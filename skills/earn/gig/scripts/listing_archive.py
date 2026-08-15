#!/usr/bin/env python3
"""listing_archive.py -- gig-loop spec Task C2 (docs/loop-engineering/26-...md SS CC').

Takes down a listing this account cannot actually execute (C1's fit judgment).
Coconala's own confirm modal (dumped from the live page, 2026-08-09) says archiving:
  "サービス詳細に「受付終了」と表示され、購入することができません。"
  "検索結果、カテゴリ一覧、プロフィールサービス一覧からこのサービスが見られなくなります。"
  "評価一覧、トークルーム、URLから、直接このサービスをたどることができます。"
i.e. it delists from search/category/profile, but existing talk-rooms, reviews, and
direct links stay reachable -- an archive cannot touch an in-flight order.

The confirm modal's "OK" control is a plain `<a href="/services/archive/<id>">` with no
onclick/data-method (dumped outerHTML has neither) -- so the browser's own click just
navigates there. This module reproduces that exact navigation in a hidden CDP target
(same technique as listing_inventory.py), then verifies the response body says
"サービスをアーカイブしました" before it is trusted as a real state change.

Usage:
  listing_archive.py archive 94000007 --reason capability_mismatch_delist
"""
from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from cdp_nav_snapshot import hidden_page_target, _call, _wait_for_load  # noqa: E402

STATE_DIR = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
LEDGER_PATH = STATE_DIR / "shuppin.jsonl"
IDENTITY = "coconala:kosuke"
BROWSER_GUARD = os.path.expanduser("~/.config/ai/bin/browser-guard.sh")
CONFIRM_TEXT = "サービスをアーカイブしました"
# Coconala intentionally keeps an archived service's direct URL reachable.  The
# confirmation page alone is therefore not a sufficient postcondition: a stale
# redirect/session can show the success copy while the buyer-facing service is
# still purchasable.  These are the rendered buyer-visible markers of the
# archived state (the direct page is expected to remain 200).
ARCHIVED_MARKERS = ("受付終了", "アーカイブ")

# In listing_ledger.ACTION_KIND as its own KIND_ARCHIVED (C3, 2026-08-09): an archive
# removes a listing, so it must never inflate published_listings/created_listings (the
# counters B0's objective math reads) -- and, unlike the pre-C3 version of this comment
# claimed, it must also net a previously-published id back OUT of published_listings, or
# a delisted service_id counts forever. count() does both from this one action string.
ARCHIVE_ACTION = "shuppin_archived"


def archive_state_confirmed(*, confirmation: bool, inventory_absent: bool) -> bool:
    """Return true only when the authenticated seller inventory lacks the service."""
    # The direct URL and confirmation copy are useful diagnostics, but only the
    # fresh seller inventory proves that the listing is no longer offered.
    return bool(inventory_absent)


async def _archive_live(service_id: str) -> dict:
    url = f"https://coconala.com/services/archive/{service_id}"
    async with hidden_page_target(url) as ws_url:
        import websockets
        async with websockets.connect(
            ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024,
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid); cid += 1
            await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": url}}))
            cid += 1
            deadline = asyncio.get_event_loop().time() + 15
            navigated_ok, cid = await _wait_for_load(ws, deadline, cid)
            r = await _call(ws, "Runtime.evaluate", {
                "expression": (
                    "JSON.stringify({url:location.href, title:document.title,"
                    "text:(document.body?document.body.innerText:'').slice(0,2000)})"
                ),
                "returnByValue": True,
            }, cid)
            raw = r.get("result", {}).get("result", {}).get("value", "") or ""
    try:
        page = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        page = {}
    confirmation = {
        "navigated_ok": navigated_ok,
        "url": page.get("url", ""),
        "title": page.get("title", ""),
        "confirmed": CONFIRM_TEXT in str(page.get("text", "")),
    }
    # Fresh buyer-facing readback.  Do not write the ledger until the real
    # seller inventory shows the archived state; this is the claim==reality gate.
    public_url = f"https://coconala.com/services/{service_id}"
    async with hidden_page_target(public_url) as ws_url:
        import websockets
        async with websockets.connect(
            ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024,
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid); cid += 1
            await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": public_url}}))
            cid += 1
            deadline = asyncio.get_event_loop().time() + 15
            public_navigated_ok, cid = await _wait_for_load(ws, deadline, cid)
            r = await _call(ws, "Runtime.evaluate", {
                "expression": (
                    "JSON.stringify({url:location.href, title:document.title,"
                    "text:(document.body?document.body.innerText:'').slice(0,12000)})"
                ),
                "returnByValue": True,
            }, cid)
            public_raw = r.get("result", {}).get("result", {}).get("value", "") or ""
    try:
        public_page = json.loads(public_raw)
    except (TypeError, json.JSONDecodeError):
        public_page = {}
    public_text = str(public_page.get("text", ""))
    public_archived = public_navigated_ok and any(marker in public_text for marker in ARCHIVED_MARKERS)

    # Coconala keeps direct service URLs reachable after archive, so the public
    # page may still render the old service/edit affordance.  The authoritative
    # seller-side state is the fresh services list: the archived service must no
    # longer have a card/link there.  This also makes the command idempotent when
    # a previous attempt already completed the archive.
    list_url = "https://coconala.com/mypage/services_lists"
    async with hidden_page_target(list_url) as ws_url:
        import websockets
        async with websockets.connect(
            ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024,
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid); cid += 1
            await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": list_url}}))
            cid += 1
            deadline = asyncio.get_event_loop().time() + 15
            list_navigated_ok, cid = await _wait_for_load(ws, deadline, cid)
            r = await _call(ws, "Runtime.evaluate", {
                "expression": (
                    "JSON.stringify({url:location.href,"
                    "has_service:[...document.querySelectorAll('a[href]')]"
                    ".some(a=>a.href.includes('/services/" + service_id + "'))})"
                ),
                "returnByValue": True,
            }, cid)
            list_raw = r.get("result", {}).get("result", {}).get("value", "") or ""
    try:
        list_page = json.loads(list_raw)
    except (TypeError, json.JSONDecodeError):
        list_page = {}
    inventory_absent = list_navigated_ok and not bool(list_page.get("has_service"))
    return {
        **confirmation,
        "public_url": public_page.get("url", public_url),
        "public_title": public_page.get("title", ""),
        "public_archived": public_archived,
        "inventory_url": list_page.get("url", list_url),
        "inventory_absent": inventory_absent,
        "confirmed": archive_state_confirmed(
            confirmation=confirmation["confirmed"], inventory_absent=inventory_absent,
        ),
    }


async def archive_listing_live(service_id: str, identity: str = IDENTITY) -> dict:
    cdp_base = subprocess.run(
        [BROWSER_GUARD, "acquire", identity], capture_output=True, text=True, check=True,
    ).stdout.strip()
    os.environ["CLOAK_CDP_BASE_URL"] = cdp_base
    try:
        return await _archive_live(service_id)
    finally:
        subprocess.run([BROWSER_GUARD, "release", identity], capture_output=True, text=True)


# --- deterministic ledger row (unit-testable without a browser) ---------------------

def build_ledger_row(
    *, ts: int, pass_id: str, service_id: str, title: str, reason: str,
    evidence: dict | None = None,
    recorded_by: str = "listing_archive",
) -> dict:
    row = {
        "ts": ts,
        "pass_id": pass_id,
        "lane": "list",
        "action": ARCHIVE_ACTION,
        "service_id": service_id,
        "url": f"https://coconala.com/services/{service_id}",
        "title": title,
        "reason": reason,
        "recorded_by": recorded_by,
    }
    if evidence:
        row["evidence"] = evidence
    return row


def append_ledger_row(ledger_path: Path, row: dict) -> bool:
    """Idempotent, lock-protected append -- same shape as b0_result_gate._append_once,
    deduped on (action, service_id, pass_id) so a retried pass never double-records."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            for line in handle:
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    isinstance(existing, dict)
                    and existing.get("action") == row["action"]
                    and existing.get("service_id") == row["service_id"]
                    and existing.get("pass_id") == row["pass_id"]
                ):
                    return False
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            return True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# --- CLI -------------------------------------------------------------------------------

def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    archive_p = sub.add_parser("archive")
    archive_p.add_argument("service_id")
    archive_p.add_argument("--title", default="")
    archive_p.add_argument("--reason", default="capability_mismatch_delist")
    archive_p.add_argument("--pass-id", default=None)
    archive_p.add_argument("--ledger", default=str(LEDGER_PATH))
    args = parser.parse_args(argv)

    result = asyncio.run(archive_listing_live(args.service_id))
    if not result.get("confirmed"):
        print(json.dumps({"ok": False, **result}, ensure_ascii=False))
        return 1

    ts = int(time.time())
    pass_id = args.pass_id or f"c2-delist-{ts}"
    row = build_ledger_row(
        ts=ts, pass_id=pass_id, service_id=args.service_id,
        title=args.title, reason=args.reason,
        evidence={
            "archive_url": result.get("url", ""),
            "public_url": result.get("public_url", ""),
            "inventory_url": result.get("inventory_url", ""),
            "inventory_absent": result.get("inventory_absent", False),
            "public_archived": result.get("public_archived", False),
        },
    )
    written = append_ledger_row(Path(args.ledger), row)
    print(json.dumps({"ok": True, "written": written, **result, "row": row}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
