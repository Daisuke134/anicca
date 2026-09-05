#!/usr/bin/env python3
"""Buyer-bound, replay-safe Coconala cancellation request adapter."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import importlib.util
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlsplit

import websockets


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    import coconala_queue_snapshot as collector
except ModuleNotFoundError:
    collector = _load_local("coconala_queue_snapshot")


REASON = "出品者の都合で提供できなくなった"
DETAIL = (
    "長期間ご連絡できず、取引の継続が困難となったため、購入者様のご希望に沿って"
    "キャンセルを申請いたします。この度はご迷惑をおかけし、申し訳ございませんでした。"
)
CANCEL_REQUEST = re.compile(r"(?:キャンセル|取消).{0,30}(?:手続|申請|お願い|希望)", re.DOTALL)


class CancellationContract(NamedTuple):
    talkroom_id: str
    talkroom_url: str
    feedback_sha256: str
    feedback_message_ids: tuple[str, ...]
    feedback_text: str
    reason: str
    detail: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"\s+", "", _text(value))


def _message_id(value: Any) -> str:
    return _text(value).removeprefix("message:")


def validate_contract(queue: dict[str, Any], requirements: dict[str, Any]) -> CancellationContract:
    room = _text(queue.get("talkroom_id"))
    url = _text(queue.get("marketplace_url") or queue.get("talkroom_url"))
    parsed = urlsplit(url)
    feedback = _text(queue.get("buyer_feedback_sha256"))
    requirement_feedback = _text(requirements.get("feedback_sha256"))
    queue_ids = tuple(_message_id(value) for value in queue.get("buyer_feedback_message_identities") or [])
    requirement_ids = tuple(_message_id(value) for value in requirements.get("feedback_message_identities") or [])
    feedback_text = _text(requirements.get("feedback_text"))
    if (
        not re.fullmatch(r"[0-9]+", room)
        or parsed.scheme != "https"
        or parsed.hostname != "coconala.com"
        or parsed.path.rstrip("/") != f"/talkrooms/{room}"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("talkroom_url_not_canonical")
    if (
        requirements.get("talkroom_id") != room
        or not re.fullmatch(r"[a-f0-9]{64}", feedback)
        or feedback != requirement_feedback
        or not queue_ids
        or queue_ids != requirement_ids
    ):
        raise ValueError("buyer_feedback_binding_invalid")
    if not CANCEL_REQUEST.search(feedback_text):
        raise ValueError("buyer_cancellation_not_requested")
    return CancellationContract(room, url, feedback, queue_ids, feedback_text, REASON, DETAIL)


def _buyer_tail_matches(state: dict[str, Any], contract: CancellationContract) -> bool:
    messages = state.get("buyer_messages")
    if not isinstance(messages, list) or len(messages) < len(contract.feedback_message_ids):
        return False
    tail = messages[-len(contract.feedback_message_ids):]
    ids = tuple(_message_id(row.get("message_id")) for row in tail if isinstance(row, dict))
    text = "\n".join(_text(row.get("text")) for row in tail if isinstance(row, dict))
    return ids == contract.feedback_message_ids and _normalized(text) == _normalized(contract.feedback_text)


def matching_cancellation(state: dict[str, Any], contract: CancellationContract) -> bool:
    return (
        state.get("url") == contract.talkroom_url
        and state.get("transaction_state") == "取引中"
        and state.get("formal_delivery_control_checked") is False
        and state.get("cancel_control_present") is False
        and state.get("cancellation_pending") is True
        and _normalized(state.get("cancellation_reason_observed")) == _normalized(contract.reason)
        and _normalized(state.get("cancellation_detail_observed")) == _normalized(contract.detail)
    )


def ready_to_send(state: dict[str, Any], contract: CancellationContract) -> bool:
    return (
        state.get("url") == contract.talkroom_url
        and state.get("transaction_state") == "取引中"
        and state.get("formal_delivery_control_checked") is False
        and state.get("cancel_control_present") is True
        and _buyer_tail_matches(state, contract)
    )


def browser_state_expression(reason: str, detail: str) -> str:
    reason_json, detail_json = json.dumps(reason, ensure_ascii=False), json.dumps(detail, ensure_ascii=False)
    return f'''(()=>{{
      const formal=document.querySelector('.d-messageFormButtonArea_item-deliveryCheck input[type="checkbox"]');
      const step=(document.querySelector('.d-talkroomStep_label-current')?.innerText||'').trim();
      const cancel=[...document.querySelectorAll('a,button')].find(e=>(e.innerText||'').trim()==='取引をキャンセルリクエストする'&&e.offsetParent!==null);
      const buyers=[...document.querySelectorAll('.d-talkroomMessage.d-talkroomMessage-isOthers')].map(m=>({{
        message_id:m.id||m.getAttribute('data-message-id')||'',
        text:(m.querySelector('.d-normalMessage')?.innerText||'').trim()
      }}));
      const body=document.body.innerText||'';
      const pending=!cancel&&/キャンセルリクエスト(?:を送信しました|が送信されました|中)/.test(body);
      return {{
        url:location.origin+location.pathname,
        transaction_state:step==='進行中'?'取引中':step,
        formal_delivery_control_checked:formal?.checked===true,
        cancel_control_present:!!cancel,
        buyer_messages:buyers,
        cancellation_pending:pending,
        cancellation_reason_observed:pending&&body.includes({reason_json})?{reason_json}:'',
        cancellation_detail_observed:pending&&body.includes({detail_json})?{detail_json}:''
      }};
    }})()'''


def cancel_send_button_expression() -> str:
    return '''(()=>{const modal=[...document.querySelectorAll('.modal-content,[role=dialog]')].find(x=>x.offsetParent!==null&&(x.innerText||'').includes('キャンセルリクエスト'));const e=modal?[...modal.querySelectorAll('button')].find(x=>(x.innerText||'').trim()==='送信する'&&x.offsetParent!==null&&!x.disabled&&!x.classList.contains('is-disabled')):null;if(!e)return null;const formal=document.querySelector('.d-messageFormButtonArea_item-deliveryCheck input[type="checkbox"]');if(!formal||formal.checked)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return{x:r.left+r.width/2,y:r.top+r.height/2}})()'''


def cancel_form_configuration_expression(reason: str, detail: str) -> str:
    reason_json, detail_json = json.dumps(reason, ensure_ascii=False), json.dumps(detail, ensure_ascii=False)
    return f'''(()=>{{
      const modal=[...document.querySelectorAll('.modal-content,[role=dialog]')].find(e=>e.offsetParent!==null&&(e.innerText||'').includes('キャンセルリクエスト'));
      const select=modal?.querySelector('select'); const textarea=modal?.querySelector('textarea');
      const option=select?[...select.options].find(o=>(o.textContent||'').trim()==={reason_json}):null;
      if(!select||!textarea||!option)return false;
      const selectSetter=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;
      selectSetter.call(select,option.value);
      select.dispatchEvent(new Event('input',{{bubbles:true}}));
      select.dispatchEvent(new Event('change',{{bubbles:true}}));
      const textareaSetter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
      textareaSetter.call(textarea,{detail_json});
      textarea.dispatchEvent(new InputEvent('input',{{bubbles:true,inputType:'insertText'}}));
      textarea.dispatchEvent(new Event('change',{{bubbles:true}}));
      return true;
    }})()'''


def intent_is_reconcile_only(intent: dict[str, Any], effect_key: str) -> bool:
    return intent.get("effect_key") == effect_key and intent.get("phase") in {
        "click_started", "verified",
    }


def cancellation_initial_action(
    intent: dict[str, Any], effect_key: str, state: dict[str, Any], contract: CancellationContract,
) -> str:
    if matching_cancellation(state, contract):
        return "dedupe"
    if intent_is_reconcile_only(intent, effect_key):
        return "retry" if ready_to_send(state, contract) else "reconcile_unknown"
    return "send"


def cancel_send_button_click_expression() -> str:
    return '''(()=>{const modal=[...document.querySelectorAll('.modal-content,[role=dialog]')].find(x=>x.offsetParent!==null&&(x.innerText||'').includes('キャンセルリクエスト'));const e=modal?[...modal.querySelectorAll('button')].find(x=>(x.innerText||'').trim()==='送信する'&&x.offsetParent!==null&&!x.disabled&&!x.classList.contains('is-disabled')):null;if(!e)return false;const formal=document.querySelector('.d-messageFormButtonArea_item-deliveryCheck input[type="checkbox"]');if(!formal||formal.checked)return false;e.click();return true})()'''


class Session:
    def __init__(self, websocket: Any):
        self.websocket = websocket
        self.request_id = 0

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.request_id += 1
        return await collector.call(self.websocket, self.request_id, method, params or {})

    async def evaluate(self, expression: str, *, user_gesture: bool = False) -> Any:
        params: dict[str, Any] = {
            "expression": expression, "returnByValue": True, "awaitPromise": True,
        }
        if user_gesture:
            params["userGesture"] = True
        result = await self.call("Runtime.evaluate", params)
        if result.get("exceptionDetails"):
            raise RuntimeError("cancellation_browser_evaluate_failed")
        return result.get("result", {}).get("value")


async def _wait(session: Session, expression: str, predicate: Any, timeout: float) -> dict[str, Any]:
    deadline, last = time.monotonic() + timeout, {}
    while time.monotonic() < deadline:
        value = await session.evaluate(expression)
        if isinstance(value, dict):
            last = value
            if predicate(value):
                return value
        await asyncio.sleep(0.5)
    raise RuntimeError(f"cancellation_readback_timeout:{json.dumps({k: last.get(k) for k in ('url','transaction_state','formal_delivery_control_checked','cancel_control_present','cancellation_pending')}, separators=(',', ':'))}")


async def _click(
    session: Session, selector_expression: str, before_dispatch: Any = None, *, dispatch: bool = True,
) -> None:
    deadline, point = time.monotonic() + 10, None
    while time.monotonic() < deadline and not isinstance(point, dict):
        point = await session.evaluate(selector_expression)
        if not isinstance(point, dict):
            await asyncio.sleep(0.25)
    if not isinstance(point, dict):
        raise RuntimeError("cancellation_control_not_clickable")
    if before_dispatch is not None:
        before_dispatch()
    if not dispatch:
        return
    for event in ("mouseMoved", "mousePressed", "mouseReleased"):
        params: dict[str, Any] = {"type": event, "x": point["x"], "y": point["y"]}
        if event != "mouseMoved":
            params.update(button="left", clickCount=1)
        await session.call("Input.dispatchMouseEvent", params)


async def submit(ws_url: str, contract: CancellationContract, timeout: float, *,
                 intent_path: Path, reconcile_only: bool = False,
                 previous_intent: dict[str, Any] | None = None) -> tuple[dict[str, Any], bytes, bool]:
    expression = browser_state_expression(contract.reason, contract.detail)
    effect_key = hashlib.sha256(f"coconala:cancel:{contract.talkroom_id}:{contract.feedback_sha256}".encode()).hexdigest()
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=64 * 1024 * 1024) as ws:
        session = Session(ws)
        await session.call("Page.enable")
        initial = await _wait(session, expression, lambda value: ready_to_send(value, contract) or matching_cancellation(value, contract), timeout)
        sent = False
        initial_intent = previous_intent
        if initial_intent is None:
            initial_intent = {"effect_key": effect_key, "phase": "click_started"} if reconcile_only else {}
        action = cancellation_initial_action(initial_intent, effect_key, initial, contract)
        if action == "reconcile_unknown":
            raise RuntimeError("cancellation_reconcile_unknown")
        if action != "dedupe":
            await _click(session, '''(()=>{const e=[...document.querySelectorAll('a,button')].find(x=>(x.innerText||'').trim()==='取引をキャンセルリクエストする'&&x.offsetParent!==null);if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return{x:r.left+r.width/2,y:r.top+r.height/2}})()''')
            configured = await session.evaluate(
                cancel_form_configuration_expression(contract.reason, contract.detail)
            )
            if configured is not True:
                raise RuntimeError("cancellation_form_not_configurable")
            def mark_started() -> None:
                intent = json.loads(intent_path.read_text(encoding="utf-8"))
                intent["phase"] = "click_started"
                intent["effect_started_at"] = datetime.now(timezone.utc).isoformat()
                collector.atomic_json(intent_path, intent)

            await _click(session, cancel_send_button_expression(), mark_started, dispatch=False)
            if await session.evaluate(cancel_send_button_click_expression(), user_gesture=True) is not True:
                raise RuntimeError("cancellation_send_not_clickable")
            sent = True
        verified = await _wait(session, expression, lambda value: matching_cancellation(value, contract), timeout)
        screenshot = await session.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        return verified, base64.b64decode(screenshot["data"]), sent


def persist(evidence_dir: Path, contract: CancellationContract, state: dict[str, Any], screenshot: bytes, sent: bool) -> dict[str, Any]:
    if not matching_cancellation(state, contract):
        raise RuntimeError("cancellation_official_readback_missing")
    collector.secure_directory(evidence_dir)
    screenshot_path = evidence_dir / "cancellation-readback.png"
    live_path = evidence_dir / "cancellation-live-dom.json"
    evidence_path = evidence_dir / "cancellation-evidence.json"
    collector.secure_write_bytes(screenshot_path, screenshot)
    captured = datetime.now(timezone.utc).isoformat()
    effect_key = hashlib.sha256(f"coconala:cancel:{contract.talkroom_id}:{contract.feedback_sha256}".encode()).hexdigest()
    live = {
        "url": contract.talkroom_url, "talkroom_id": contract.talkroom_id,
        "feedback_sha256": contract.feedback_sha256, "cancellation_pending": True,
        "reason": contract.reason, "detail_sha256": hashlib.sha256(contract.detail.encode()).hexdigest(),
        "formal_delivery_control_checked": False, "captured_at": captured,
    }
    collector.atomic_json(live_path, live)
    evidence = {
        "ok": True, "action": "cancellation_request", "effect_key": effect_key,
        "talkroom_id": contract.talkroom_id, "feedback_sha256": contract.feedback_sha256,
        "url": contract.talkroom_url, "send_performed": sent, "deduplicated": not sent,
        "formal_delivery_checkbox": False, "readback": 1, "captured_at": captured,
        "live_dom_path": str(live_path), "screenshot_path": str(screenshot_path),
    }
    collector.atomic_json(evidence_path, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-item", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--default-tab-helper", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    queue = json.loads(args.queue_item.read_text(encoding="utf-8"))
    requirements = json.loads((args.project_root / "requirements/live-buyer-reply.json").read_text(encoding="utf-8"))
    contract = validate_contract(queue, requirements)
    effect_key = hashlib.sha256(
        f"coconala:cancel:{contract.talkroom_id}:{contract.feedback_sha256}".encode()
    ).hexdigest()
    intent_path = args.project_root / "delivery/cancellation-intent.json"
    previous = json.loads(intent_path.read_text(encoding="utf-8")) if intent_path.is_file() else {}
    reconcile_only = intent_is_reconcile_only(previous, effect_key)
    collector.atomic_json(intent_path, {
        "version": 1, "action": "cancellation_request", "effect_key": effect_key,
        "target": contract.talkroom_url, "talkroom_id": contract.talkroom_id,
        "feedback_sha256": contract.feedback_sha256, "reason": contract.reason,
        "detail_sha256": hashlib.sha256(contract.detail.encode()).hexdigest(),
        "formal_delivery_checkbox": False,
        "phase": "click_started" if reconcile_only else "prepared",
    })
    with collector.DefaultTab(args.default_tab_helper, contract.talkroom_url) as tab:
        state, screenshot, sent = asyncio.run(submit(
            tab.ws, contract, args.timeout, intent_path=intent_path,
            reconcile_only=reconcile_only,
            previous_intent=previous,
        ))
    evidence = persist(args.evidence_dir.resolve(), contract, state, screenshot, sent)
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    intent["phase"] = "verified"
    intent["evidence_path"] = str(args.evidence_dir.resolve() / "cancellation-evidence.json")
    collector.atomic_json(intent_path, intent)
    print(json.dumps({"ok": True, "evidence": evidence}, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
