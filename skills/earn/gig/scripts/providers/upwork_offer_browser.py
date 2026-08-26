#!/usr/bin/env python3
"""Fail-closed browser effect for one qualified Upwork direct offer."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import websockets

from cdp_nav_snapshot import LOAD_TIMEOUT_SECS, _call, _wait_for_load, hidden_page_target


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def offer_preflight_expression() -> str:
    return r'''(()=>{const norm=x=>(x||'').replace(/\s+/g,' ').trim();
const controls=[...document.querySelectorAll('button,a')];
const accept=controls.find(x=>/^accept offer$/i.test(norm(x.innerText)));
const body=norm(document.body.innerText);
return {offer_url:location.href,body_text:body,accept_label:accept?norm(accept.innerText):null,accept_enabled:!!accept&&!accept.disabled};})()'''


def accept_click_expression(offer_id: str) -> str:
    sealed = json.dumps(offer_id)
    return rf'''(()=>{{const id={sealed},norm=x=>(x||'').replace(/\s+/g,' ').trim();
if(!location.pathname.includes(id))throw Error('upwork_offer_identity_mismatch');
const matches=[...document.querySelectorAll('button,a')].filter(x=>/^accept offer$/i.test(norm(x.innerText))&&!x.disabled);
if(matches.length!==1)throw Error('upwork_offer_accept_control_invalid');matches[0].click();return true;}})()'''


def offer_readback_expression(offer_id: str) -> str:
    sealed = json.dumps(offer_id)
    return rf'''(()=>{{const offer={sealed},body=(document.body.innerText||'').replace(/\s+/g,' ').trim(),url=location.href;
const hrefs=[...document.querySelectorAll('a[href]')].map(x=>x.href).concat([url]);
const match=hrefs.map(x=>x.match(/\/workroom\/([^/?#]+)/)).find(Boolean);
return {{offer_id:offer,readback_url:url,contract_id:match?match[1]:null,state:match&&/active contract|contract room|workroom|my jobs/i.test(body)?'accepted':'unknown'}};}})()'''


def validate_offer_preflight(snapshot: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    offer = decision.get("offer") if isinstance(decision, dict) else None
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "offer_url", "body_text", "accept_label", "accept_enabled",
    } or not isinstance(offer, dict):
        raise ValueError("upwork_offer_preflight_mismatch")
    url = urlsplit(str(snapshot.get("offer_url") or ""))
    body = _norm(snapshot.get("body_text"))
    amount = offer.get("rate_or_amount_usd")
    required_fragments = [offer.get("title"), offer.get("scope"), offer.get("deadline")]
    amount_markers = {f"${amount}", f"${float(amount):.2f}"} if isinstance(amount, (int, float)) else set()
    if (
        decision.get("action") != "accept"
        or not re.fullmatch(r"[0-9a-f]{64}", str(decision.get("decision_sha256") or ""))
        or url.scheme != "https" or url.netloc != "www.upwork.com"
        or offer.get("offer_url") != snapshot.get("offer_url")
        or offer.get("offer_id") not in url.path
        or snapshot.get("accept_label") != "Accept offer"
        or snapshot.get("accept_enabled") is not True
        or any(_norm(fragment).casefold() not in body.casefold() for fragment in required_fragments)
        or not any(marker in body for marker in amount_markers)
        or (offer.get("contract_type") == "fixed_price" and not re.search(r"funded|in escrow", body, re.IGNORECASE))
        or (offer.get("contract_type") == "hourly" and not re.search(r"billing (?:method )?verified|payment verified", body, re.IGNORECASE))
    ):
        raise ValueError("upwork_offer_preflight_mismatch")
    evidence = hashlib.sha256(json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    return {"ready": True, "offer_id": offer["offer_id"], "evidence_sha256": evidence}


def validate_offer_readback(snapshot: dict[str, Any], decision: dict[str, Any]) -> dict[str, str]:
    offer = decision.get("offer") if isinstance(decision, dict) else None
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "offer_id", "readback_url", "contract_id", "state",
    } or not isinstance(offer, dict):
        raise ValueError("upwork_offer_accept_unconfirmed")
    url = urlsplit(str(snapshot.get("readback_url") or ""))
    contract_id = snapshot.get("contract_id")
    if (
        snapshot.get("offer_id") != offer.get("offer_id") or snapshot.get("state") != "accepted"
        or not isinstance(contract_id, str) or not contract_id.strip()
        or url.scheme != "https" or url.netloc != "www.upwork.com"
    ):
        raise ValueError("upwork_offer_accept_unconfirmed")
    evidence = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"state": "accepted", "offer_id": offer["offer_id"],
            "contract_id": contract_id, "evidence_sha256": evidence}


async def accept_offer_after_fence(
    decision: dict[str, Any], start_effect: Callable[[dict[str, Any]], bool],
) -> dict[str, str]:
    offer = decision.get("offer") if isinstance(decision, dict) else None
    if not isinstance(offer, dict) or not callable(start_effect):
        raise ValueError("upwork_offer_preflight_mismatch")
    async with hidden_page_target(offer["offer_url"]) as ws_url:
        async with websockets.connect(ws_url, ping_interval=None, open_timeout=10,
                                      max_size=40 * 1024 * 1024) as ws:
            await _call(ws, "Page.enable", {}, 1)
            await _call(ws, "Page.navigate", {"url": offer["offer_url"]}, 2)
            _, cid = await _wait_for_load(ws, asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS, 3)
            raw = await _call(ws, "Runtime.evaluate", {
                "expression": offer_preflight_expression(), "returnByValue": True,
            }, cid)
            preflight = validate_offer_preflight(raw.get("result", {}).get("result", {}).get("value"), decision)
            if start_effect(preflight) is not True:
                raise ValueError("upwork_offer_effect_not_started")
            await _call(ws, "Runtime.evaluate", {
                "expression": accept_click_expression(offer["offer_id"]), "returnByValue": True,
            }, cid + 1)
            await asyncio.sleep(2)
            raw = await _call(ws, "Runtime.evaluate", {
                "expression": offer_readback_expression(offer["offer_id"]), "returnByValue": True,
            }, cid + 2)
    return validate_offer_readback(raw.get("result", {}).get("result", {}).get("value"), decision)
