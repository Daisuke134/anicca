#!/usr/bin/env python3
"""Deterministic, queue-bound Coconala paid progress delivery over CDP."""

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
from playwright.async_api import async_playwright


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    import coconala_queue_snapshot as collector
except ModuleNotFoundError:  # imported directly by unit-test loaders
    collector = _load_local("coconala_queue_snapshot")


class ProgressContract(NamedTuple):
    talkroom_id: str
    talkroom_url: str
    project_root: Path
    artifact_path: Path
    artifact_version: str
    acceptance_path: Path
    acceptance_delta: list[str]
    package_sha256: str
    message: str


class AnswerContract(NamedTuple):
    """Message-only reply in a paid talkroom: the buyer asked something that a
    new artifact version cannot answer (schedule, confirmation, phase change)."""
    talkroom_id: str
    talkroom_url: str
    message: str


def validate_answer_contract(queue: dict[str, Any], answer: dict[str, Any]) -> AnswerContract:
    """Fail closed unless the queue item and the builder's answer agree."""
    if not isinstance(queue, dict) or not isinstance(answer, dict):
        raise ValueError("queue_or_answer_not_object")
    if answer.get("version") != 1 or answer.get("status") != "answer":
        raise ValueError("answer_payload_invalid")
    message = str(answer.get("message") or "").strip()
    if not message or len(message) > 4000:
        raise ValueError("answer_message_empty_or_oversized")
    talkroom_id = str(queue.get("talkroom_id") or "").strip()
    talkroom_url = str(queue.get("marketplace_url") or queue.get("talkroom_url") or "").strip()
    parsed = urlsplit(talkroom_url)
    if (
        not re.fullmatch(r"[0-9]+", talkroom_id)
        or parsed.scheme != "https"
        or parsed.hostname != "coconala.com"
        or parsed.path.rstrip("/") != f"/talkrooms/{talkroom_id}"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("talkroom_url_not_canonical")
    return AnswerContract(
        talkroom_id=talkroom_id,
        talkroom_url=f"https://coconala.com/talkrooms/{talkroom_id}",
        message=message,
    )


def _inside(child: Path, parent: Path, error: str) -> Path:
    resolved = child.expanduser().resolve()
    try:
        resolved.relative_to(parent)
    except ValueError as exc:
        raise ValueError(error) from exc
    return resolved


def _nonempty_strings(value: Any, error: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(error)
    result = [str(item).strip() for item in value if isinstance(item, str) and item.strip()]
    if len(result) != len(value) or not result:
        raise ValueError(error)
    return result


def _sha256_file(target: Path) -> str:
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_progress_contract(
    queue: dict[str, Any], manifest: dict[str, Any]
) -> ProgressContract:
    """Fail closed unless queue, builder manifest, and real files agree exactly."""
    if not isinstance(queue, dict) or not isinstance(manifest, dict):
        raise ValueError("queue_or_manifest_not_object")
    if queue.get("delivery_action") != "progress":
        raise ValueError("delivery_action_not_progress")
    if queue.get("formal_delivery_checkbox") is not False:
        raise ValueError("queue_formal_delivery_not_off")
    progress = queue.get("progress_payload")
    if not isinstance(progress, dict) or progress.get("mode") != "progress":
        raise ValueError("progress_payload_invalid")
    if progress.get("formal_delivery_checkbox") is not False:
        raise ValueError("progress_formal_delivery_not_off")
    if progress.get("buyer_visible") is not True:
        raise ValueError("progress_not_buyer_visible")
    evidence = queue.get("delivery_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("delivery_evidence_missing")
    if manifest.get("status") != "ok" or manifest.get("acceptance_status") != "PASS":
        raise ValueError("builder_manifest_not_accepted")

    binding_fields = (
        "project_root",
        "artifact_path",
        "artifact_version",
        "acceptance_evidence_path",
        "acceptance_status",
        "acceptance_delta",
        "package_sha256",
    )
    for key in binding_fields:
        if evidence.get(key) != manifest.get(key):
            raise ValueError(f"queue_manifest_mismatch:{key}")

    project_root = Path(str(manifest.get("project_root") or "")).expanduser().resolve()
    if not project_root.is_dir():
        raise ValueError("project_root_missing")
    artifact_path = _inside(
        Path(str(manifest.get("artifact_path") or "")), project_root, "artifact_outside_project_root"
    )
    acceptance_path = _inside(
        Path(str(manifest.get("acceptance_evidence_path") or "")),
        project_root,
        "acceptance_outside_project_root",
    )
    if not artifact_path.is_file() or artifact_path.stat().st_size <= 0:
        raise ValueError("artifact_missing_or_empty")
    if not acceptance_path.is_file() or acceptance_path.stat().st_size <= 0:
        raise ValueError("acceptance_missing_or_empty")
    package_sha256 = str(manifest.get("package_sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", package_sha256):
        raise ValueError("package_sha256_invalid")
    if _sha256_file(artifact_path) != package_sha256:
        raise ValueError("artifact_sha256_mismatch")

    artifact_version = str(manifest.get("artifact_version") or "").strip()
    if not artifact_version or progress.get("artifact_version") != artifact_version:
        raise ValueError("progress_version_mismatch")
    acceptance_delta = _nonempty_strings(manifest.get("acceptance_delta"), "acceptance_delta_invalid")
    if progress.get("acceptance_delta") != acceptance_delta:
        raise ValueError("progress_delta_mismatch")
    _nonempty_strings(progress.get("blockers"), "progress_blockers_invalid")

    talkroom_id = str(queue.get("talkroom_id") or "").strip()
    talkroom_url = str(queue.get("marketplace_url") or queue.get("talkroom_url") or "").strip()
    parsed = urlsplit(talkroom_url)
    if (
        not re.fullmatch(r"[0-9]+", talkroom_id)
        or parsed.scheme != "https"
        or parsed.hostname != "coconala.com"
        or parsed.path.rstrip("/") != f"/talkrooms/{talkroom_id}"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("talkroom_url_not_canonical")
    talkroom_url = f"https://coconala.com/talkrooms/{talkroom_id}"

    base_message = str(progress.get("message") or "").strip()
    if not base_message:
        raise ValueError("progress_message_empty")
    binding = (
        f"添付: {artifact_path.name}（{artifact_version}）\n"
        f"パッケージSHA-256: {package_sha256}"
    )
    message = base_message if binding in base_message else f"{base_message}\n\n{binding}"
    return ProgressContract(
        talkroom_id=talkroom_id,
        talkroom_url=talkroom_url,
        project_root=project_root,
        artifact_path=artifact_path,
        artifact_version=artifact_version,
        acceptance_path=acceptance_path,
        acceptance_delta=acceptance_delta,
        package_sha256=package_sha256,
        message=message,
    )


def upload_ready(state: dict[str, Any]) -> bool:
    return (
        state.get("formal_delivery_control_present") is True
        and state.get("formal_delivery_control_checked") is False
        and state.get("textarea_present") is True
        and state.get("form_has_artifact") is True
    )


def send_ready(state: dict[str, Any], message: str) -> bool:
    return (
        upload_ready(state)
        and state.get("textarea_value") == message
        and state.get("send_button_present") is True
        and state.get("send_button_disabled") is False
    )


def matching_seller_message(
    state: dict[str, Any], artifact_basename: str, package_sha256: str
) -> dict[str, Any] | None:
    messages = state.get("seller_messages")
    if not isinstance(messages, list):
        return None
    for row in reversed(messages):
        if not isinstance(row, dict):
            continue
        attachments = row.get("attachments")
        if (
            isinstance(attachments, list)
            and artifact_basename in attachments
            and package_sha256 in str(row.get("text") or "")
        ):
            return row
    return None


def _normalized_text(value: Any) -> str:
    # DOM innerText injects arbitrary whitespace/newlines; whitespace carries
    # no meaning for matching Japanese text, so drop it entirely.
    return re.sub(r"\s+", "", str(value or ""))


def matching_seller_text(state: dict[str, Any], message: str) -> dict[str, Any] | None:
    """Find our answer among seller messages by whitespace-normalized text."""
    needle = _normalized_text(message)[:120]
    if not needle:
        return None
    messages = state.get("seller_messages")
    if not isinstance(messages, list):
        return None
    for row in reversed(messages):
        if isinstance(row, dict) and needle in _normalized_text(row.get("text")):
            return row
    return None


def answer_send_ready(state: dict[str, Any], message: str) -> bool:
    return (
        state.get("formal_delivery_control_present") is True
        and state.get("formal_delivery_control_checked") is False
        and state.get("textarea_present") is True
        and state.get("textarea_value") == message
        and state.get("send_button_present") is True
        and state.get("send_button_disabled") is False
    )


async def deliver_answer(
    ws_url: str,
    contract: AnswerContract,
    *,
    page_timeout: float,
    send_timeout: float,
    post_timeout: float,
) -> tuple[dict[str, Any], bytes, bool]:
    expression = browser_state_expression("__no_artifact__")
    async with websockets.connect(
        ws_url, ping_interval=None, open_timeout=10, max_size=64 * 1024 * 1024
    ) as ws:
        session = CdpSession(ws, ws_url, contract.talkroom_url)
        await session.call("Page.enable")
        await session.call("DOM.enable")
        initial = await _wait_for_state(
            session,
            expression,
            lambda state: (
                state.get("url") == contract.talkroom_url
                and state.get("form_present") is True
                and state.get("textarea_present") is True
                and state.get("formal_delivery_control_present") is True
                and state.get("formal_delivery_control_checked") is False
            ),
            page_timeout,
            "paid_answer_talkroom_not_ready",
        )
        send_performed = False
        if matching_seller_text(initial, contract.message) is None:
            await _fill_message(session, contract.message)
            await _wait_for_state(
                session,
                expression,
                lambda state: answer_send_ready(state, contract.message),
                send_timeout,
                "paid_answer_send_not_ready",
            )
            await _click_send(session)
            send_performed = True
        verified = await _wait_for_state(
            session,
            expression,
            lambda state: (
                state.get("url") == contract.talkroom_url
                and state.get("formal_delivery_control_checked") is False
                and matching_seller_text(state, contract.message) is not None
            ),
            post_timeout,
            "paid_answer_post_send_not_observed",
        )
        screenshot = await session.call(
            "Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False}
        )
        return verified, base64.b64decode(screenshot["data"]), send_performed


def persist_answer_evidence(
    evidence_dir: Path,
    contract: AnswerContract,
    verified: dict[str, Any],
    screenshot: bytes,
    send_performed: bool,
) -> dict[str, Any]:
    matched = matching_seller_text(verified, contract.message)
    if matched is None:
        raise RuntimeError("paid_answer_verified_message_missing")
    collector.secure_directory(evidence_dir)
    screenshot_path = (evidence_dir / "paid-queue-screenshot.png").resolve()
    live_dom_path = (evidence_dir / "paid-queue-live-dom.json").resolve()
    manifest_path = evidence_dir / "paid-queue-evidence.json"
    collector.secure_write_bytes(screenshot_path, screenshot)
    captured_at = datetime.now(timezone.utc).isoformat()
    outer = {
        "sent": True,
        "mode": "answer",
        "send_performed": send_performed,
        "deduplicated": not send_performed,
        "formal_delivery_checkbox": False,
        "captured_at": captured_at,
        "talkroom_id": contract.talkroom_id,
        "message_sha256": hashlib.sha256(contract.message.encode("utf-8")).hexdigest(),
        "screenshot_path": str(screenshot_path),
        "live_dom_path": str(live_dom_path),
    }
    live = {
        "url": contract.talkroom_url,
        "sent": True,
        "mode": "answer",
        "send_performed": send_performed,
        "deduplicated": not send_performed,
        "formal_delivery_control_checked": False,
        "captured_at": captured_at,
        "latest_seller_message": str(matched.get("text") or "")[:2000],
    }
    collector.atomic_json(live_dom_path, live)
    collector.atomic_json(manifest_path, outer)
    return outer


def browser_state_expression(artifact_basename: str) -> str:
    encoded = json.dumps(artifact_basename, ensure_ascii=False)
    return f'''(()=>{{
      const form=document.querySelector('.d-messageForm');
      const textarea=document.querySelector('textarea[placeholder="メッセージを入力"]');
      const formal=document.querySelector('.d-messageFormButtonArea_item-deliveryCheck input[type="checkbox"]');
      const buttons=form?[...form.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()==='送信'):[];
      const send=buttons[buttons.length-1]||null;
      const selectedFileNames=form?[...form.querySelectorAll('input[type=file]')].flatMap(input=>[...(input.files||[])]).map(file=>file.name):[];
      const renderedFileNames=form?[...form.querySelectorAll('.d-partOfFilename')].map(x=>(x.textContent||'').replace(/\\s+/g,'')):[];
      const sellers=[...document.querySelectorAll('.d-talkroomMessage')].map(m=>{{
        const side=m.classList.contains('d-talkroomMessage-isOthers')?'buyer':(((m.innerText||'').trim().startsWith('自分'))?'seller':'system');
        const text=(m.querySelector('.d-normalMessage')?.innerText||'').trim();
        const attachments=[...m.querySelectorAll('.d-talkroomMessage_attachedFilesItem')].map(f=>(f.querySelector('.tooltip-content')?.innerText||f.querySelector('.d-attachedFileName')?.innerText||'').replace(/\\s+/g,' ').trim()).filter(Boolean);
        return {{side,text,attachments}};
      }}).filter(x=>x.side==='seller');
      return {{
        url:location.origin+location.pathname,
        title:document.title,
        form_present:!!form,
        textarea_present:!!textarea,
        textarea_value:textarea?.value||'',
        formal_delivery_control_present:!!formal,
        formal_delivery_control_checked:formal?.checked===true,
        form_has_artifact:!!form&&(
          selectedFileNames.includes({encoded})||
          renderedFileNames.includes({encoded})||
          ((form.innerText||'')+(form.innerHTML||'')).includes({encoded})
        ),
        selected_file_names:selectedFileNames,
        rendered_file_names:renderedFileNames,
        send_button_present:!!send,
        send_button_disabled:send?.disabled!==false,
        seller_messages:sellers
      }};
    }})()'''


class CdpSession:
    def __init__(self, ws: Any, ws_url: str, talkroom_url: str):
        self.ws = ws
        self.ws_url = ws_url
        self.talkroom_url = talkroom_url
        self.request_id = 0

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.request_id += 1
        return await collector.call(self.ws, self.request_id, method, params or {})

    async def evaluate(self, expression: str) -> Any:
        result = await self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if result.get("exceptionDetails"):
            raise RuntimeError("browser_evaluate_failed")
        return result.get("result", {}).get("value")


async def _wait_for_state(
    session: CdpSession,
    expression: str,
    predicate: Any,
    timeout_seconds: float,
    error: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        value = await session.evaluate(expression)
        if isinstance(value, dict):
            last = value
            if predicate(value):
                return value
        await asyncio.sleep(0.5)
    safe = {
        key: last.get(key)
        for key in (
            "url",
            "form_present",
            "textarea_present",
            "formal_delivery_control_present",
            "formal_delivery_control_checked",
            "form_has_artifact",
            "send_button_present",
            "send_button_disabled",
        )
    }
    raise RuntimeError(f"{error}:{json.dumps(safe, separators=(',', ':'))}")


async def _fill_message(session: CdpSession, message: str) -> None:
    cleared = await session.evaluate('''(()=>{
      const textarea=document.querySelector('textarea[placeholder="メッセージを入力"]');
      if(!textarea)return false;
      textarea.focus();
      const setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
      setter.call(textarea,'');
      textarea.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'deleteContentBackward'}));
      return textarea===document.activeElement;
    })()''')
    if cleared is not True:
        raise RuntimeError("message_textarea_not_focusable")
    await session.call("Input.insertText", {"text": message})


async def _upload(session: CdpSession, artifact_path: Path) -> None:
    endpoint = urlsplit(session.ws_url)
    cdp_url = f"{'https' if endpoint.scheme == 'wss' else 'http'}://{endpoint.netloc}"
    target_id = endpoint.path.rsplit("/", 1)[-1]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(cdp_url)
        page = None
        for context in browser.contexts:
            for candidate in context.pages:
                if candidate.url.split("#", 1)[0] != session.talkroom_url:
                    continue
                candidate_session = await context.new_cdp_session(candidate)
                try:
                    info = await candidate_session.send("Target.getTargetInfo")
                finally:
                    await candidate_session.detach()
                if info.get("targetInfo", {}).get("targetId") == target_id:
                    page = candidate
                    break
            if page is not None:
                break
        if page is None:
            raise RuntimeError("paid_progress_talkroom_page_missing")
        await page.locator(".d-messageForm .isPC input[type=file]").set_input_files(
            str(artifact_path)
        )


async def _click_send(session: CdpSession) -> None:
    button = await session.evaluate('''(()=>{
      const form=document.querySelector('.d-messageForm');
      const buttons=form?[...form.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()==='送信'&&!x.disabled):[];
      const target=buttons[buttons.length-1]||null;
      const formal=document.querySelector('.d-messageFormButtonArea_item-deliveryCheck input[type="checkbox"]');
      if(!target||!formal||formal.checked)return null;
      target.scrollIntoView({block:'center'});
      const rect=target.getBoundingClientRect();
      return {x:rect.left+rect.width/2,y:rect.top+rect.height/2};
    })()''')
    if not isinstance(button, dict):
        raise RuntimeError("paid_progress_send_button_not_clickable")
    for event_type in ("mouseMoved", "mousePressed", "mouseReleased"):
        params: dict[str, Any] = {"type": event_type, "x": button["x"], "y": button["y"]}
        if event_type != "mouseMoved":
            params.update({"button": "left", "clickCount": 1})
        await session.call("Input.dispatchMouseEvent", params)


async def deliver_progress(
    ws_url: str,
    contract: ProgressContract,
    *,
    page_timeout: float,
    upload_timeout: float,
    send_timeout: float,
    post_timeout: float,
) -> tuple[dict[str, Any], bytes, bool]:
    expression = browser_state_expression(contract.artifact_path.name)
    async with websockets.connect(
        ws_url, ping_interval=None, open_timeout=10, max_size=64 * 1024 * 1024
    ) as ws:
        session = CdpSession(ws, ws_url, contract.talkroom_url)
        await session.call("Page.enable")
        await session.call("DOM.enable")
        initial = await _wait_for_state(
            session,
            expression,
            lambda state: (
                state.get("url") == contract.talkroom_url
                and state.get("form_present") is True
                and state.get("textarea_present") is True
                and state.get("formal_delivery_control_present") is True
                and state.get("formal_delivery_control_checked") is False
            ),
            page_timeout,
            "paid_progress_talkroom_not_ready",
        )
        existing = matching_seller_message(
            initial, contract.artifact_path.name, contract.package_sha256
        )
        send_performed = False
        if existing is None:
            await _upload(session, contract.artifact_path)
            await _wait_for_state(
                session, expression, upload_ready, upload_timeout, "paid_progress_upload_not_ready"
            )
            await _fill_message(session, contract.message)
            await _wait_for_state(
                session,
                expression,
                lambda state: send_ready(state, contract.message),
                send_timeout,
                "paid_progress_send_not_ready",
            )
            await _click_send(session)
            send_performed = True

        verified = await _wait_for_state(
            session,
            expression,
            lambda state: (
                state.get("url") == contract.talkroom_url
                and state.get("formal_delivery_control_checked") is False
                and matching_seller_message(
                    state, contract.artifact_path.name, contract.package_sha256
                )
                is not None
            ),
            post_timeout,
            "paid_progress_post_send_not_observed",
        )
        screenshot = await session.call(
            "Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False}
        )
        return verified, base64.b64decode(screenshot["data"]), send_performed


def persist_evidence(
    evidence_dir: Path,
    contract: ProgressContract,
    verified: dict[str, Any],
    screenshot: bytes,
    send_performed: bool,
) -> dict[str, Any]:
    matched = matching_seller_message(
        verified, contract.artifact_path.name, contract.package_sha256
    )
    if matched is None:
        raise RuntimeError("paid_progress_verified_message_missing")
    collector.secure_directory(evidence_dir)
    screenshot_path = (evidence_dir / "paid-queue-screenshot.png").resolve()
    live_dom_path = (evidence_dir / "paid-queue-live-dom.json").resolve()
    manifest_path = evidence_dir / "paid-queue-evidence.json"
    collector.secure_write_bytes(screenshot_path, screenshot)
    captured_at = datetime.now(timezone.utc).isoformat()
    outer = {
        "sent": True,
        "send_performed": send_performed,
        "deduplicated": not send_performed,
        "formal_delivery_checkbox": False,
        "captured_at": captured_at,
        "talkroom_id": contract.talkroom_id,
        "artifact_basename": contract.artifact_path.name,
        "artifact_version": contract.artifact_version,
        "package_sha256": contract.package_sha256,
        "acceptance_delta": contract.acceptance_delta,
        "screenshot_path": str(screenshot_path),
        "live_dom_path": str(live_dom_path),
    }
    live = {
        "url": contract.talkroom_url,
        "sent": True,
        "send_performed": send_performed,
        "deduplicated": not send_performed,
        "formal_delivery_control_checked": False,
        "captured_at": captured_at,
        "latest_seller_attachment": {
            "filename": contract.artifact_path.name,
            "size_bytes": contract.artifact_path.stat().st_size,
            "message": str(matched.get("text") or ""),
        },
    }
    collector.atomic_json(live_dom_path, live)
    collector.atomic_json(manifest_path, outer)
    return outer


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-item", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--default-tab-helper", required=True, type=Path)
    parser.add_argument("--page-timeout", type=float, default=30)
    parser.add_argument("--upload-timeout", type=float, default=120)
    parser.add_argument("--send-timeout", type=float, default=120)
    parser.add_argument("--post-timeout", type=float, default=60)
    args = parser.parse_args()
    if (args.manifest is None) == (args.answer_file is None):
        raise SystemExit("exactly one of --manifest or --answer-file is required")
    queue = json.loads(args.queue_item.read_text(encoding="utf-8"))
    if args.answer_file is not None:
        answer = json.loads(args.answer_file.read_text(encoding="utf-8"))
        answer_contract = validate_answer_contract(queue, answer)
        with collector.DefaultTab(args.default_tab_helper, answer_contract.talkroom_url) as tab:
            verified, screenshot, send_performed = asyncio.run(
                deliver_answer(
                    tab.ws,
                    answer_contract,
                    page_timeout=args.page_timeout,
                    send_timeout=args.send_timeout,
                    post_timeout=args.post_timeout,
                )
            )
        evidence = persist_answer_evidence(
            args.evidence_dir.resolve(), answer_contract, verified, screenshot, send_performed
        )
        print(json.dumps({"ok": True, "evidence": evidence}, ensure_ascii=False, separators=(",", ":")))
        return 0
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    contract = validate_progress_contract(queue, manifest)
    with collector.DefaultTab(args.default_tab_helper, contract.talkroom_url) as tab:
        verified, screenshot, send_performed = asyncio.run(
            deliver_progress(
                tab.ws,
                contract,
                page_timeout=args.page_timeout,
                upload_timeout=args.upload_timeout,
                send_timeout=args.send_timeout,
                post_timeout=args.post_timeout,
            )
        )
    evidence = persist_evidence(
        args.evidence_dir.resolve(), contract, verified, screenshot, send_performed
    )
    print(json.dumps({"ok": True, "evidence": evidence}, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
