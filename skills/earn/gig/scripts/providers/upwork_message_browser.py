#!/usr/bin/env python3
"""Fail-closed Upwork room message fill, single send and official-ID readback."""

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


def message_preflight_expression(decision: dict[str, Any]) -> str:
    sealed = json.dumps(decision, ensure_ascii=False, separators=(",", ":"))
    return rf'''(async()=>{{const d={sealed},norm=x=>(x||'').replace(/\s+/g,' ').trim();
const digest=async s=>{{const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s));return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');}};
const head=await digest(norm(document.body.innerText));
const selectors=['[data-test="message-input"]','[data-cy="message-input"]','div[contenteditable="true"]','textarea[placeholder*="message" i]','.message-input textarea','#message-text'];
const inputs=selectors.flatMap(s=>[...document.querySelectorAll(s)]).filter((x,i,a)=>a.indexOf(x)===i&&x.offsetParent!==null);
if(inputs.length!==1)throw Error('upwork_message_input_invalid');const input=inputs[0];
if(input.tagName==='TEXTAREA'||input.tagName==='INPUT'){{const p=input.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(input,d.message.body);}}else{{input.textContent=d.message.body;}}
input.dispatchEvent(new InputEvent('input',{{bubbles:true,inputType:'insertText',data:d.message.body}}));input.dispatchEvent(new Event('change',{{bubbles:true}}));
const buttons=[...document.querySelectorAll('[data-test="send-message-button"],[data-cy="send-button"],button[aria-label="Send message"],button')].filter((x,i,a)=>a.indexOf(x)===i&&x.offsetParent!==null&&(/send/i.test(norm(x.innerText))||/send/i.test(x.getAttribute('aria-label')||'')));
const ids=[...document.querySelectorAll('[data-test="message-item"],.message-item,.chat-message')].map(x=>x.getAttribute('data-id')||x.getAttribute('data-message-id')||x.getAttribute('data-story-id')).filter(Boolean);
return{{room_url:location.href,room_id:d.source.room_id,room_head_sha256:head,message_body:input.value??input.textContent,send_enabled:buttons.length===1&&!buttons[0].disabled,send_label:buttons.length===1?norm(buttons[0].innerText||buttons[0].getAttribute('aria-label')):null,before_message_ids:ids,validation_errors:[...document.querySelectorAll('[role="alert"],.form-error,.air3-form-error')].map(x=>norm(x.innerText)).filter(Boolean)}};
}})()'''


def send_click_expression(room_id: str) -> str:
    sealed = json.dumps(room_id)
    return rf'''(()=>{{const id={sealed},norm=x=>(x||'').replace(/\s+/g,' ').trim();if(!location.pathname.includes('/rooms/'+id))throw Error('upwork_room_identity_mismatch');
const buttons=[...document.querySelectorAll('[data-test="send-message-button"],[data-cy="send-button"],button[aria-label="Send message"],button')].filter((x,i,a)=>a.indexOf(x)===i&&x.offsetParent!==null&&!x.disabled&&(/send/i.test(norm(x.innerText))||/send/i.test(x.getAttribute('aria-label')||'')));
if(buttons.length!==1)throw Error('upwork_message_send_control_invalid');buttons[0].click();return true;}})()'''


def message_readback_expression(decision: dict[str, Any]) -> str:
    sealed = json.dumps(decision, ensure_ascii=False, separators=(",", ":"))
    return rf'''(()=>{{const d={sealed},norm=x=>(x||'').replace(/\s+/g,' ').trim(),before=new Set(d.before_message_ids||[]);
const items=[...document.querySelectorAll('[data-test="message-item"],.message-item,.chat-message')];
const rows=items.map(x=>{{const id=x.getAttribute('data-id')||x.getAttribute('data-message-id')||x.getAttribute('data-story-id');const body=norm((x.querySelector('[data-test="message-text"],.message-text,p')||x).innerText);const mine=x.classList.contains('outgoing')||x.classList.contains('sent')||!!x.querySelector('[data-test="my-message"]');return{{id,body,mine}};}});
const match=rows.find(x=>x.id&&!before.has(x.id)&&x.mine&&x.body===norm(d.message.body));return{{room_id:d.source.room_id,readback_url:location.href,message_id:match?match.id:null,state:match?'sent':'unknown',body_sha256:null}};}})()'''


def validate_preflight(snapshot: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    source, message = decision.get("source"), decision.get("message")
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "room_url", "room_id", "room_head_sha256", "message_body", "send_enabled",
        "send_label", "before_message_ids", "validation_errors",
    } or not isinstance(source, dict) or not isinstance(message, dict):
        raise ValueError("upwork_message_preflight_mismatch")
    url = urlsplit(str(snapshot.get("room_url") or ""))
    ids = snapshot.get("before_message_ids")
    if (
        url.scheme != "https" or url.netloc != "www.upwork.com"
        or source.get("room_url") != snapshot.get("room_url")
        or source.get("room_id") != snapshot.get("room_id") or source["room_id"] not in url.path
        or source.get("head_sha256") != snapshot.get("room_head_sha256")
        or message.get("body") != snapshot.get("message_body")
        or snapshot.get("send_enabled") is not True
        or not re.search(r"send", str(snapshot.get("send_label") or ""), re.I)
        or not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids)
        or snapshot.get("validation_errors") != []
    ):
        raise ValueError("upwork_message_preflight_mismatch")
    evidence = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"ready": True, "room_id": source["room_id"], "head_sha256": source["head_sha256"],
            "before_message_ids": ids, "evidence_sha256": evidence}


def validate_readback(snapshot: dict[str, Any], decision: dict[str, Any]) -> dict[str, str]:
    source, message = decision.get("source"), decision.get("message")
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "room_id", "readback_url", "message_id", "state", "body_sha256",
    } or not isinstance(source, dict) or not isinstance(message, dict):
        raise ValueError("upwork_message_send_unconfirmed")
    url = urlsplit(str(snapshot.get("readback_url") or ""))
    message_id = snapshot.get("message_id")
    if (
        snapshot.get("room_id") != source.get("room_id") or snapshot.get("state") != "sent"
        or not isinstance(message_id, str) or not message_id
        or url.scheme != "https" or url.netloc != "www.upwork.com" or source["room_id"] not in url.path
    ):
        raise ValueError("upwork_message_send_unconfirmed")
    body_sha = hashlib.sha256(" ".join(message["body"].split()).encode()).hexdigest()
    return {"state": "sent", "room_id": source["room_id"], "message_id": message_id,
            "body_sha256": body_sha, "evidence_sha256": hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()}


async def send_message_after_fence(
    decision: dict[str, Any], start_effect: Callable[[dict[str, Any]], bool],
) -> dict[str, str]:
    source = decision.get("source") if isinstance(decision, dict) else None
    if not isinstance(source, dict) or not isinstance(decision.get("message"), dict):
        raise ValueError("upwork_message_preflight_mismatch")
    async with hidden_page_target(source["room_url"]) as ws_url:
        async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024) as ws:
            await _call(ws, "Page.enable", {}, 1)
            await _call(ws, "Page.navigate", {"url": source["room_url"]}, 2)
            _, cid = await _wait_for_load(ws, asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS, 3)
            raw = await _call(ws, "Runtime.evaluate", {"expression": message_preflight_expression(decision), "awaitPromise": True, "returnByValue": True}, cid)
            preflight = validate_preflight(raw.get("result", {}).get("result", {}).get("value"), decision)
            if start_effect(preflight) is not True:
                raise ValueError("upwork_message_effect_not_started")
            click_decision = {**decision, "before_message_ids": preflight["before_message_ids"]}
            await _call(ws, "Runtime.evaluate", {"expression": send_click_expression(source["room_id"]), "returnByValue": True}, cid + 1)
            await asyncio.sleep(2)
            raw = await _call(ws, "Runtime.evaluate", {"expression": message_readback_expression(click_decision), "returnByValue": True}, cid + 2)
    return validate_readback(raw.get("result", {}).get("result", {}).get("value"), decision)
