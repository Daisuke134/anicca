#!/usr/bin/env python3
"""Mail draft generator — HARD RULE #6 compliant.

NO external LLM call. The bash pipeline must NEVER attempt LLM draft.
Draft generation is heartbeat (Claude) reading SKILL.md + 8-layer context
and writing the reply inline using its own LLM.

This module exists as a stub so the existing run.sh shell pipeline doesn't
break. It always returns an empty string which:
  - Causes run.sh:78 to grep no-reply-signal → skip send
  - No autonomous reply will ever happen

The heartbeat owns reply duty going forward (HEARTBEAT.md §2.5).
"""
from __future__ import annotations
import json, sys


def draft(thread_meta: dict) -> str:
    """Stub: always return empty. No LLM call.
    run.sh's no-reply-signal check will catch this and skip send."""
    return ""


if __name__ == "__main__":
    meta = json.load(sys.stdin)
    print(draft(meta))
