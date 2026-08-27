#!/usr/bin/env python3
"""Reversibly wire the existing daily mine and weekly review schedules to Gate 8."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import plistlib
import shutil
import subprocess


HERE = pathlib.Path(__file__).resolve().parent
ENGINE_ROOT = HERE.parent
REPO_ROOT = ENGINE_ROOT.parents[2]


def _read(path):
    with pathlib.Path(path).open("rb") as handle:
        return plistlib.load(handle)


def _write(path, value):
    with pathlib.Path(path).open("wb") as handle:
        plistlib.dump(value, handle, sort_keys=True)


def _default_launchctl(args):
    return subprocess.run(["launchctl", *args], capture_output=True, text=True).returncode


def install(*, repo=REPO_ROOT, home=pathlib.Path.home(), backup_root=None, apply=False, launchctl=None):
    repo = pathlib.Path(repo).resolve()
    home = pathlib.Path(home).resolve()
    backup_root = pathlib.Path(backup_root or ENGINE_ROOT / "evidence" / "schedulers" / "gate8-backups")
    launchctl = launchctl or _default_launchctl
    launch_agents = home / "Library" / "LaunchAgents"
    daily_path = launch_agents / "ai.anicca.marketing-mine-daily.plist"
    weekly_path = launch_agents / "ai.anicca.marketing-weekly-review.plist"
    if not daily_path.is_file() or not weekly_path.is_file():
        raise ValueError("Gate 8 requires the existing daily mine and weekly review plists")
    daily = _read(daily_path)
    weekly = _read(weekly_path)
    daily_args = daily.get("ProgramArguments")
    expected_runner = str(repo / "skills/earn/marketing-engine/report/scheduled_runner.py")
    if not isinstance(daily_args, list) or len(daily_args) < 3 or daily_args[-1] != "mine" or expected_runner not in daily_args:
        raise ValueError("daily mine schedule does not own the canonical mine lane")

    expected_weekly_args = [str(repo / "skills/earn/marketing-engine/bin/lm"), "intel", "gap", "--telegram"]
    log_root = home / "Library" / "Logs" / "AniccaMarketing"
    expected_weekly = dict(weekly)
    expected_weekly["ProgramArguments"] = expected_weekly_args
    expected_weekly["WorkingDirectory"] = str(repo)
    expected_weekly["StandardOutPath"] = str(log_root / "intel-gap.out.log")
    expected_weekly["StandardErrorPath"] = str(log_root / "intel-gap.err.log")
    weekly_change = weekly != expected_weekly
    result = {
        "schema_version": "marketing.gate8-schedules.v1",
        "mode": "apply" if apply else "plan",
        "daily": {
            "path": str(daily_path), "label": daily.get("Label"),
            "would_change": False, "changed": False,
            "program_arguments": daily_args,
            "cadence": daily.get("StartCalendarInterval"),
        },
        "weekly": {
            "path": str(weekly_path), "label": weekly.get("Label"),
            "would_change": weekly_change, "changed": False,
            "program_arguments": expected_weekly_args,
            "cadence": weekly.get("StartCalendarInterval"),
        },
    }
    if not apply or not weekly_change:
        return result

    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / weekly_path.name
    if not backup_path.exists():
        shutil.copy2(weekly_path, backup_path)
    log_root.mkdir(parents=True, exist_ok=True)
    _write(weekly_path, expected_weekly)
    domain = f"gui/{os.getuid()}"
    bootout = launchctl(["bootout", domain, str(weekly_path)])
    bootstrap = launchctl(["bootstrap", domain, str(weekly_path)])
    if bootstrap != 0:
        shutil.copy2(backup_path, weekly_path)
        launchctl(["bootstrap", domain, str(weekly_path)])
        raise RuntimeError(f"weekly bootstrap failed: {bootstrap}; backup restored")
    result["weekly"].update({
        "changed": True,
        "backup_path": str(backup_path),
        "bootout_returncode": bootout,
        "bootstrap_returncode": bootstrap,
    })
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        result = install(apply=args.apply)
    except (OSError, ValueError, RuntimeError, plistlib.InvalidFileException) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
