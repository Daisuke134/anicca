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
import shutil
import tempfile
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
except ModuleNotFoundError:  # imported directly by unit-test loaders
    collector = _load_local("coconala_queue_snapshot")

try:
    from buyer_voice import check_style, normalize_for_match
except ModuleNotFoundError:  # imported directly by unit-test loaders
    _buyer_voice = _load_local("buyer_voice")
    check_style = _buyer_voice.check_style
    normalize_for_match = _buyer_voice.normalize_for_match

try:
    import artifact_judge
except ModuleNotFoundError:  # imported directly by unit-test loaders
    artifact_judge = _load_local("artifact_judge")

try:
    import paid_direct as paid_direct_executor
except ModuleNotFoundError:  # imported directly by unit-test loaders
    paid_direct_executor = _load_local("paid_direct")

try:
    import predelivery_score
except ModuleNotFoundError:  # imported directly by unit-test loaders
    predelivery_score = _load_local("predelivery_score")

# EV1 instrumentation. Catches everything, not just ModuleNotFoundError: unlike the imports
# above, nothing here is load-bearing, so a broken trajectory.py must degrade to silence
# rather than stop a delivery. See artifact_judge for the same shim.
try:
    from trajectory import record as record_trajectory
except Exception:  # noqa: BLE001 - instrumentation may never break its host
    try:
        record_trajectory = _load_local("trajectory").record
    except Exception:  # noqa: BLE001
        def record_trajectory(**_kwargs: Any) -> None:  # type: ignore[misc]
            return None


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
    attachment_path: Path | None
    attachment_sha256: str | None


def validate_answer_contract(queue: dict[str, Any], answer: dict[str, Any]) -> AnswerContract:
    """Fail closed unless the queue item and the builder's answer agree."""
    if not isinstance(queue, dict) or not isinstance(answer, dict):
        raise ValueError("queue_or_answer_not_object")
    if answer.get("version") != 1 or answer.get("status") != "answer":
        raise ValueError("answer_payload_invalid")
    message = str(answer.get("message") or "").strip()
    if not message or len(message) > 4000:
        raise ValueError("answer_message_empty_or_oversized")
    violations = check_style(message)
    if violations:
        raise ValueError(f"buyer_style_violation:{violations[0]}")
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
    attachment_path = None
    attachment = answer.get("attachment")
    if attachment is not None:
        if not isinstance(attachment, dict) or set(attachment) != {"path", "filename", "sha256"}:
            raise ValueError("answer_attachment_invalid")
        raw = Path(str(attachment.get("path") or ""))
        filename = str(attachment.get("filename") or "").strip()
        digest = str(attachment.get("sha256") or "").strip()
        project_root = Path(str(queue.get("project_root") or "")).expanduser()
        evidence_root = project_root / "evidence"
        if (project_root.is_symlink() or evidence_root.is_symlink() or not project_root.is_dir()
                or raw.is_symlink() or not raw.is_file() or raw.name != filename
                or Path(filename).name != filename or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or _sha256_file(raw) != digest):
            raise ValueError("answer_attachment_invalid")
        attachment_path = raw.resolve()
        try:
            attachment_path.relative_to(evidence_root.resolve())
        except ValueError as error:
            raise ValueError("answer_attachment_invalid") from error
    return AnswerContract(
        talkroom_id=talkroom_id,
        talkroom_url=f"https://coconala.com/talkrooms/{talkroom_id}",
        message=message,
        attachment_path=attachment_path,
        attachment_sha256=digest if attachment_path else None,
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


def effect_keys(talkroom_id: str, message: str, attachment_sha256: str | None = None) -> dict[str, str]:
    """Stable, channel-specific identities; reply and file effects never dedupe each other."""
    keys = {
        "reply_effect_key": (
            f"coconala:reply:{talkroom_id}:{hashlib.sha256(message.encode('utf-8')).hexdigest()}"
        )
    }
    if attachment_sha256:
        keys["attachment_effect_key"] = f"coconala:attachment:{talkroom_id}:{attachment_sha256}"
    return keys


def snapshot_answer_attachment(contract: AnswerContract, evidence_dir: Path) -> tuple[AnswerContract, Path | None]:
    if contract.attachment_path is None:
        return contract, None
    collector.secure_directory(evidence_dir)
    snapshot_dir = Path(tempfile.mkdtemp(prefix=".paid-answer-upload-", dir=evidence_dir))
    snapshot_dir.chmod(0o700)
    snapshot = snapshot_dir / contract.attachment_path.name
    try:
        shutil.copyfile(contract.attachment_path, snapshot)
        snapshot.chmod(0o400)
        if _sha256_file(snapshot) != contract.attachment_sha256:
            raise ValueError("answer_attachment_changed_before_upload")
        return contract._replace(attachment_path=snapshot), snapshot_dir
    except Exception:
        shutil.rmtree(snapshot_dir, ignore_errors=True)
        raise


def validate_answer_attachment_authorization(
    queue: dict[str, Any], contract: AnswerContract,
) -> str:
    if contract.attachment_path is None or contract.attachment_sha256 is None:
        raise ValueError("answer_attachment_authorization_missing")
    root = Path(str(queue.get("project_root") or "")).expanduser()
    feedback = str(queue.get("buyer_feedback_sha256") or "").strip()
    if root.is_symlink() or not root.is_dir() or not re.fullmatch(r"[0-9a-f]{64}", feedback):
        raise ValueError("answer_attachment_authorization_invalid")
    root = root.resolve()
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    if str(state.get("talkroom_id") or "").strip() != contract.talkroom_id:
        raise ValueError("answer_attachment_talkroom_mismatch")
    intent = json.loads((root / "delivery/paid-remote-intent.json").read_text(encoding="utf-8"))
    result = json.loads((root / "delivery/paid-remote-result.json").read_text(encoding="utf-8"))
    digest = str(intent.get("desired_state_sha256") or "").strip()
    paid_direct_executor.paid_remote_result.resume_owner(root, feedback, digest)
    attachment = paid_direct_executor._validated_customer_attachment(
        root, result.get("customer_attachment")
    )
    if (result.get("customer_message") != contract.message or attachment is None
            or attachment["filename"] != contract.attachment_path.name
            or attachment["sha256"] != contract.attachment_sha256):
        raise ValueError("answer_attachment_authorization_mismatch")
    return digest


def validate_progress_contract(
    queue: dict[str, Any], manifest: dict[str, Any], *, revision_after_formal: bool = False
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
    if revision_after_formal and not (
        queue.get("revision_after_formal") is True
        and queue.get("talkroom_state") == "納品確認待ち"
        and queue.get("formal_delivery_observed") is True
    ):
        raise ValueError("revision_formal_state_not_observed")
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
    # An ordinary progress delivery exists BECAUSE blockers exist (delivery_cadence:
    # mode is progress only when the blocker list is non-empty), so the builder shape
    # always carries at least one and non-empty stays required. A revision redelivery
    # is the one legitimate exception: the artifact passed every gate and rides the
    # progress channel only because 納品確認待ち disabled the formal checkbox --
    # measured live 2026-08-08 22:04 (gig-pass-1786194006-85231, order 91000002), where
    # this line rejected a correct, complete v6 revision whose blockers were honestly
    # []. Empty LIST only; a missing key or None still fails closed either way.
    if not (revision_after_formal and progress.get("blockers") == []):
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
    # The attachment name and version help the buyer; the sha256 never did. It stays in the
    # evidence JSON and the ledger, which is where it is actually the proof.
    binding = f"添付: {artifact_path.name}（{artifact_version}）"
    message = base_message if binding in base_message else f"{base_message}\n\n{binding}"
    violations = check_style(message)
    if violations:
        raise ValueError(f"buyer_style_violation:{violations[0]}")
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


def upload_ready(state: dict[str, Any], *, revision_after_formal: bool = False) -> bool:
    return (
        (revision_after_formal or (
            state.get("formal_delivery_control_present") is True
            and state.get("formal_delivery_control_checked") is False
        ))
        and state.get("textarea_present") is True
        and state.get("form_has_artifact") is True
    )


def send_ready(
    state: dict[str, Any], message: str, *, revision_after_formal: bool = False
) -> bool:
    return (
        upload_ready(state, revision_after_formal=revision_after_formal)
        and state.get("textarea_value") == message
        and state.get("send_button_present") is True
        and state.get("send_button_disabled") is False
    )


def matching_seller_message(
    state: dict[str, Any], artifact_basename: str, message: str
) -> dict[str, Any] | None:
    """Identify our own progress delivery among the seller rows.

    Took package_sha256 as its third argument until the sha left the buyer's text. Keying
    on a string we no longer send would have made every progress delivery report itself as
    unsent -- the post-send wait would time out at paid_progress_post_send_not_observed and
    persist_evidence would raise paid_progress_verified_message_missing, on deliveries that
    in fact succeeded.

    So the key is now the message itself, exactly as the formal lane does it, and exactly
    as matching_seller_text already did for the answer lane: attachment name AND our own
    opening. Same strength, no dependency on text the buyer should never have seen.
    """
    expected = normalize_for_match(message)
    if not expected:
        return None
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
            and normalize_for_match(row.get("text")) == expected
        ):
            return row
    return None


def _normalized_text(value: Any) -> str:
    # DOM innerText injects arbitrary whitespace/newlines; whitespace carries
    # no meaning for matching Japanese text, so drop it entirely.
    return normalize_for_match(value)


def matching_seller_text(state: dict[str, Any], message: str) -> dict[str, Any] | None:
    """Find our answer among seller messages by whitespace-normalized text."""
    needle = _normalized_text(message)
    if not needle:
        return None
    messages = state.get("seller_messages")
    if not isinstance(messages, list):
        return None
    for row in reversed(messages):
        if isinstance(row, dict) and needle == _normalized_text(row.get("text")):
            return row
    return None


def answer_send_ready(state: dict[str, Any], message: str) -> bool:
    return (
        state.get("formal_delivery_control_checked") is False
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
    attachment_name = contract.attachment_path.name if contract.attachment_path else "__no_artifact__"
    expression = browser_state_expression(attachment_name)
    match = (lambda state: matching_seller_message(state, attachment_name, contract.message)
             if contract.attachment_path else matching_seller_text(state, contract.message))
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
                and state.get("formal_delivery_control_checked") is False
            ),
            page_timeout,
            "paid_answer_talkroom_not_ready",
        )
        send_performed = False
        if match(initial) is None:
            if contract.attachment_path is not None:
                if _sha256_file(contract.attachment_path) != contract.attachment_sha256:
                    raise RuntimeError("paid_answer_attachment_changed_before_upload")
                await _upload(session, contract.attachment_path)
                if _sha256_file(contract.attachment_path) != contract.attachment_sha256:
                    raise RuntimeError("paid_answer_attachment_changed_during_upload")
                await _wait_for_state(
                    session, expression, lambda state: state.get("form_has_artifact") is True,
                    send_timeout, "paid_answer_upload_not_ready",
                )
            await _fill_message(session, contract.message)
            await _wait_for_state(
                session,
                expression,
                lambda state: (answer_send_ready(state, contract.message)
                               and (contract.attachment_path is None or state.get("form_has_artifact") is True)),
                send_timeout,
                "paid_answer_send_not_ready",
                diagnose=lambda state: textarea_diagnosis(state, contract.message),
            )
            await _click_answer_send(session)
            send_performed = True
        verified = await _wait_for_state(
            session,
            expression,
            lambda state: (
                state.get("url") == contract.talkroom_url
                and state.get("formal_delivery_control_checked") is False
                and match(state) is not None
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
    matched = (matching_seller_message(verified, contract.attachment_path.name, contract.message)
               if contract.attachment_path else matching_seller_text(verified, contract.message))
    if matched is None:
        raise RuntimeError("paid_answer_verified_message_missing")
    collector.secure_directory(evidence_dir)
    screenshot_path = (evidence_dir / "paid-queue-screenshot.png").resolve()
    live_dom_path = (evidence_dir / "paid-queue-live-dom.json").resolve()
    manifest_path = evidence_dir / "paid-queue-evidence.json"
    collector.secure_write_bytes(screenshot_path, screenshot)
    captured_at = datetime.now(timezone.utc).isoformat()
    keys = effect_keys(contract.talkroom_id, contract.message, contract.attachment_sha256)
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
        **keys,
    }
    if contract.attachment_path is not None:
        outer["latest_seller_attachment"] = {
            "filename": contract.attachment_path.name,
            "size_bytes": contract.attachment_path.stat().st_size,
        }
    live = {
        "url": contract.talkroom_url,
        "sent": True,
        "mode": "answer",
        "send_performed": send_performed,
        "deduplicated": not send_performed,
        "formal_delivery_control_checked": False,
        "formal_delivery_control_disabled": verified.get("formal_delivery_control_disabled") is True,
        "captured_at": captured_at,
        "latest_seller_message": str(matched.get("text") or "")[:2000],
        "latest_seller_attachment": contract.attachment_path.name if contract.attachment_path else None,
        # Ordered conversation, buyer and system rows included. Persisted so the paid-buyer
        # liability lane can derive its readback from evidence this path already writes,
        # instead of opening the room a second time to ask the same question. The page has
        # no timestamps, so ordering is the only available proof that our answer sits below
        # the buyer's message. Consumed by paid_thread_state.py.
        "messages": verified.get("messages") or [],
        **keys,
    }
    collector.atomic_json(live_dom_path, live)
    collector.atomic_json(manifest_path, outer)
    return outer


def browser_state_expression(artifact_basename: str) -> str:
    encoded = json.dumps(artifact_basename, ensure_ascii=False)
    return f'''(async()=>{{
      const expanders=[...document.querySelectorAll('.d-talkroomMessage button,.d-talkroomMessage a')]
        .filter(x=>(x.innerText||'').trim()==='続きを読む');
      expanders.forEach(x=>x.click());
      if(expanders.length) await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      const form=document.querySelector('.d-messageForm');
      const textarea=document.querySelector('textarea[placeholder="メッセージを入力"]');
      const formal=document.querySelector('.d-messageFormButtonArea_item-deliveryCheck input[type="checkbox"]');
      const buttons=form?[...form.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()==='送信'):[];
      const send=buttons[buttons.length-1]||null;
      const selectedFileNames=form?[...form.querySelectorAll('input[type=file]')].flatMap(input=>[...(input.files||[])]).map(file=>file.name):[];
      const renderedFileNames=form?[...form.querySelectorAll('.d-partOfFilename')].map(x=>(x.textContent||'').replace(/\\s+/g,'')):[];
      const everyMessage=[...document.querySelectorAll('.d-talkroomMessage')].map(m=>{{
        const side=m.classList.contains('d-talkroomMessage-isOthers')?'buyer':(((m.innerText||'').trim().startsWith('自分'))?'seller':'system');
        const text=(m.querySelector('.d-normalMessage')?.innerText||'').trim();
        const attachments=[...m.querySelectorAll('.d-talkroomMessage_attachedFilesItem')].map(f=>(f.querySelector('.tooltip-content')?.innerText||f.querySelector('.d-attachedFileName')?.innerText||'').replace(/\\s+/g,' ').trim()).filter(Boolean);
        return {{side,text,attachments}};
      }});
      const sellers=everyMessage.filter(x=>x.side==='seller');
      return {{
        url:location.origin+location.pathname,
        title:document.title,
        form_present:!!form,
        textarea_present:!!textarea,
        textarea_value:textarea?.value||'',
        formal_delivery_control_present:!!formal,
        formal_delivery_control_checked:formal?.checked===true,
        formal_delivery_control_disabled:formal?.disabled===true,
        form_has_artifact:!!form&&(
          selectedFileNames.includes({encoded})||
          renderedFileNames.includes({encoded})||
          ((form.innerText||'')+(form.innerHTML||'')).includes({encoded})
        ),
        selected_file_names:selectedFileNames,
        rendered_file_names:renderedFileNames,
        send_button_present:!!send,
        send_button_disabled:send?.disabled!==false,
        seller_messages:sellers,
        // Every message in DOM order, buyer and system rows included. `seller_messages`
        // above is unchanged so the delivery path keeps its contract; this exists because
        // the page carries no timestamps, so proving "our answer sits below theirs" needs
        // the ordering the filtered list threw away. Consumed by paid_thread_state.py.
        messages:everyMessage
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


def textarea_diagnosis(state: dict[str, Any], message: str) -> dict[str, Any]:
    """Why ``textarea_value == message`` is false, without quoting either side.

    ★ The one field answer_send_ready decides on was the one field the failure report left
    out. ★ Measured on order 91000001, 2026-08-08 00:56:32: paid_answer_send_not_ready came
    back with form_present, textarea_present, send_button_present and
    send_button_disabled=false -- every clause of the predicate satisfied except the
    invisible one -- so the send that stalled a paying customer for six hours cannot be
    diagnosed from its own error to this day. (The enabled send button is itself evidence:
    the box was not empty, so text arrived and arrived different.)

    Derived integers and booleans only. Remote page text is not copied into a log line for
    the same reason it is not copied into a ledger.
    """
    value = state.get("textarea_value")
    if not isinstance(value, str):
        return {"textarea_value_readable": False}
    difference = next(
        (index for index, (left, right) in enumerate(zip(value, message)) if left != right),
        min(len(value), len(message)) if len(value) != len(message) else -1,
    )
    return {
        "textarea_value_readable": True,
        "textarea_value_length": len(value),
        "expected_length": len(message),
        "textarea_matches_expected": value == message,
        "first_difference_index": difference,
    }


async def _wait_for_state(
    session: CdpSession,
    expression: str,
    predicate: Any,
    timeout_seconds: float,
    error: str,
    diagnose: Any = None,
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
            "formal_delivery_control_disabled",
            "form_has_artifact",
            "send_button_present",
            "send_button_disabled",
        )
    }
    if diagnose is not None:
        # A diagnosis that itself raises would replace the real failure with its own.
        try:
            extra = diagnose(last)
        except Exception:  # noqa: BLE001
            extra = {"diagnosis_failed": True}
        if isinstance(extra, dict):
            safe.update(extra)
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
    # Playwright serializes files over its CDP connection and refuses payloads
    # above 50 MiB even when Chromium and the artifact share this same Mac.
    # DOM.setFileInputFiles makes Chromium open the local path directly, so the
    # marketplace's own input/change handlers receive the real file without a
    # second in-memory/network transfer.
    for attempt in range(3):
        try:
            document = await session.call("DOM.getDocument", {"depth": 1, "pierce": True})
            root_id = document.get("root", {}).get("nodeId")
            if not isinstance(root_id, int) or root_id <= 0:
                raise RuntimeError("paid_progress_document_missing")
            selected = await session.call(
                "DOM.querySelector",
                {"nodeId": root_id, "selector": ".d-messageForm .isPC input[type=file]"},
            )
            node_id = selected.get("nodeId")
            if not isinstance(node_id, int) or node_id <= 0:
                raise RuntimeError("paid_progress_file_input_missing")
            await session.call(
                "DOM.setFileInputFiles",
                {"nodeId": node_id, "files": [str(artifact_path.resolve())]},
            )
            return
        except RuntimeError as error:
            if "Could not find node with given id" not in str(error) or attempt == 2:
                raise
            await asyncio.sleep(0.25)


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


async def _click_answer_send(session: CdpSession) -> None:
    button = await session.evaluate('''(()=>{
      const form=document.querySelector('.d-messageForm');
      const buttons=form?[...form.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()==='送信'&&!x.disabled):[];
      const target=buttons[buttons.length-1]||null;
      if(!target)return null;
      target.scrollIntoView({block:'center'});
      const rect=target.getBoundingClientRect();
      return {x:rect.left+rect.width/2,y:rect.top+rect.height/2};
    })()''')
    if not isinstance(button, dict):
        raise RuntimeError("paid_answer_send_button_not_clickable")
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
    revision_after_formal: bool = False,
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
                and (
                    state.get("formal_delivery_control_present") is True
                    and state.get("formal_delivery_control_checked") is False
                    if revision_after_formal
                    else state.get("formal_delivery_control_present") is True
                    and state.get("formal_delivery_control_checked") is False
                )
            ),
            page_timeout,
            "paid_progress_talkroom_not_ready",
        )
        existing = matching_seller_message(
            initial, contract.artifact_path.name, contract.message
        )
        send_performed = False
        if existing is None:
            await _upload(session, contract.artifact_path)
            await _wait_for_state(
                session,
                expression,
                lambda state: upload_ready(
                    state, revision_after_formal=revision_after_formal
                ),
                upload_timeout,
                "paid_progress_upload_not_ready",
            )
            await _fill_message(session, contract.message)
            await _wait_for_state(
                session,
                expression,
                lambda state: send_ready(
                    state,
                    contract.message,
                    revision_after_formal=revision_after_formal,
                ),
                send_timeout,
                "paid_progress_send_not_ready",
            )
            if revision_after_formal:
                await _click_answer_send(session)
            else:
                await _click_send(session)
            send_performed = True

        verified = await _wait_for_state(
            session,
            expression,
            lambda state: (
                state.get("url") == contract.talkroom_url
                and (
                    state.get("formal_delivery_control_present") is True
                    and state.get("formal_delivery_control_checked") is False
                    if revision_after_formal
                    else state.get("formal_delivery_control_checked") is False
                )
                and matching_seller_message(
                    state, contract.artifact_path.name, contract.message
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
    revision_after_formal: bool = False,
) -> dict[str, Any]:
    matched = matching_seller_message(
        verified, contract.artifact_path.name, contract.message
    )
    if matched is None:
        raise RuntimeError("paid_progress_verified_message_missing")
    collector.secure_directory(evidence_dir)
    screenshot_path = (evidence_dir / "paid-queue-screenshot.png").resolve()
    live_dom_path = (evidence_dir / "paid-queue-live-dom.json").resolve()
    manifest_path = evidence_dir / "paid-queue-evidence.json"
    collector.secure_write_bytes(screenshot_path, screenshot)
    captured_at = datetime.now(timezone.utc).isoformat()
    keys = effect_keys(contract.talkroom_id, contract.message, contract.package_sha256)
    outer = {
        "mode": "revision_after_formal" if revision_after_formal else "progress",
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
        **keys,
    }
    live = {
        "mode": "revision_after_formal" if revision_after_formal else "progress",
        "url": contract.talkroom_url,
        "sent": True,
        "send_performed": send_performed,
        "deduplicated": not send_performed,
        "formal_delivery_control_checked": False,
        "formal_delivery_control_disabled": verified.get("formal_delivery_control_disabled") is True,
        "formal_delivery_click_performed": False,
        "transaction_state": "納品確認待ち" if revision_after_formal else None,
        "captured_at": captured_at,
        "latest_seller_attachment": {
            "filename": contract.artifact_path.name,
            "size_bytes": contract.artifact_path.stat().st_size,
            "message": str(matched.get("text") or ""),
        },
        **keys,
    }
    collector.atomic_json(live_dom_path, live)
    collector.atomic_json(manifest_path, outer)
    return outer


# validate_progress_contract raised before any browser action: nothing was uploaded, typed,
# or sent. gig_pass.sh must not book this as a delivery attempt -- 9 is chosen clear of the
# formal browser's 7 (ROUTED_TO_ASK_EXIT) and 8 (AWAITING_BUYER_CONFIRMATION_EXIT) and of
# run_with_cdp_lock.sh's 64/75/78, so the branches can never be confused. Any exit code the
# pass does not recognise still records an attempt: fail-closed toward counting.
CONTRACT_INVALID_EXIT = 9


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
    parser.add_argument("--revision-after-formal", action="store_true")
    args = parser.parse_args()
    if (args.manifest is None) == (args.answer_file is None):
        raise SystemExit("exactly one of --manifest or --answer-file is required")
    queue = json.loads(args.queue_item.read_text(encoding="utf-8"))
    if args.answer_file is not None:
        answer = json.loads(args.answer_file.read_text(encoding="utf-8"))
        answer_contract = validate_answer_contract(queue, answer)
        if answer_contract.attachment_path is not None:
            validate_answer_attachment_authorization(queue, answer_contract)
        answer_contract, snapshot_dir = snapshot_answer_attachment(answer_contract, args.evidence_dir.resolve())
        try:
            if answer_contract.attachment_path is not None:
                record_trajectory(
                    stage="PAID_QUEUE_DELIVERY", lane="delivery",
                    resource_key=f"talkroom:{answer_contract.talkroom_id}",
                    action="judge", result="ok", artifact_sha256=answer_contract.attachment_sha256,
                )
            with collector.DefaultTab(args.default_tab_helper, answer_contract.talkroom_url) as tab:
                verified, screenshot, send_performed = asyncio.run(
                    deliver_answer(
                        tab.ws, answer_contract, page_timeout=args.page_timeout,
                        send_timeout=args.send_timeout, post_timeout=args.post_timeout,
                    )
                )
            evidence = persist_answer_evidence(
                args.evidence_dir.resolve(), answer_contract, verified, screenshot, send_performed
            )
        finally:
            if snapshot_dir is not None:
                shutil.rmtree(snapshot_dir, ignore_errors=True)
        record_trajectory(
            stage="PAID_QUEUE_DELIVERY", lane="delivery",
            resource_key=f"talkroom:{answer_contract.talkroom_id}",
            action="deliver" if answer_contract.attachment_path else "ask",
            result="ok" if send_performed else "refused",
            artifact_sha256=answer_contract.attachment_sha256,
        )
        print(json.dumps({"ok": True, "evidence": evidence}, ensure_ascii=False, separators=(",", ":")))
        return 0
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    try:
        contract = validate_progress_contract(
            queue, manifest, revision_after_formal=args.revision_after_formal
        )
    except ValueError as invalid:
        # A contract that fails validation dies HERE, before any tab is opened and
        # before anything could reach the buyer. Measured 2026-08-08 22:04 on order
        # 91000002: progress_blockers_invalid crashed with rc=1, gig_pass.sh read that
        # as a delivery attempt, and the per-target counter went to 9/3 exhausted --
        # a validation bug consumed the order's real retry budget. Same principle as
        # the gc brake: record only after a real attempt. Distinct exit so the pass
        # can skip attempt recording; every other nonzero exit still counts.
        print(json.dumps({"ok": False, "contract_invalid": str(invalid)},
                         ensure_ascii=False, separators=(",", ":")))
        return CONTRACT_INVALID_EXIT
    # ── The last question before the buyer sees it ────────────────────────────────
    #
    # The progress path attaches the same artifact to a buyer-visible message, so it needs
    # the same gate as the formal path and for the same reason: this pass may never have
    # entered PAID_WORK, and the promotion-time judge only guards the transition into
    # "deliverable", not the act of delivering. See
    # artifact_judge.refuse_unless_deliverable for the measurement.
    #
    # Not applied to the --answer-file branch above, which returns before this line: an
    # answer is a message with no artifact, and there is nothing to judge.
    #
    # ★ Fails CLOSED, same error ids as validate_paid_work and the formal browser. ★
    trajectory_context = {
        "stage": "PAID_QUEUE_DELIVERY",
        "lane": "delivery",
        "resource_key": f"talkroom:{contract.talkroom_id}",
        "artifact_sha256": contract.package_sha256,
    }
    artifact_judge.refuse_unless_deliverable(
        contract.project_root, contract.artifact_path, manifest.get("requirements_path"),
        trajectory_context=trajectory_context,
    )
    # Ordinary progress is intentionally incomplete and already declares its blockers. Score the
    # whole contract only when this channel carries a completed revision after formal delivery.
    if args.revision_after_formal:
        predelivery_score.score_predelivery(
            contract.project_root, contract.artifact_path, manifest.get("requirements_path"),
        )
    with collector.DefaultTab(args.default_tab_helper, contract.talkroom_url) as tab:
        verified, screenshot, send_performed = asyncio.run(
            deliver_progress(
                tab.ws,
                contract,
                page_timeout=args.page_timeout,
                upload_timeout=args.upload_timeout,
                send_timeout=args.send_timeout,
                post_timeout=args.post_timeout,
                revision_after_formal=args.revision_after_formal,
            )
        )
    # EV1: the second delivery path. Same shape as the formal browser -- see there.
    record_trajectory(
        action="deliver", result="ok" if send_performed else "refused",
        stage=trajectory_context["stage"], lane=trajectory_context["lane"],
        resource_key=trajectory_context["resource_key"],
        artifact_sha256=trajectory_context["artifact_sha256"],
    )
    evidence = persist_evidence(
        args.evidence_dir.resolve(),
        contract,
        verified,
        screenshot,
        send_performed,
        revision_after_formal=args.revision_after_formal,
    )
    print(json.dumps({"ok": True, "evidence": evidence}, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
