#!/usr/bin/env python3
"""Generate launchd jobs from each loop's own declaration.

241 launchd plists on this machine are hand-written with /Users/operator baked into them, which is
why none of them run on anyone else's Mac and why adding loop number 300 currently means writing
XML by hand. A loop should declare its cadence and its entrypoint; the paths belong to the machine
the job is installed on, so they are produced at generation time rather than committed.

  python3 bin/plistgen.py --loops-dir loops --out-dir ~/Library/LaunchAgents
  python3 bin/plistgen.py --loops-dir loops --out-dir /tmp/x --diff   # show, install nothing

Each loops/<name>/loop.toml:

    name      = "x-repost"
    state_dir = "~/loops/x-repost"

    [env]
    X_REPOST_BROWSER_IDENTITY = "x:anicca"

    [jobs.pass]
    program          = "skills/x-repost/x-repost-cli.sh"
    interval_seconds = 3600

    [jobs.digest]
    program  = "skills/x-repost/x-repost-digest.sh"
    calendar = { hour = 9, minute = 12 }
"""
from __future__ import annotations

import argparse
import os
import plistlib
import sys
import tomllib
from pathlib import Path

LABEL_PREFIX = "ai.anicca"
# launchd hands a job a minimal PATH. Homebrew covers python/tmux/openclaw, but npm-global
# binaries -- the model CLI among them -- live under ~/.local/bin, and leaving it out makes a loop
# depend on its own fallback guesswork instead of on its environment.
DEFAULT_PATH_PARTS = ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
                      "/usr/sbin", "/sbin", "{home}/.local/bin")


def expand(value: str, home: Path) -> str:
    return str(Path(os.path.expandvars(value.replace("~", str(home)))))


def build(loop: dict, job_name: str, job: dict, home: Path, current: Path, logs: Path) -> dict:
    name = loop["name"]
    # A migration must not rename. Labels on this machine follow no single convention
    # (ai.anicca.hf-gig-apply-direct, ai.anicca.bounty-core-healthcheck, ai.anicca.hf-bounty-daily),
    # and they are referenced by healthchecks, self-heal scripts, tests and docs. Renaming while
    # moving a loop would break those quietly, at the same moment its code moved -- two changes to
    # untangle instead of one. An existing loop declares the label it already answers to; only new
    # loops take the generated convention.
    label = job.get("label") or f"{LABEL_PREFIX}.{name}-{job_name}"

    default_path = ":".join(p.format(home=home) for p in DEFAULT_PATH_PARTS)
    env = {"HOME": str(home), "PATH": job.get("path", default_path)}
    if loop.get("state_dir"):
        # Every loop needs to be told where its own state lives, because the code it runs from is a
        # read-only release and must not be the place a ledger accumulates.
        env[loop.get("state_env", f"{name.upper().replace('-', '_')}_STATE_DIR")] = \
            expand(loop["state_dir"], home)
    env.update({k: str(v) for k, v in (loop.get("env") or {}).items()})
    env.update({k: str(v) for k, v in (job.get("env") or {}).items()})

    plist = {
        "Label": label,
        "ProgramArguments": ["/bin/bash", str(current / job["program"])],
        "ProcessType": job.get("process_type", "Background"),
        "ThrottleInterval": int(job.get("throttle_seconds", 60)),
        "WorkingDirectory": str(home),
        "EnvironmentVariables": env,
        "StandardOutPath": str(logs / f"{name}-{job_name}.out.log"),
        "StandardErrorPath": str(logs / f"{name}-{job_name}.err.log"),
    }

    if "interval_seconds" in job:
        plist["StartInterval"] = int(job["interval_seconds"])
    elif "calendars" in job:
        plist["StartCalendarInterval"] = [
            {k.capitalize(): int(v) for k, v in calendar.items()}
            for calendar in job["calendars"]
        ]
    elif "calendar" in job:
        cal = job["calendar"]
        plist["StartCalendarInterval"] = {k.capitalize(): int(v) for k, v in cal.items()}
    else:
        raise SystemExit(f"{label}: needs interval_seconds or calendar")

    return plist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--home", default=str(Path.home()))
    ap.add_argument("--current", default=None,
                    help="release root the jobs resolve through (default ~/loops/current)")
    ap.add_argument("--logs", default=None)
    ap.add_argument("--only", help="generate a single loop by name")
    ap.add_argument("--diff", action="store_true", help="print what would change, write nothing")
    args = ap.parse_args()

    home = Path(args.home)
    current = Path(args.current) if args.current else home / "loops" / "current"
    logs = Path(args.logs) if args.logs else home / ".openclaw" / "logs"
    out_dir = Path(expand(args.out_dir, home))

    written = []
    for toml_path in sorted(Path(args.loops_dir).glob("*/loop.toml")):
        loop = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        if args.only and loop.get("name") != args.only:
            continue
        for job_name, job in (loop.get("jobs") or {}).items():
            plist = build(loop, job_name, job, home, current, logs)
            target = out_dir / f"{plist['Label']}.plist"
            body = plistlib.dumps(plist, sort_keys=True)
            existing = target.read_bytes() if target.exists() else None
            if args.diff:
                state = "unchanged" if existing == body else ("new" if existing is None else "CHANGED")
                print(f"{state:>9}  {target}")
                continue
            if existing == body:
                written.append((plist["Label"], "unchanged"))
                continue
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            written.append((plist["Label"], "written"))

    for label, state in written:
        print(f"{state:>9}  {label}")
    if not written and not args.diff:
        print("no loop.toml found", file=sys.stderr)


if __name__ == "__main__":
    main()
