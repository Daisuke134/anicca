#!/usr/bin/env python3
"""Read-only lm-loop commands. Lifecycle mutation is added in later slices."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

from runtime.loop.macos_launchd_inventory import extract_release, parse_disabled, parse_loaded
from runtime.loop.macos_loop_registry import validate_registry
from runtime.loop.lm_loop_apply import apply_registry, install_one
from runtime.loop.lm_loop_lifecycle import lifecycle, lifecycle_one
from runtime.loop.runtime_event import validate_runtime_event


ROOT = Path(__file__).resolve().parents[2]


def _next_eligible(cadence: dict) -> str:
    key, value = next(iter(cadence.items()))
    if key == "start_interval_seconds":
        return f"interval:{value}s"
    if key == "calendar_interval":
        return "calendar:" + json.dumps(value, sort_keys=True, separators=(",", ":"))
    return key.replace("_", "-")


def status_rows(registry: dict, *, loaded: dict, disabled: dict, events: dict,
                installed_releases: dict) -> list[dict]:
    validate_registry(registry)
    rows = []
    for loop_id in sorted(registry["loops"]):
        entry = registry["loops"][loop_id]
        label = entry["label"]
        runtime = loaded.get(label)
        if disabled.get(label):
            launchd_state = "disabled"
        elif runtime:
            launchd_state = "loaded-running" if runtime.get("pid") else "loaded-idle"
        else:
            launchd_state = "unloaded"
        event = events.get(loop_id) or {}
        rows.append({
            "loop_id": loop_id,
            "label": label,
            "domain": entry["domain"],
            "launchd_state": launchd_state,
            "pid": runtime.get("pid") if runtime else None,
            "last_exit": runtime.get("last_exit") if runtime else None,
            "installed_release_sha": installed_releases.get(label),
            "provider_route": entry["provider_route"],
            "provider": event.get("provider"),
            "profile_alias": event.get("profile_alias"),
            "last_pass": event.get("timestamp"),
            "last_terminal_result": event.get("status"),
            "effect_class": entry["effect_class"],
            "effect_status": event.get("effect_status", "unknown"),
            "event_release_sha": event.get("release_sha"),
            "next_eligible_run": _next_eligible(entry["cadence"]),
            "blocker": event.get("blocker"),
        })
    return rows


def doctor_report(registry: dict, *, installed_labels: set[str], loaded_labels: set[str],
                  existing_entrypoints: set[str]) -> dict:
    validate_registry(registry)
    retired = set(registry.get("retired_labels", []))
    managed = ({entry["label"] for entry in registry["loops"].values()}
               | set(registry.get("external_labels", [])) | retired)
    unmanaged = sorted((installed_labels | loaded_labels) - managed)
    missing = sorted(
        f"{loop_id}:{entry['entrypoint']}"
        for loop_id, entry in registry["loops"].items()
        if entry["entrypoint"] not in existing_entrypoints
    )
    return {
        "ok": not unmanaged and not missing and not ((installed_labels | loaded_labels) & retired),
        "registry_entries": len(registry["loops"]),
        "unmanaged_labels": unmanaged,
        "missing_entrypoints": missing,
        "retired_installed_labels": sorted((installed_labels | loaded_labels) & retired),
    }


def _launchctl(*args: str) -> str:
    result = subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "launchctl failed")
    return result.stdout


def _last_event(state_root: str) -> dict | None:
    path = Path(os.path.expanduser(state_root)) / "events.jsonl"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            value = json.loads(line)
            validate_runtime_event(value)
        except (json.JSONDecodeError, ValueError):
            continue
        return value
    return None


def _release_from_plist(path: Path) -> str | None:
    try:
        plist = plistlib.load(path.open("rb"))
    except Exception:
        return None
    args = list(map(str, plist.get("ProgramArguments") or []))
    release = extract_release(" ".join(args))
    if release:
        return release
    for arg in args:
        candidate = Path(os.path.expanduser(arg))
        try:
            if candidate.exists():
                release = extract_release(str(candidate.resolve()))
        except OSError:
            continue
        if release:
            return release
    return None


def collect_live(registry: dict) -> tuple[dict, dict, dict, set[str], set[str]]:
    loaded = parse_loaded(_launchctl("list"))
    disabled = parse_disabled(_launchctl("print-disabled", f"gui/{os.getuid()}"))
    plist_dir = Path.home() / "Library/LaunchAgents"
    installed = {path.stem for path in plist_dir.glob("ai.anicca.*.plist")}
    releases, events = {}, {}
    for loop_id, entry in registry["loops"].items():
        label = entry["label"]
        releases[label] = _release_from_plist(plist_dir / f"{label}.plist")
        event = _last_event(entry["state_root"])
        if event:
            events[loop_id] = event
    return loaded, disabled, events, releases, installed


def _select(rows: list[dict], target: str) -> list[dict]:
    if target == "all":
        return rows
    selected = [row for row in rows if row["loop_id"] == target]
    if not selected:
        raise ValueError(f"unknown loop id: {target}")
    return selected


def snapshot(registry: dict, target: str) -> list[dict]:
    loaded, disabled, events, releases, _ = collect_live(registry)
    return _select(status_rows(registry, loaded=loaded, disabled=disabled,
                               events=events, installed_releases=releases), target)


def _safe_launchctl(executable: Path, args: list[str]) -> tuple[int, str]:
    result = subprocess.run([str(executable), *args], capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout + result.stderr


def apply_live(release_root: Path, agents_dir: Path, launchctl_safe: Path) -> list[dict]:
    release_root = release_root.resolve()
    registry = json.loads((release_root / "config/loop-registry.json").read_text())
    manifest = json.loads((release_root / "RELEASE.json").read_text())
    release_sha = manifest.get("sha")
    plan = apply_registry(registry, release_root, release_sha, lambda item: item)
    preflight_rc, detail = _safe_launchctl(launchctl_safe, ["preflight"])
    if preflight_rc:
        raise RuntimeError(f"launchctl-safe preflight failed: {detail.strip()}")
    results = []
    for item in plan:
        target = agents_dir / f"{item['label']}.plist"
        if target.is_file() and target.read_bytes() == item["plist_bytes"]:
            rc, printed = _safe_launchctl(
                launchctl_safe, ["print", f"gui/{os.getuid()}/{item['label']}"])
            from runtime.loop.lm_loop_apply import _loaded_arguments
            loaded = _loaded_arguments(printed) if rc == 0 else []
            if loaded == item["expected_arguments"]:
                results.append({"ok": True, "label": item["label"],
                                "loaded_arguments": loaded, "release_sha": release_sha,
                                "changed": False})
                continue
        result = install_one(
            item, target, lambda args: _safe_launchctl(launchctl_safe, args))
        result["changed"] = True
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    commands = {"apply", "doctor", "start", "stop", "restart", "status", "watch"}
    if not args or args[0] not in commands:
        print("usage: lm-loop apply|doctor|start|stop|restart <loop-id|all>|status|watch [<loop-id|all>]", file=sys.stderr)
        return 2
    command = args[0]
    if command == "apply":
        release_root = Path(os.environ.get("LIFE_MANAGER_RELEASE_ROOT", "~/loops/current")).expanduser()
        agents_dir = Path(os.environ.get(
            "LIFE_MANAGER_LAUNCH_AGENTS_DIR", "~/Library/LaunchAgents")).expanduser()
        launchctl_safe = Path(os.environ.get(
            "LIFE_MANAGER_LAUNCHCTL_SAFE", str(release_root / "bin/launchctl-safe"))).expanduser()
        try:
            results = apply_live(release_root, agents_dir, launchctl_safe)
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
            return 1
        print(json.dumps(results, indent=2, sort_keys=True))
        return 0
    registry = validate_registry(json.loads((ROOT / "config/loop-registry.json").read_text()))
    if command in {"start", "stop", "restart"}:
        if len(args) != 2:
            print(json.dumps({"ok": False, "error": f"{command} requires <loop-id|all>"}))
            return 2
        target = args[1]
        if target != "all" and target not in registry["loops"]:
            print(json.dumps({"ok": False, "error": f"unknown loop id: {target}"}))
            return 2
        agents_dir = Path(os.environ.get(
            "LIFE_MANAGER_LAUNCH_AGENTS_DIR", "~/Library/LaunchAgents")).expanduser()
        launchctl_safe = Path(os.environ.get(
            "LIFE_MANAGER_LAUNCHCTL_SAFE", str(ROOT / "bin/launchctl-safe"))).expanduser()
        preflight_rc, detail = _safe_launchctl(launchctl_safe, ["preflight"])
        if preflight_rc:
            print(json.dumps({"ok": False, "error": detail.strip()}, sort_keys=True))
            return 1
        results = lifecycle(
            registry, command, target,
            lambda action, loop_id, entry: lifecycle_one(
                action, loop_id, entry, agents_dir,
                lambda launch_args: _safe_launchctl(launchctl_safe, launch_args)))
        print(json.dumps(results, indent=2, sort_keys=True))
        return 1 if any(row["return_code"] for row in results) else 0
    target = args[1] if len(args) > 1 else "all"
    if command == "doctor":
        loaded, _, _, _, installed = collect_live(registry)
        existing = {entry["entrypoint"] for entry in registry["loops"].values()
                    if (ROOT / entry["entrypoint"]).is_file()}
        report = doctor_report(registry, installed_labels=installed,
                               loaded_labels=set(loaded), existing_entrypoints=existing)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 1
    while True:
        print(json.dumps(snapshot(registry, target), indent=2, sort_keys=True), flush=True)
        if command == "status" or os.environ.get("LM_LOOP_WATCH_ONCE") == "1":
            return 0
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
