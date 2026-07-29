#!/usr/bin/env python3
"""migration_gate.py — channel_migration_eligible(has_verification_tool) -> bool (REQ-LV-141).
v2.2's core migration constraint: a channel is only migration-eligible when it genuinely has a
machine-verification tool. The judgment (does THIS channel actually have one) stays with the
agent; this function only codifies the resulting record's meaning so no channel can be migrated
"by default". Must be a real bool identity check — None/False/anything else is NOT eligible (no
truthy/falsy string trap: `"False"` the string is truthy in Python, so a naive `if x:` would be
wrong here)."""


def channel_migration_eligible(has_verification_tool):
    return has_verification_tool is True


FINAL_DISPOSITIONS = frozenset({"migrate", "replace", "retire"})
EFFECT_CLASSES = frozenset({"read", "draft", "publish", "message", "money", "maintenance"})


def _nonempty(record, key):
    return isinstance(record.get(key), str) and bool(record[key].strip())


def job_disposition_valid(record):
    """Return True only for a complete, executable final migration decision."""
    if not isinstance(record, dict):
        return False
    disposition = record.get("disposition")
    if disposition not in FINAL_DISPOSITIONS:
        return False
    if record.get("effect_class") not in EFFECT_CLASSES:
        return False
    for key in ("owner", "verify_command", "rollback_action"):
        if not _nonempty(record, key):
            return False
    if disposition in {"migrate", "replace"} and not _nonempty(record, "target_adapter"):
        return False
    return True
