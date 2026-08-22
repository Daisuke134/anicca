#!/usr/bin/env python3
"""Fail-closed contracts for filling an Upwork proposal before any submit click."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import websockets


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cdp_nav_snapshot import (  # noqa: E402
    LOAD_TIMEOUT_SECS, _call, _wait_for_load, hidden_page_target,
)


_SNAPSHOT_KEYS = {
    "attachments", "bid_usd", "cover_letter", "duration_label", "form_url",
    "job_id", "required_connects", "screening_answers", "submit_enabled",
    "submit_label", "validation_errors",
}


def _duration_label(days: Any) -> str:
    if type(days) is not int or days < 1:
        raise ValueError("upwork_proposal_preflight_mismatch")
    if days <= 30:
        return "Less than 1 month"
    if days <= 90:
        return "1 to 3 months"
    if days <= 180:
        return "3 to 6 months"
    return "More than 6 months"


def fill_preflight_expression(payload: dict[str, Any]) -> str:
    """Build one DOM fill/read expression with no submit click."""
    terms = payload.get("terms") if isinstance(payload, dict) else None
    if not isinstance(terms, dict):
        raise ValueError("upwork_proposal_preflight_mismatch")
    duration = _duration_label(terms.get("delivery_days"))
    sealed = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    duration_json = json.dumps(duration)
    return f'''(async()=>{{
const p={sealed},duration={duration_json},wait=ms=>new Promise(r=>setTimeout(r,ms));
const norm=x=>(x||'').replace(/\\s+/g,' ').trim();
const setValue=(x,v)=>{{if(!x)throw Error('upwork_form_control_missing');const proto=x.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(x,String(v));x.dispatchEvent(new Event('input',{{bubbles:true}}));x.dispatchEvent(new Event('change',{{bubbles:true}}));}};
const cover=document.querySelector('.cover-letter-area textarea,textarea[data-test*="cover" i],textarea[aria-label*="cover" i]');
const bid=document.querySelector('input[data-test*="bid" i],input[name*="bid" i],.fe-proposal-job-rate input');
setValue(cover,p.cover_letter);setValue(bid,p.terms.bid_usd);
const durationRoot=document.querySelector('.fe-proposal-job-estimated-duration,[data-test*="duration" i]');
const combo=durationRoot?.querySelector('[role="combobox"],button');if(!combo)throw Error('upwork_duration_missing');combo.click();await wait(0);
const option=[...(durationRoot.querySelectorAll('li,[role="option"]'))].find(x=>norm(x.innerText)===duration);if(!option)throw Error('upwork_duration_option_missing');option.click();await wait(0);
const areas=[...document.querySelectorAll('.fe-proposal-job-questions textarea')];if(areas.length!==p.screening_answers.length)throw Error('upwork_question_count_mismatch');
const answers=p.screening_answers.map(item=>{{const area=areas.find(x=>norm((x.closest('label,.up-form-group,.air3-form-group,[data-test]')||x.parentElement).innerText).includes(norm(item.question)));if(!area)throw Error('upwork_question_mismatch');setValue(area,item.answer);return{{question:item.question,answer:area.value}};}});
const submit=document.querySelector('footer .air3-btn-primary,footer button[type="submit"],button[data-test*="submit" i]');if(!submit)throw Error('upwork_submit_control_missing');
const body=norm(document.body.innerText),required=p.terms.required_connects,connects=body.includes(String(required)+' Connects')?required:null;
const errors=[...document.querySelectorAll('.form-error,.air3-form-error,.up-alert-danger,[role="alert"]')].map(x=>norm(x.innerText)).filter(Boolean);
return{{job_id:p.job_id,form_url:location.href,required_connects:connects,bid_usd:Number(bid.value),duration_label:norm(combo.innerText),cover_letter:cover.value,screening_answers:answers,attachments:[],submit_label:norm(submit.innerText),submit_enabled:!submit.disabled,validation_errors:errors}};
}})()'''


async def fill_proposal_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    """Fill and read one authenticated hidden proposal form without submit."""
    job_id = payload.get("job_id") if isinstance(payload, dict) else None
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("upwork_proposal_preflight_mismatch")
    apply_url = f"https://www.upwork.com/ab/proposals/job/{job_id}/apply/#/"
    async with hidden_page_target(apply_url) as ws_url:
        async with websockets.connect(
            ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024,
        ) as ws:
            await _call(ws, "Page.enable", {}, 1)
            await _call(ws, "Page.navigate", {"url": apply_url}, 2)
            _, cid = await _wait_for_load(
                ws, asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS, 3,
            )
            result = await _call(ws, "Runtime.evaluate", {
                "expression": fill_preflight_expression(payload),
                "awaitPromise": True, "returnByValue": True,
            }, cid)
    value = result.get("result", {}).get("result", {}).get("value")
    if result.get("error") or not isinstance(value, dict):
        raise ValueError("upwork_proposal_preflight_mismatch")
    return validate_preflight(value, payload)


def validate_preflight(snapshot: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Require an exact filled-form readback and return no proposal copy."""
    if not isinstance(snapshot, dict) or set(snapshot) != _SNAPSHOT_KEYS:
        raise ValueError("upwork_proposal_preflight_mismatch")
    terms = payload.get("terms") if isinstance(payload, dict) else None
    if not isinstance(terms, dict):
        raise ValueError("upwork_proposal_preflight_mismatch")
    job_id = payload.get("job_id")
    url = urlsplit(str(snapshot.get("form_url") or ""))
    required = terms.get("required_connects")
    expected = {
        "job_id": job_id,
        "required_connects": required,
        "bid_usd": terms.get("bid_usd"),
        "duration_label": _duration_label(terms.get("delivery_days")),
        "cover_letter": payload.get("cover_letter"),
        "screening_answers": payload.get("screening_answers"),
        "attachments": payload.get("attachments"),
    }
    if (
        not isinstance(job_id, str) or not job_id
        or url.scheme != "https" or url.netloc != "www.upwork.com"
        or f"/ab/proposals/job/{job_id}/apply" not in url.path
        or any(snapshot.get(key) != value for key, value in expected.items())
        or snapshot.get("submit_enabled") is not True
        or snapshot.get("validation_errors") != []
        or not isinstance(snapshot.get("submit_label"), str)
        or not re.search(rf"\b{required}\s+Connects\b", snapshot["submit_label"], re.IGNORECASE)
    ):
        raise ValueError("upwork_proposal_preflight_mismatch")
    evidence = hashlib.sha256(json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    return {
        "ready": True,
        "job_id": job_id,
        "required_connects": required,
        "evidence_sha256": evidence,
    }
