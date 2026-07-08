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
