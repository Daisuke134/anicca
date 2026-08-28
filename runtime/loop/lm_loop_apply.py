"""Fail-closed plist generation and one-label rollback-safe launchd swap."""

from __future__ import annotations

import json
import os
import plistlib
import re
import tempfile
import time
from pathlib import Path
from typing import Callable

from runtime.loop.macos_loop_registry import validate_registry


def _plist(loop_id: str, entry: dict, release_root: Path, release_sha: str) -> bytes:
    executable = str(release_root / entry["entrypoint"])
    loop_runner = str(release_root / "bin/lm-loop-run")
    log_root = os.path.expanduser(entry["log_root"])
    value = {
        "Label": entry["label"],
        "ProgramArguments": [loop_runner, loop_id, str(release_root)],
        "ProcessType": "Background",
        "EnvironmentVariables": {
            "LIFE_MANAGER_LOOP_ID": loop_id,
            "LIFE_MANAGER_RELEASE_SHA": release_sha,
            "LIFE_MANAGER_STATE_ROOT": os.path.expanduser(entry["state_root"]),
        },
        "StandardOutPath": str(Path(log_root) / "launchd.out.log"),
        "StandardErrorPath": str(Path(log_root) / "launchd.err.log"),
    }
    key, cadence = next(iter(entry["cadence"].items()))
    if key == "start_interval_seconds":
        value["StartInterval"] = cadence
    elif key == "calendar_interval":
        value["StartCalendarInterval"] = cadence
    elif key == "run_at_load":
        value["RunAtLoad"] = True
    else:
        value["KeepAlive"] = True
    if loop_id.startswith(("article-", "writer-")):
        writer_root = str(release_root / "skills/writer-agent")
        value["EnvironmentVariables"].update({
            "ARTICLE_ROOT": writer_root, "ARTICLE_SKILL_DIR": writer_root,
            "LIFE_MANAGER_REPO": str(release_root),
        })
    return plistlib.dumps(value, fmt=plistlib.FMT_XML, sort_keys=True)


def build_apply_plan(registry: dict, release_root: Path, release_sha: str) -> list[dict]:
    validate_registry(registry)
    if not re.fullmatch(r"[0-9a-f]{40}", release_sha):
        raise ValueError("release SHA must be exact 40-character lowercase hex")
    release_root = release_root.resolve()
    try:
        manifest = json.loads((release_root / "RELEASE.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("release manifest missing or invalid") from exc
    if manifest.get("sha") != release_sha:
        raise ValueError("release manifest SHA mismatch")
    loop_runner = release_root / "bin/lm-loop-run"
    if not loop_runner.is_file() or not os.access(loop_runner, os.X_OK):
        raise ValueError("release loop runner missing or not executable")
    plan = []
    for loop_id in sorted(registry["loops"]):
        entry = registry["loops"][loop_id]
        executable = release_root / entry["entrypoint"]
        if not executable.is_file():
            raise ValueError(f"{loop_id}: missing entrypoint {entry['entrypoint']}")
        if not os.access(executable, os.X_OK):
            raise ValueError(f"{loop_id}: entrypoint is not executable {entry['entrypoint']}")
        plan.append({
            "loop_id": loop_id,
            "label": entry["label"],
            "plist_bytes": _plist(loop_id, entry, release_root, release_sha),
            "expected_arguments": [str(loop_runner), loop_id, str(release_root)],
            "release_sha": release_sha,
        })
    return plan


def apply_registry(registry: dict, release_root: Path, release_sha: str,
                   installer: Callable[[dict], dict], *, target: str | None = None) -> list[dict]:
    if target is not None:
        if target not in registry.get("loops", {}):
            raise ValueError(f"unknown apply target: {target}")
        registry = {**registry, "loops": {target: registry["loops"][target]}}
    plan = build_apply_plan(registry, release_root, release_sha)
    return [installer(item) for item in plan]


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _preserve_operational_attributes(new_bytes: bytes, old_bytes: bytes | None) -> bytes:
    if old_bytes is None:
        return new_bytes
    old, new = plistlib.loads(old_bytes), plistlib.loads(new_bytes)
    for key in ("WorkingDirectory", "ProcessType", "RunAtLoad", "ThrottleInterval", "Umask", "Nice"):
        if key in old:
            new[key] = old[key]
    new["EnvironmentVariables"] = {
        **(old.get("EnvironmentVariables") or {}),
        **(new.get("EnvironmentVariables") or {}),
    }
    return plistlib.dumps(new, fmt=plistlib.FMT_XML, sort_keys=True)


def _loaded_arguments(text: str) -> list[str]:
    arguments, inside = [], False
    for raw in text.splitlines():
        line = raw.strip()
        if line == "arguments = {":
            inside = True
        elif inside and line == "}":
            break
        elif inside and line:
            arguments.append(line)
    return arguments


def install_one(item: dict, target: Path,
                launchctl: Callable[[list[str]], tuple[int, str]], *, attempts: int = 3,
                sleeper: Callable[[float], None] = time.sleep) -> dict:
    label = item["label"]
    domain = f"gui/{os.getuid()}"
    service = f"{domain}/{label}"
    old_bytes = target.read_bytes() if target.is_file() else None
    initial_rc, _ = launchctl(["print", service])
    was_loaded = initial_rc == 0
    _atomic_write(target, _preserve_operational_attributes(item["plist_bytes"], old_bytes))
    launchctl(["bootout", service])
    sleeper(1.0)
    last_detail = ""
    retry_delays = (3.0, 10.0)
    for attempt in range(attempts):
        bootstrap_rc, last_detail = launchctl(["bootstrap", domain, str(target)])
        if bootstrap_rc == 0:
            print_rc, printed = launchctl(["print", service])
            loaded = _loaded_arguments(printed) if print_rc == 0 else []
            if loaded == item["expected_arguments"]:
                return {"ok": True, "label": label, "loaded_arguments": loaded,
                        "release_sha": item["release_sha"]}
        launchctl(["bootout", service])
        sleeper(retry_delays[min(attempt, len(retry_delays) - 1)])
    if old_bytes is None:
        if target.exists():
            target.unlink()
    else:
        _atomic_write(target, old_bytes)
    restored = not was_loaded
    if was_loaded and old_bytes is not None:
        old_args = list(map(str, plistlib.loads(old_bytes).get("ProgramArguments") or []))
        restore_rc, _ = launchctl(["bootstrap", domain, str(target)])
        print_rc, printed = launchctl(["print", service])
        restored = restore_rc == 0 and print_rc == 0 and _loaded_arguments(printed) == old_args
    if restored:
        raise RuntimeError(f"{label}: apply failed; restored previous job ({last_detail})")
    raise RuntimeError(f"{label}: apply failed and previous job restoration failed ({last_detail})")
