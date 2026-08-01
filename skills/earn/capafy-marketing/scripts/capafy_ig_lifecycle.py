#!/usr/bin/env python3
"""Deterministic Capafy Instagram lifecycle state and atomic bookkeeping."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


VALID_CAPABILITIES = frozenset({"none", "publish_probe", "commercial_post"})
ACTIVE_STATUSES = frozenset(
    {
        "warming",
        "ready_browser",
        "created_session_verified",
        "publish_probe_ready",
        "first_publish_probe_verified",
        "noncommercial_ready",
        "reach_observing",
        "commercial_ready",
    }
)
INSTAGRAM_REEL_HOST = "www.instagram.com"
INSTAGRAM_REEL_PATH_PREFIX = "/reel/"


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _positive_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _account_sort_key(row: dict) -> tuple[str, int]:
    created = row.get("started_warming") or row.get("created") or ""
    return str(created), _positive_int(row.get("created_at_epoch"))


def _active_account(accounts: list[dict]) -> dict | None:
    usable = [
        row
        for row in accounts
        if isinstance(row, dict)
        and row.get("handle")
        and row.get("session_owner") == "browser"
        and row.get("status") in ACTIVE_STATUSES
    ]
    return max(usable, key=_account_sort_key) if usable else None


def derive_snapshot(accounts: list[dict], prior: dict, now: datetime) -> dict:
    active = _active_account(accounts)
    updated_at = _utc_text(now)
    if active is None:
        return {
            "schema_version": 1,
            "status": "replacement_requested",
            "handle": None,
            "session_owner": None,
            "session_established": False,
            "capability": "none",
            "last_public_reel_url": None,
            "post_write_session_verified": False,
            "reach_healthy": False,
            "replacement_requested": True,
            "incident_id": prior.get("incident_id"),
            "updated_at": updated_at,
        }

    handle = str(active["handle"])
    prior_is_same = prior.get("handle") == handle
    incident_id = prior.get("incident_id") if prior_is_same else None
    reach_healthy = bool(prior.get("reach_healthy")) if prior_is_same else False
    reel_url = prior.get("last_public_reel_url") if prior_is_same else None
    post_write_verified = (
        bool(prior.get("post_write_session_verified")) if prior_is_same else False
    )
    if reel_url and reach_healthy and post_write_verified:
        capability = "commercial_post"
        status = "commercial_ready"
    elif reel_url:
        capability = "none"
        status = "reach_observing"
    else:
        capability = "publish_probe"
        status = "publish_probe_ready"

    assert capability in VALID_CAPABILITIES
    return {
        "schema_version": 1,
        "status": status,
        "handle": handle,
        "session_owner": "browser",
        "session_established": True,
        "capability": capability,
        "last_public_reel_url": reel_url,
        "post_write_session_verified": post_write_verified,
        "reach_healthy": reach_healthy,
        "replacement_requested": False,
        "incident_id": incident_id,
        "updated_at": updated_at,
    }


def atomic_json(path: Path, value: Any) -> Any:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temp_name = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        temp_name = None
        return _read_json(path)
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def retire_account(
    path: Path, handle: str, reason: str, incident_id: str
) -> dict:
    rows = _read_json(path)
    if not isinstance(rows, list):
        raise ValueError("account registry must be a JSON list")
    target_index = next(
        (index for index, row in enumerate(rows) if isinstance(row, dict) and row.get("handle") == handle),
        None,
    )
    if target_index is None:
        raise ValueError(f"account handle not found: {handle}")
    replacement = dict(rows[target_index])
    replacement.update(
        {
            "status": "session_failed",
            "retirement_reason": reason,
            "incident_id": incident_id,
            "retired_at": _utc_text(_now_utc()),
        }
    )
    rows[target_index] = replacement
    written = atomic_json(path, rows)
    return {
        "retired_handle": handle,
        "reason": reason,
        "incident_id": incident_id,
        "account": written[target_index],
    }


def _is_reel_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    suffix = parsed.path[len(INSTAGRAM_REEL_PATH_PREFIX) :].strip("/")
    return (
        parsed.scheme == "https"
        and parsed.hostname == INSTAGRAM_REEL_HOST
        and parsed.path.startswith(INSTAGRAM_REEL_PATH_PREFIX)
        and bool(suffix)
    )


def record_public_reel(
    path: Path,
    handle: str,
    reel_url: str,
    *,
    owner_session_verified: bool,
) -> dict:
    if not _is_reel_url(reel_url):
        raise ValueError("expected a public https://www.instagram.com/reel/... Instagram Reel URL")
    if owner_session_verified is not True:
        raise ValueError("post-write owner session must be verified")
    state = _read_json(path, {})
    if not isinstance(state, dict):
        raise ValueError("lifecycle state must be a JSON object")
    if state.get("handle") not in (None, handle):
        raise ValueError("Reel handle does not match lifecycle handle")
    state.update(
        {
            "schema_version": 1,
            "handle": handle,
            "status": "first_publish_probe_verified",
            "capability": "none",
            "last_public_reel_url": reel_url,
            "post_write_session_verified": True,
            "replacement_requested": False,
            "updated_at": _utc_text(_now_utc()),
        }
    )
    return atomic_json(path, state)


def request_replacement(
    path: Path, reason: str, incident_id: str, handle: str | None = None
) -> dict:
    state = _read_json(path, {})
    if not isinstance(state, dict):
        raise ValueError("lifecycle state must be a JSON object")
    if handle is not None:
        state["handle"] = handle
    state.update(
        {
            "schema_version": 1,
            "status": "replacement_requested",
            "capability": "none",
            "session_established": False,
            "replacement_requested": True,
            "replacement_reason": reason,
            "incident_id": incident_id,
            "updated_at": _utc_text(_now_utc()),
        }
    )
    return atomic_json(path, state)


def _parse_now(value: str | None) -> datetime:
    if not value:
        return _now_utc()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--accounts", type=Path, required=True)
    snapshot.add_argument("--state", type=Path, required=True)
    snapshot.add_argument("--now")

    retire = commands.add_parser("retire")
    retire.add_argument("--accounts", type=Path, required=True)
    retire.add_argument("--handle", required=True)
    retire.add_argument("--reason", required=True)
    retire.add_argument("--incident-id", required=True)

    record = commands.add_parser("record-reel")
    record.add_argument("--state", type=Path, required=True)
    record.add_argument("--handle", required=True)
    record.add_argument("--reel-url", required=True)
    record.add_argument("--owner-session-verified", action="store_true")

    replacement = commands.add_parser("request-replacement")
    replacement.add_argument("--state", type=Path, required=True)
    replacement.add_argument("--reason", required=True)
    replacement.add_argument("--incident-id", required=True)
    replacement.add_argument("--handle")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "snapshot":
        accounts = _read_json(args.accounts, [])
        prior = _read_json(args.state, {})
        if not isinstance(accounts, list) or not isinstance(prior, dict):
            raise ValueError("snapshot inputs have invalid JSON shapes")
        result = atomic_json(
            args.state, derive_snapshot(accounts, prior, _parse_now(args.now))
        )
    elif args.command == "retire":
        result = retire_account(args.accounts, args.handle, args.reason, args.incident_id)
    elif args.command == "record-reel":
        result = record_public_reel(
            args.state,
            args.handle,
            args.reel_url,
            owner_session_verified=args.owner_session_verified,
        )
    else:
        result = request_replacement(
            args.state, args.reason, args.incident_id, args.handle
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
