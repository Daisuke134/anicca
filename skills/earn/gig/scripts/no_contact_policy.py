#!/usr/bin/env python3
"""Validate and match the machine-private Negotiate no-contact registry."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class NoContactPolicyError(ValueError):
    """The private policy cannot be trusted."""


_ID = re.compile(r"[1-9][0-9]*")
_THREAD_PATH = re.compile(r"/mypage/direct_message/([1-9][0-9]*)")
_POLICY_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


def load_registry(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NoContactPolicyError("no_contact_registry_unreadable") from error
    validate_registry(value)
    return value


def validate_registry(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise NoContactPolicyError("invalid_no_contact_registry_version")
    entries = value.get("entries")
    if not isinstance(entries, list):
        raise NoContactPolicyError("invalid_no_contact_entries")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    normalized: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "policy_id", "counterparty_user_id", "thread_path",
        }:
            raise NoContactPolicyError("invalid_no_contact_entry")
        policy_id = str(entry.get("policy_id") or "")
        user_id = str(entry.get("counterparty_user_id") or "")
        thread_path = str(entry.get("thread_path") or "")
        match = _THREAD_PATH.fullmatch(thread_path)
        if _POLICY_ID.fullmatch(policy_id) is None:
            raise NoContactPolicyError("invalid_no_contact_policy_id")
        if _ID.fullmatch(user_id) is None:
            raise NoContactPolicyError("invalid_no_contact_counterparty_id")
        if match is None:
            raise NoContactPolicyError("invalid_no_contact_thread_path")
        if user_id in seen_ids or thread_path in seen_paths:
            raise NoContactPolicyError("duplicate_no_contact_identity")
        seen_ids.add(user_id)
        seen_paths.add(thread_path)
        normalized.append({
            "policy_id": policy_id,
            "counterparty_user_id": user_id,
            "thread_path": thread_path,
        })
    return normalized


def match_thread(
    registry: dict[str, Any], *, thread_path: str,
    counterparty_user_id: str | None = None,
) -> dict[str, str] | None:
    entries = validate_registry(registry)
    matches = [entry for entry in entries if entry["thread_path"] == thread_path]
    if not matches:
        return None
    entry = matches[0]
    if counterparty_user_id is not None and str(counterparty_user_id) != entry["counterparty_user_id"]:
        raise NoContactPolicyError("no_contact_identity_mismatch")
    return entry
