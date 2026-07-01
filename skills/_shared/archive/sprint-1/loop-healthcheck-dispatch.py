#!/usr/bin/env python3
"""loop-healthcheck-dispatch.py — Python side of loop-healthcheck.sh.

SECURITY: reads all inputs from os.environ (set safely by the shell), never from
string interpolation. Prevents FIND-2-001 RCE.
"""
import os
import sys
from pathlib import Path

shared_dir = os.environ.get("ANICCA_SHARED_DIR", "")
if shared_dir:
    sys.path.insert(0, shared_dir)

from lib.healthcheck import HealthcheckContext, Mode, classify  # noqa: E402


def main() -> int:
    def _int_or_none(s: str) -> int | None:
        try:
            return int(s) if s.strip() else None
        except (ValueError, AttributeError):
            return None

    restart_log = []
    log_str = os.environ.get("ANICCA_RESTART_LOG", "")
    for line in log_str.splitlines():
        line = line.strip()
        if line:
            try:
                restart_log.append(int(line))
            except ValueError:
                pass

    ctx = HealthcheckContext(
        slot=os.environ.get("ANICCA_SLOT", ""),
        pane_text=os.environ.get("ANICCA_PANE_TEXT", ""),
        has_session=os.environ.get("ANICCA_HAS_SESSION", "false").lower() == "true",
        last_pass_mtime=_int_or_none(os.environ.get("ANICCA_LAST_PASS_MTIME", "")),
        last_start_mtime=_int_or_none(os.environ.get("ANICCA_LAST_START_MTIME", "")),
        restart_log_entries=restart_log,
        cron_has_slot_job=True,  # TODO sprint-2: probe via CronList wrapper
        now_ts=int(os.environ.get("ANICCA_NOW_TS", "0")) or 0,
    )
    mode = classify(ctx)
    print(f"mode: {mode.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
