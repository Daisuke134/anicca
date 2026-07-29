#!/usr/bin/env python3
"""Autonomous multi-thread orchestration for the Coconala reply queue."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    from reply_executor import execute_reply
except ModuleNotFoundError:  # imported directly by unit-test loaders
    execute_reply = _load_local("reply_executor").execute_reply


def _verified_event(
    *, action: dict[str, Any], item: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    """Project a verified result to bounded, Telegram-safe metadata."""
    event = {
        "action_id": int(result.get("action_id") or action["action_id"]),
        "revision": int(result.get("revision") or action["revision"]),
        "talkroom_id": str(item["talkroom_id"]),
        "origin_at": str(result.get("origin_at") or item["origin_at"]),
        "seller_sent_at": str(result["seller_sent_at"]),
        "status": "replied",
    }
    if event["action_id"] <= 0 or event["revision"] <= 0:
        raise ValueError("verified reply event lacks positive action revision")
    return event


def process_queue(
    *,
    controller: Any,
    queue: dict[str, Any],
    compose: Any,
    browser_factory: Any,
    owner_prefix: str,
    clock: Any,
    max_model_calls: int | None = None,
) -> dict[str, Any]:
    """Process every current pending thread; repeated projections become no-ops."""
    if queue.get("status") == "collector_unhealthy":
        raise ValueError("collector queue is unhealthy")
    if queue.get("status") not in {"ready", "queue_empty"}:
        raise ValueError("invalid reply queue status")
    summary = {
        "status": "completed",
        "replied": 0,
        "reconciled": 0,
        "requeued": 0,
        "reconcile_pending": 0,
        "blocked": 0,
        "skipped": 0,
        "deferred": 0,
        "model_calls": 0,
        "errors": [],
        "events": [],
    }
    items = list(queue.get("items", []))
    queued_threads = {
        str(item.get("talkroom_id") or "")
        for item in items
        if isinstance(item, dict)
    }
    reconciliations = {
        str(action["thread_id"]): action
        for action in controller.reconciliation_actions()
    }
    for thread_id, action in reconciliations.items():
        if thread_id in queued_threads:
            continue
        event_key = str(action.get("event_key") or "")
        items.append({
            "event_key": event_key,
            "covered_event_keys": [event_key] if event_key else [],
            "talkroom_id": thread_id,
            "talkroom_url": str(action["thread_url"]),
            "origin_at": datetime.fromtimestamp(
                int(action["intent_origin_at"]), timezone.utc
            ).isoformat(),
        })
        queued_threads.add(thread_id)
    if queue.get("status") == "queue_empty" and not items:
        for action in controller.pending_actions():
            thread_id = str(action["thread_id"])
            if thread_id in queued_threads:
                continue
            event_key = str(action.get("event_key") or "")
            event_observed_at = action.get("event_observed_at")
            if not event_key or type(event_observed_at) is not int:
                raise ValueError("durable pending action lacks event identity")
            items.append({
                "event_key": event_key,
                "covered_event_keys": [event_key],
                "talkroom_id": thread_id,
                "talkroom_url": str(action["thread_url"]),
                "origin_at": datetime.fromtimestamp(
                    event_observed_at, timezone.utc
                ).isoformat(),
            })
            queued_threads.add(thread_id)
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("invalid reply queue item")
        thread_id = str(item.get("talkroom_id") or "")
        reconciliation = reconciliations.get(thread_id)
        if reconciliation is not None:
            with browser_factory(reconciliation, item) as browser:
                transient, observation = browser.read_before()
            if isinstance(transient, dict):
                transient.clear()
            reconciled = controller.reconcile_observation(
                action=reconciliation,
                observation=observation,
                observed_at=clock(),
            )
            reconciliation_status = str(reconciled.get("status") or "")
            if reconciliation_status == "replied":
                summary["replied"] += 1
                summary["reconciled"] += 1
                summary["events"].append(_verified_event(
                    action=reconciliation, item=item, result=reconciled,
                ))
            elif reconciliation_status == "requeued":
                summary["requeued"] += 1
                if reconciled.get("defer") is True:
                    continue
            elif reconciliation_status == "blocked":
                summary["blocked"] += 1
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "status": "blocked",
                    "errors": list(reconciled.get("errors") or []),
                })
                continue
            elif reconciliation_status in {"reconcile_pending", "duplicate_detected"}:
                summary["reconcile_pending"] += 1
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "status": reconciliation_status,
                    "errors": list(reconciled.get("errors") or []),
                })
                continue
            else:
                raise RuntimeError(
                    f"reply reconciliation ended in unexpected status: {reconciliation_status}"
                )
        action = controller.pending_action_for_thread(thread_id)
        if action is None:
            if reconciliation is None:
                summary["skipped"] += 1
            continue
        if max_model_calls is not None and summary["model_calls"] >= max_model_calls:
            summary["deferred"] += 1
            continue
        summary["model_calls"] += 1
        owner = f"{owner_prefix}:{action['action_id']}"
        with browser_factory(action, item) as browser:
            result = execute_reply(
                controller=controller,
                queue_item=item,
                owner=owner,
                clock=clock,
                compose=compose,
                browser=browser,
                action_id=int(action["action_id"]),
            )
        status = str(result.get("status") or "")
        if status == "replied":
            summary["replied"] += 1
            summary["events"].append(_verified_event(
                action=action, item=item, result=result,
            ))
        elif status == "reconcile_pending":
            summary["reconcile_pending"] += 1
            summary["errors"].append({
                "talkroom_id": thread_id,
                "status": status,
                "errors": list(result.get("errors") or []),
            })
        elif status == "queue_empty":
            summary["skipped"] += 1
        else:
            raise RuntimeError(f"reply action ended in unexpected status: {status}")
    if summary["reconcile_pending"]:
        summary["status"] = "reconcile_pending"
    return summary


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        path.chmod(0o600)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--cdp-helper", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workdir", type=Path, default=Path.home())
    parser.add_argument("--owner-prefix")
    parser.add_argument("--hidden-browser", action="store_true")
    parser.add_argument("--max-model-calls", type=int, default=1)
    args = parser.parse_args()
    if args.max_model_calls < 1:
        parser.error("--max-model-calls must be at least 1")
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    action_module = _load_local("reply_action")
    controller = action_module.ReplyActionController(args.database, args.manifest)
    try:
        if (
            not queue.get("items")
            and queue.get("status") == "queue_empty"
            and not controller.reconciliation_actions()
            and not controller.pending_actions()
        ):
            result = process_queue(
                controller=controller,
                queue=queue,
                compose=lambda _: (_ for _ in ()).throw(AssertionError("model must not run")),
                browser_factory=lambda *_: (_ for _ in ()).throw(AssertionError("browser must not run")),
                owner_prefix=args.owner_prefix or "gig-reply-empty",
                clock=lambda: int(time.time()),
                max_model_calls=args.max_model_calls,
            )
        else:
            composer_module = _load_local("reply_composer")
            browser_module = _load_local("coconala_reply_browser")
            composer = composer_module.RunnerComposer(
                runner=args.runner,
                schema=args.schema,
                workdir=args.workdir,
            )

            def browser_factory(action: dict[str, Any], item: dict[str, Any]):
                return browser_module.CoconalaCdpReplyBrowser(
                    args.cdp_helper,
                    str(item["talkroom_url"]),
                    hidden=args.hidden_browser,
                )

            result = process_queue(
                controller=controller,
                queue=queue,
                compose=composer,
                browser_factory=browser_factory,
                owner_prefix=args.owner_prefix or f"gig-reply-{os.getpid()}-{uuid.uuid4().hex[:12]}",
                clock=lambda: int(time.time()),
                max_model_calls=args.max_model_calls,
            )
        _atomic_json(args.output, result)
    except Exception as error:
        failure = {
            "status": "failed",
            "replied": 0,
            "reconciled": 0,
            "requeued": 0,
            "reconcile_pending": 0,
            "blocked": 0,
            "skipped": 0,
            "errors": [{"type": type(error).__name__, "message": str(error)[:300]}],
            "events": [],
        }
        _atomic_json(args.output, failure)
        print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 2 if result["status"] == "reconcile_pending" else 0


if __name__ == "__main__":
    raise SystemExit(main())
