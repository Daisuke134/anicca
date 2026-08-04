#!/usr/bin/env python3
"""Reversibly quarantine the reviewed legacy marketing scheduler snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable


LAUNCH_LABEL = re.compile(r"^ai\.anicca\.(?:larry|reelclaw|watercolor)-[A-Za-z0-9._-]+$")
OPENCLAW_ID = re.compile(r"^(?:[0-9a-f]{8}-[0-9a-f-]{27}|monk-factory-en-recovery)$")


class QuarantineError(RuntimeError):
    def __init__(self, message: str, evidence: dict[str, Any] | None = None):
        super().__init__(message)
        self.evidence = evidence


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def parse_loaded(text: str) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    for line in text.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        pid, label = parts[0].strip(), parts[2].strip()
        result[label] = int(pid) if pid.isdigit() else None
    return result


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def select_targets(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    targets = [
        row for row in snapshot.get("records", [])
        if row.get("disposition") == "retire" and row.get("enabled") is True
    ]
    seen: set[tuple[str, str]] = set()
    for row in targets:
        runtime, identifier = row.get("runtime"), str(row.get("id") or "")
        key = (runtime, identifier)
        if key in seen:
            raise QuarantineError(f"duplicate target in snapshot: {runtime}:{identifier}")
        seen.add(key)
        if runtime == "launchd" and not LAUNCH_LABEL.fullmatch(identifier):
            raise QuarantineError(f"launchd target outside reviewed families: {identifier}")
        if runtime == "openclaw" and not OPENCLAW_ID.fullmatch(identifier):
            raise QuarantineError(f"invalid OpenClaw job id: {identifier}")
        if runtime not in {"launchd", "openclaw"}:
            raise QuarantineError(f"unsupported runtime: {runtime}")
    return targets


def preflight(
    snapshot: dict[str, Any],
    targets: list[dict[str, Any]],
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]],
) -> dict[str, int | None]:
    if snapshot.get("host_uid") != os.getuid():
        raise QuarantineError("snapshot UID does not match current user")
    loaded = parse_loaded(runner(["launchctl", "list"]).stdout)
    for row in targets:
        source = Path(row["source_path"])
        if not source.is_file() or sha256_file(source) != row.get("source_sha256"):
            raise QuarantineError(f"source changed since inventory: {row['runtime']}:{row['id']}")
        if row["runtime"] == "launchd" and loaded.get(row["id"]) is not None:
            raise QuarantineError(f"refusing to interrupt running publisher: {row['id']}")
    return loaded


def rollback(
    changed: list[dict[str, Any]],
    uid: int,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]],
) -> list[dict[str, Any]]:
    results = []
    for row in reversed(changed):
        commands: list[list[str]]
        if row["runtime"] == "launchd":
            commands = [
                ["launchctl", "enable", f"gui/{uid}/{row['id']}"],
                ["launchctl", "bootstrap", f"gui/{uid}", row["source_path"]],
            ]
        else:
            commands = [["openclaw", "cron", "enable", row["id"]]]
        entry = {"runtime": row["runtime"], "id": row["id"], "commands": [], "status": "restored"}
        for command in commands:
            try:
                runner(command)
                entry["commands"].append({"argv": command, "status": "ok"})
            except subprocess.CalledProcessError as exc:
                # bootstrap can legitimately report already-loaded after enable.
                if row["runtime"] == "launchd" and command[1] == "bootstrap":
                    entry["commands"].append({"argv": command, "status": "already_loaded_or_error"})
                else:
                    entry["commands"].append({"argv": command, "status": "error", "returncode": exc.returncode})
                    entry["status"] = "rollback_error"
        results.append(entry)
    return results


def quarantine(
    snapshot: dict[str, Any],
    apply: bool,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    targets = select_targets(snapshot)
    preflight(snapshot, targets, runner)
    uid = os.getuid()
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "captured_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mode": "apply" if apply else "dry_run",
        "snapshot_captured_at": snapshot.get("captured_at"),
        "target_count": len(targets),
        "results": [],
        "rollback": [],
        "status": "planned" if not apply else "applying",
    }
    if not apply:
        evidence["results"] = [
            {"runtime": row["runtime"], "id": row["id"], "status": "planned"}
            for row in targets
        ]
        return evidence

    changed: list[dict[str, Any]] = []
    try:
        for row in targets:
            if row["runtime"] == "launchd":
                commands = [
                    ["launchctl", "disable", f"gui/{uid}/{row['id']}"],
                    ["launchctl", "bootout", f"gui/{uid}/{row['id']}"],
                ]
            else:
                commands = [["openclaw", "cron", "disable", row["id"]]]
            entry = {"runtime": row["runtime"], "id": row["id"], "commands": [], "status": "applying"}
            evidence["results"].append(entry)
            changed.append(row)
            for command in commands:
                runner(command)
                entry["commands"].append({"argv": command, "status": "ok"})
            entry["status"] = "quarantined"
        evidence["status"] = "quarantined"
    except subprocess.CalledProcessError as exc:
        evidence["status"] = "failed_rolled_back"
        evidence["failure"] = {"argv": exc.cmd, "returncode": exc.returncode}
        evidence["rollback"] = rollback(changed, uid, runner)
        raise QuarantineError("quarantine command failed; attempted rollback", evidence) from exc
    return evidence


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--snapshot", type=Path, required=True)
    result.add_argument("--evidence", type=Path)
    result.add_argument("--apply", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    try:
        result = quarantine(snapshot, args.apply)
    except QuarantineError as exc:
        if args.evidence and exc.evidence:
            atomic_write(args.evidence, exc.evidence)
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.evidence:
        atomic_write(args.evidence, result)
    print(json.dumps({"status": result["status"], "targets": result["target_count"], "evidence": str(args.evidence) if args.evidence else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
