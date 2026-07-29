#!/usr/bin/env python3
"""Validate B0's browser result and let code, not the model, write shuppin.jsonl.

The browser agent owns marketplace judgement and the visible side effect.  This
module owns the durable identity boundary: context binding, fresh owned evidence,
canonical ledger location, action taxonomy, and idempotent append.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class ContractError(ValueError):
    pass


ACTION_TO_LEDGER = {
    "published": "shuppin_published",
    "created": "shuppin_created",
    "updated": "shuppin_edited",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label}_unreadable") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label}_invalid")
    return value


def _owned_fresh_file(value: Any, root: Path, min_mtime: float, label: str) -> Path:
    try:
        path = Path(str(value or "")).resolve()
        path.relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise ContractError(f"{label}_not_owned") from exc
    try:
        stat = path.stat()
    except OSError as exc:
        raise ContractError(f"{label}_missing") from exc
    if not path.is_file() or stat.st_size == 0:
        raise ContractError(f"{label}_missing")
    if stat.st_mtime < min_mtime:
        raise ContractError(f"{label}_stale")
    return path


def _listing_url(value: Any, service_id: str) -> bool:
    parsed = urlsplit(str(value or ""))
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"coconala.com", "www.coconala.com"}
        and parsed.path == f"/services/{service_id}"
        and not parsed.query
        and not parsed.fragment
    )


def build_context(decision: dict[str, Any], ledger_path: Path, pass_id: str) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise ContractError("b0_decision_invalid")
    action = str(decision.get("action") or "").strip()
    objective = str(decision.get("objective") or "").strip()
    if not action or not objective:
        raise ContractError("b0_decision_incomplete")
    if not pass_id:
        raise ContractError("pass_id_missing")
    return {
        "version": 1,
        "pass_id": pass_id,
        "canonical_ledger_path": str(Path(ledger_path).resolve()),
        "objective_action": action,
        "objective": objective,
        "must_reuse_existing": decision.get("must_reuse_existing") is True,
    }


def prepare_capacity_retry(
    *,
    gate_result_path: Path,
    context_path: Path,
    attempt: int,
) -> dict[str, Any]:
    if attempt != 0:
        raise ContractError("b0_capacity_retry_exhausted")
    gate_result = _read_object(Path(gate_result_path), "b0_gate_result")
    context = _read_object(Path(context_path), "b0_context")
    if (
        gate_result.get("error") != "capacity_recovery_requires_existing_effect"
        or context.get("must_reuse_existing") is not True
    ):
        raise ContractError("b0_capacity_retry_not_applicable")
    retry = dict(context)
    retry["objective_action"] = "improve_existing_after_capacity"
    retry["objective"] = (
        "CAPACITY IS NOW CONFIRMED by the same-wake live publisher rejection. "
        "Do not publish or resume a draft and do not return verified_noop. "
        "Immediately choose one currently public service from "
        "/mypage/services_lists, make one buyer-visible improvement grounded in "
        "work this account has actually delivered, save it, then reopen the exact "
        "public /services/<id> page and return fresh after-change evidence."
    )
    retry["recovery_of_error"] = str(gate_result["error"])
    return retry


def _write_object_atomic(path: Path, value: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _result(
    summary_path: Path, evidence_dir: Path, min_mtime: float
) -> dict[str, Any]:
    summary = _read_object(summary_path, "b0_runner_summary")
    if summary.get("status") != "success" or summary.get("task_label") != "gig-B0":
        raise ContractError("b0_runner_summary_not_success")
    result_path = _owned_fresh_file(
        summary.get("result_path"), evidence_dir, min_mtime, "b0_result"
    )
    result = _read_object(result_path, "b0_result")
    if result.get("status") != "ok":
        raise ContractError("b0_result_invalid")
    return result


def _append_once(ledger_path: Path, row: dict[str, Any]) -> bool:
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
                    and existing.get("pass_id") == row["pass_id"]
                    and str(existing.get("recorded_by") or "").startswith(
                        "b0_result_gate"
                    )
                ):
                    return False
            handle.seek(0, os.SEEK_END)
            handle.write(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
            return True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def reconcile(
    *,
    context_path: Path,
    summary_path: Path,
    evidence_dir: Path,
    ledger_path: Path,
    min_mtime: float,
    now: float | None = None,
) -> dict[str, int | str]:
    context_path = Path(context_path)
    evidence_dir = Path(evidence_dir)
    ledger_path = Path(ledger_path)
    context = _read_object(context_path, "b0_context")
    try:
        expected_ledger = Path(
            str(context["canonical_ledger_path"])
        ).resolve()
        pass_id = str(context["pass_id"])
    except (KeyError, OSError) as exc:
        raise ContractError("b0_context_invalid") from exc
    if expected_ledger != ledger_path.resolve():
        raise ContractError("canonical_ledger_path_mismatch")

    result = _result(summary_path, evidence_dir, min_mtime)
    current = result.get("current_b0")
    if not isinstance(current, dict):
        raise ContractError("current_b0_missing")
    try:
        if Path(str(current.get("context_path") or "")).resolve() != context_path.resolve():
            raise ContractError("context_path_mismatch")
        if current.get("context_sha256") != sha256_file(context_path):
            raise ContractError("context_sha256_mismatch")
    except OSError as exc:
        raise ContractError("context_binding_unreadable") from exc

    action = str(current.get("action") or "")
    if (
        context.get("must_reuse_existing") is True
        and action not in {"published", "updated"}
    ):
        raise ContractError("capacity_recovery_requires_existing_effect")
    if action == "verified_noop":
        if any(
            current.get(key) is not None
            for key in (
                "service_id",
                "url",
                "title",
                "screenshot_path",
                "live_dom_path",
            )
        ):
            raise ContractError("noop_carries_action_identity")
        return {"action": action, "appended": 0, "duplicate": 0}
    if action not in ACTION_TO_LEDGER:
        raise ContractError("listing_action_invalid")

    service_id = str(current.get("service_id") or "").strip()
    if not re.fullmatch(r"\d+", service_id):
        raise ContractError("service_id_invalid")
    url = str(current.get("url") or "").strip()
    if not _listing_url(url, service_id):
        raise ContractError("listing_url_invalid")
    title = str(current.get("title") or "").strip()
    if not title:
        raise ContractError("listing_title_missing")
    _owned_fresh_file(
        current.get("screenshot_path"), evidence_dir, min_mtime, "screenshot"
    )
    live_dom_path = _owned_fresh_file(
        current.get("live_dom_path"), evidence_dir, min_mtime, "live_dom"
    )
    live_dom = _read_object(live_dom_path, "live_dom")
    if live_dom.get("url") != url:
        raise ContractError("live_dom_url_mismatch")
    if live_dom.get("observed") is not True:
        raise ContractError("live_dom_not_observed")
    if live_dom.get("not_found") is True:
        raise ContractError("live_dom_not_found")

    row = {
        "ts": int(time.time() if now is None else now),
        "pass_id": pass_id,
        "lane": "list",
        "action": ACTION_TO_LEDGER[action],
        "service_id": service_id,
        "url": url,
        "title": title,
        "evidence": str(live_dom_path),
        "recorded_by": "b0_result_gate",
    }
    appended = _append_once(ledger_path, row)
    return {
        "action": action,
        "appended": int(appended),
        "duplicate": int(not appended),
    }


def recover_misrouted(
    *,
    row_path: Path,
    pass_id: str,
    evidence_dir: Path,
    screenshot_path: Path,
    live_dom_path: Path,
    ledger_path: Path,
    min_mtime: float,
    now: float | None = None,
) -> dict[str, int | str]:
    """Recover one preserved wrong-path row after re-observing its public identity."""
    try:
        lines = [
            line
            for line in Path(row_path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError as exc:
        raise ContractError("misrouted_row_unreadable") from exc
    if len(lines) != 1:
        raise ContractError("misrouted_row_count_invalid")
    try:
        source = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ContractError("misrouted_row_invalid") from exc
    if not isinstance(source, dict):
        raise ContractError("misrouted_row_invalid")
    raw_action = str(source.get("action") or "").strip().lower()
    if raw_action not in {"published", "shuppin_published"}:
        raise ContractError("misrouted_action_not_published")
    service_id = str(source.get("service_id") or "").strip()
    url = str(source.get("url") or "").strip()
    title = str(source.get("title") or "").strip()
    if not re.fullmatch(r"\d+", service_id):
        raise ContractError("service_id_invalid")
    if not _listing_url(url, service_id):
        raise ContractError("listing_url_invalid")
    if not title:
        raise ContractError("listing_title_missing")
    _owned_fresh_file(
        screenshot_path, evidence_dir, min_mtime, "screenshot"
    )
    verified_dom_path = _owned_fresh_file(
        live_dom_path, evidence_dir, min_mtime, "live_dom"
    )
    live_dom = _read_object(verified_dom_path, "live_dom")
    if live_dom.get("url") != url:
        raise ContractError("live_dom_url_mismatch")
    if live_dom.get("observed") is not True:
        raise ContractError("live_dom_not_observed")
    if live_dom.get("not_found") is True:
        raise ContractError("live_dom_not_found")
    row = {
        "ts": int(time.time() if now is None else now),
        "pass_id": pass_id,
        "lane": "list",
        "action": "shuppin_published",
        "service_id": service_id,
        "url": url,
        "title": title,
        "evidence": str(verified_dom_path),
        "recorded_by": "b0_result_gate_recovery",
    }
    appended = _append_once(Path(ledger_path), row)
    return {
        "action": "published",
        "appended": int(appended),
        "duplicate": int(not appended),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--decision-json", required=True)
    build.add_argument("--ledger", required=True, type=Path)
    build.add_argument("--pass-id", required=True)
    build.add_argument("--output", required=True, type=Path)
    reconcile_parser = subparsers.add_parser("reconcile")
    reconcile_parser.add_argument("--context", required=True, type=Path)
    reconcile_parser.add_argument("--runner-summary", required=True, type=Path)
    reconcile_parser.add_argument("--evidence-dir", required=True, type=Path)
    reconcile_parser.add_argument("--ledger", required=True, type=Path)
    reconcile_parser.add_argument("--min-mtime", required=True, type=float)
    recover = subparsers.add_parser("recover")
    recover.add_argument("--row", required=True, type=Path)
    recover.add_argument("--pass-id", required=True)
    recover.add_argument("--evidence-dir", required=True, type=Path)
    recover.add_argument("--screenshot", required=True, type=Path)
    recover.add_argument("--live-dom", required=True, type=Path)
    recover.add_argument("--ledger", required=True, type=Path)
    recover.add_argument("--min-mtime", required=True, type=float)
    retry = subparsers.add_parser("retry-context")
    retry.add_argument("--gate-result", required=True, type=Path)
    retry.add_argument("--context", required=True, type=Path)
    retry.add_argument("--attempt", required=True, type=int)
    retry.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "build":
            decision = json.loads(args.decision_json)
            context = build_context(decision, args.ledger, args.pass_id)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(context, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            print(json.dumps({"ok": True, "output": str(args.output)}))
        elif args.command == "reconcile":
            result = reconcile(
                context_path=args.context,
                summary_path=args.runner_summary,
                evidence_dir=args.evidence_dir,
                ledger_path=args.ledger,
                min_mtime=args.min_mtime,
            )
            print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        elif args.command == "recover":
            result = recover_misrouted(
                row_path=args.row,
                pass_id=args.pass_id,
                evidence_dir=args.evidence_dir,
                screenshot_path=args.screenshot,
                live_dom_path=args.live_dom,
                ledger_path=args.ledger,
                min_mtime=args.min_mtime,
            )
            print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        else:
            context = prepare_capacity_retry(
                gate_result_path=args.gate_result,
                context_path=args.context,
                attempt=args.attempt,
            )
            _write_object_atomic(args.output, context)
            print(json.dumps({"ok": True, "output": str(args.output)}))
        return 0
    except (ContractError, json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
