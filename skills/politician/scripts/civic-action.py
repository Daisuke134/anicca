#!/usr/bin/env python3
"""civic-action.py — unified entry point for advocacy-platform automation.

Replaces the v0.1.0 placeholder. Drives the bash wrappers under
scripts/lib/{phone2action.sh,quorum.sh} via subprocess so that all
policy gating (DRY_RUN, missing-API-key stubbing, env loading) lives
in one place — the bash layer — rather than being duplicated in Python.

Usage:
  civic-action.py track-bill   <bill_id>
  civic-action.py send-alert   <legislator_id> <template_path>
  civic-action.py pull-history [since_iso8601]
  civic-action.py search-bill  <keyword>
  civic-action.py voting       <legislator_id>
  civic-action.py staffers     <office_id>
  civic-action.py self-check

  --json   emit machine-readable JSON instead of plain text where possible

Exit codes:
  0   success (including stub-mode no-op)
  2   bad invocation (missing arg, unknown subcommand)
  3   underlying wrapper exited non-zero
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = SKILL_ROOT / "scripts" / "lib"
P2A = LIB_DIR / "phone2action.sh"
QUORUM = LIB_DIR / "quorum.sh"


def _run_bash(lib: Path, fn: str, *args: str, capture: bool = True) -> tuple[int, str, str]:
    """Source `lib` and invoke `fn args...`. Returns (exitcode, stdout, stderr)."""
    cmd = ["bash", "-c", f'set -euo pipefail; source "{lib}"; {fn} "$@"', "_", *args]
    env = os.environ.copy()
    env.setdefault("SKILL", str(SKILL_ROOT))
    if capture:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr
    proc = subprocess.run(cmd, env=env)
    return proc.returncode, "", ""


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    # human-readable
    for k, v in payload.items():
        sys.stdout.write(f"{k}: {v}\n")


def cmd_track_bill(args) -> int:
    rc, out, err = _run_bash(P2A, "p2a_track_bill", args.bill_id)
    sys.stderr.write(err)
    sys.stdout.write(out)
    return 0 if rc == 0 else 3


def cmd_send_alert(args) -> int:
    rc, out, err = _run_bash(P2A, "p2a_send_alert", args.legislator_id, args.template_path)
    sys.stderr.write(err)
    sys.stdout.write(out)
    return 0 if rc == 0 else 3


def cmd_pull_history(args) -> int:
    a = [args.since] if args.since else []
    rc, out, err = _run_bash(P2A, "p2a_pull_action_history", *a)
    sys.stderr.write(err)
    sys.stdout.write(out)
    return 0 if rc == 0 else 3


def cmd_search_bill(args) -> int:
    rc, out, err = _run_bash(QUORUM, "quorum_search_bill", args.keyword)
    sys.stderr.write(err)
    sys.stdout.write(out)
    return 0 if rc == 0 else 3


def cmd_voting(args) -> int:
    rc, out, err = _run_bash(QUORUM, "quorum_legislator_voting_record", args.legislator_id)
    sys.stderr.write(err)
    sys.stdout.write(out)
    return 0 if rc == 0 else 3


def cmd_staffers(args) -> int:
    rc, out, err = _run_bash(QUORUM, "quorum_lookup_staffer", args.office_id)
    sys.stderr.write(err)
    sys.stdout.write(out)
    return 0 if rc == 0 else 3


def cmd_self_check(args) -> int:
    rc1, out1, err1 = _run_bash(P2A, "p2a_self_check")
    rc2, out2, err2 = _run_bash(QUORUM, "quorum_self_check")
    if args.json:
        # Pull "set"/"unset" + LIVE/STUB status by scanning output.
        def parse(out: str) -> dict:
            d = {}
            for ln in out.splitlines():
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    d[k.strip()] = v.strip()
            return d
        _emit({
            "phone2action": parse(out1),
            "quorum": parse(out2),
            "skill_root": str(SKILL_ROOT),
            "lib_dir": str(LIB_DIR),
        }, as_json=True)
    else:
        sys.stdout.write(out1)
        sys.stdout.write("\n")
        sys.stdout.write(out2)
    return 0 if (rc1 == 0 and rc2 == 0) else 3


def main() -> int:
    # parent parser so --json is accepted both before and after the subcommand
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--json", action="store_true", help="emit JSON where supported")
    ap = argparse.ArgumentParser(prog="civic-action.py", parents=[parent])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("track-bill", parents=[parent], help="P2A: subscribe to bill updates")
    p.add_argument("bill_id"); p.set_defaults(func=cmd_track_bill)

    p = sub.add_parser("send-alert", parents=[parent], help="P2A: send constituent action alert")
    p.add_argument("legislator_id"); p.add_argument("template_path")
    p.set_defaults(func=cmd_send_alert)

    p = sub.add_parser("pull-history", parents=[parent], help="P2A: pull our action history")
    p.add_argument("since", nargs="?", help="ISO8601, default 7 days ago")
    p.set_defaults(func=cmd_pull_history)

    p = sub.add_parser("search-bill", parents=[parent], help="Quorum: search bills by keyword")
    p.add_argument("keyword"); p.set_defaults(func=cmd_search_bill)

    p = sub.add_parser("voting", parents=[parent], help="Quorum: legislator voting record")
    p.add_argument("legislator_id"); p.set_defaults(func=cmd_voting)

    p = sub.add_parser("staffers", parents=[parent], help="Quorum: look up staffer directory")
    p.add_argument("office_id"); p.set_defaults(func=cmd_staffers)

    p = sub.add_parser("self-check", parents=[parent], help="report wrapper health for both libs")
    p.set_defaults(func=cmd_self_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
