#!/usr/bin/env python3
"""Inventory legacy marketing schedulers without mutating them."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import plistlib
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any


INTEGRATION_ID = re.compile(r"\bcm[a-z0-9]{20,}\b")
LAUNCH_FAMILIES = ("larry", "reelclaw", "watercolor", "marketing")
OPENCLAW_FAMILY = re.compile(r"larry|reelclaw|watercolor|monk-factory|yangmun-monk", re.I)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_launchctl_list(text: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in text.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        pid, status, label = (part.strip() for part in parts[:3])
        result[label] = {
            "loaded": True,
            "pid": int(pid) if pid.isdigit() else None,
            "last_exit": int(status) if re.fullmatch(r"-?\d+", status) else None,
        }
    return result


def normalize_schedule(plist: dict[str, Any]) -> dict[str, Any]:
    if plist.get("StartCalendarInterval") is not None:
        value = plist["StartCalendarInterval"]
        entries = value if isinstance(value, list) else [value]
        return {"kind": "calendar", "entries": entries}
    if plist.get("StartInterval") is not None:
        return {"kind": "interval", "seconds": plist["StartInterval"]}
    return {"kind": "conditions", "run_at_load": bool(plist.get("RunAtLoad"))}


def launch_family(label: str) -> str | None:
    for family in LAUNCH_FAMILIES:
        if label.startswith(f"ai.anicca.{family}-") or label == f"ai.anicca.{family}":
            return family
    return None


def load_larry_accounts(path: Path) -> dict[str, list[str]]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for key, row in (data.get("accounts") or {}).items():
        result[key] = [
            value
            for value in (
                row.get("tiktok_connection"),
                row.get("instagram_connection"),
            )
            if value
        ]
    return result


def integration_ids_from_command(command: list[str], larry_accounts: dict[str, list[str]]) -> list[str]:
    joined = " ".join(command)
    ids = set(INTEGRATION_ID.findall(joined))
    if "--account-key" in command:
        index = command.index("--account-key")
        if index + 1 < len(command):
            ids.update(larry_accounts.get(command[index + 1], []))
    return sorted(ids)


def launch_records(
    plist_dir: Path,
    launchctl_text: str,
    larry_config: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    loaded = parse_launchctl_list(launchctl_text)
    larry_accounts = load_larry_accounts(larry_config)
    records = []
    invalid = []
    for path in sorted(plist_dir.glob("*.plist")):
        raw = path.read_bytes()
        try:
            plist = plistlib.loads(raw)
        except Exception as exc:
            invalid.append({"path": str(path), "error": type(exc).__name__})
            continue
        label = str(plist.get("Label") or "")
        family = launch_family(label)
        if family is None:
            continue
        command = list(plist.get("ProgramArguments") or [])
        if not command and plist.get("Program"):
            command = [str(plist["Program"])]
        runtime = loaded.get(label, {"loaded": False, "pid": None, "last_exit": None})
        publisher = family in {"larry", "reelclaw", "watercolor"} and not any(
            marker in label for marker in ("library-filler", "strategy-updater")
        )
        records.append(
            {
                "runtime": "launchd",
                "id": label,
                "label": label,
                "family": family,
                "source_path": str(path),
                "source_sha256": sha256_bytes(raw),
                "command": command,
                "command_sha256": sha256_bytes(json.dumps(command, ensure_ascii=False).encode()),
                "schedule": normalize_schedule(plist),
                "integration_ids": integration_ids_from_command(command, larry_accounts),
                "external_action": "publish" if publisher else "none",
                "disposition": "retire" if family != "marketing" else "migrate",
                "loaded": runtime["loaded"],
                "enabled": runtime["loaded"],
                "pid": runtime["pid"],
                "last_exit": runtime["last_exit"],
                "last_status": None,
                "last_run_at": None,
                "next_run_at": None,
                "rollback": [
                    "launchctl",
                    "enable",
                    f"gui/{os.getuid()}/{label}",
                    "&&",
                    "launchctl",
                    "bootstrap",
                    f"gui/{os.getuid()}",
                    str(path),
                ],
            }
        )
    return records, invalid


def monk_integration_ids(name: str, monk_env: Path) -> list[str]:
    """Resolve legacy monk account IDs from its config, never from a guess."""
    lowered = name.lower()
    if not monk_env.is_file():
        return []
    prefix = "POSTIZ_JP_" if "watercolor" in lowered else "POSTIZ_EN_"
    result = []
    for line in monk_env.read_text(errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.startswith(prefix) and key.endswith("_INTEGRATION") and value.strip():
            result.append(value.strip().strip("\"'"))
    return sorted(set(result))


def openclaw_records(
    jobs_path: Path,
    monk_env: Path | None = None,
    live_get: Any | None = None,
) -> list[dict[str, Any]]:
    if not jobs_path.is_file():
        return []
    raw = jobs_path.read_bytes()
    jobs = json.loads(raw).get("jobs") or []
    records = []
    for stored_job in jobs:
        stored_name = str(stored_job.get("name") or stored_job.get("id") or "")
        if not OPENCLAW_FAMILY.search(stored_name):
            continue
        live_job = live_get(str(stored_job.get("id"))) if live_get else None
        job = live_job or stored_job
        name = str(job.get("name") or stored_name)
        if not OPENCLAW_FAMILY.search(name):
            continue
        message = str((job.get("payload") or {}).get("message") or job.get("message") or "")
        state = job.get("state") or {}
        integration_ids = set(INTEGRATION_ID.findall(message))
        if monk_env and any(marker in name.lower() for marker in ("monk", "yangmun", "watercolor")):
            integration_ids.update(monk_integration_ids(name, monk_env))
        records.append(
            {
                "runtime": "openclaw",
                "id": str(job.get("id")),
                "label": name,
                "family": "openclaw-legacy-marketing",
                "source_path": str(jobs_path),
                "source_sha256": sha256_bytes(raw),
                "command": message,
                "command_sha256": sha256_bytes(message.encode()),
                "schedule": job.get("schedule"),
                "integration_ids": sorted(integration_ids),
                "external_action": "publish" if any(
                    marker in name.lower()
                    for marker in ("larry", "reelclaw", "watercolor", "monk")
                ) and "strategy" not in name.lower() and "trend" not in name.lower() else "none",
                "disposition": "retire",
                "loaded": bool(job.get("enabled")),
                "enabled": bool(job.get("enabled")),
                "store_enabled": bool(stored_job.get("enabled")),
                "gateway_live_lookup": live_job is not None,
                "pid": None,
                "last_exit": None,
                "last_status": state.get("lastStatus"),
                "last_run_at": state.get("lastRunAtMs"),
                "next_run_at": state.get("nextRunAtMs"),
                "rollback": ["openclaw", "cron", "enable", str(job.get("id"))],
            }
        )
    return records


def openclaw_live_get(job_id: str) -> dict[str, Any] | None:
    completed = subprocess.run(
        ["openclaw", "cron", "get", job_id],
        check=False,
        capture_output=True,
        text=True,
        timeout=35,
    )
    if completed.returncode != 0:
        return None
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def read_env(paths: list[Path], key: str) -> str | None:
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return None


def fetch_postiz_integrations(api_key: str | None) -> dict[str, dict[str, Any]]:
    if not api_key:
        return {}
    request = urllib.request.Request(
        "https://api.postiz.com/public/v1/integrations",
        headers={"Authorization": api_key},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        rows = json.load(response)
    return {
        str(row.get("id")): {
            "integration_id": row.get("id"),
            "platform": row.get("identifier"),
            "profile": row.get("profile"),
            "name": row.get("name"),
            "disabled": row.get("disabled"),
        }
        for row in rows
        if row.get("id")
    }


def add_accounts(records: list[dict[str, Any]], integrations: dict[str, dict[str, Any]]) -> None:
    for record in records:
        record["accounts"] = [
            integrations.get(integration_id, {
                "integration_id": integration_id,
                "platform": None,
                "profile": None,
                "name": None,
                "disabled": None,
            })
            for integration_id in record["integration_ids"]
        ]


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    if args.launchctl_file:
        launchctl_text = args.launchctl_file.read_text(encoding="utf-8")
    else:
        launchctl_text = subprocess.run(
            ["launchctl", "list"], check=True, capture_output=True, text=True
        ).stdout
    records, invalid = launch_records(args.plist_dir, launchctl_text, args.larry_config)
    live_get = None if args.no_openclaw_live else openclaw_live_get
    records.extend(openclaw_records(args.openclaw_jobs, args.monk_env, live_get))
    api_key = None if args.no_postiz else read_env(args.env_files, "POSTIZ_API_KEY")
    integrations = fetch_postiz_integrations(api_key)
    add_accounts(records, integrations)
    return {
        "schema_version": 1,
        "captured_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "host_uid": os.getuid(),
        "postiz_live_lookup": bool(api_key),
        "openclaw_gateway_live_lookup": not args.no_openclaw_live,
        "invalid_plists": invalid,
        "summary": {
            "records": len(records),
            "launchd_records": sum(row["runtime"] == "launchd" for row in records),
            "openclaw_records": sum(row["runtime"] == "openclaw" for row in records),
            "loaded_or_enabled_retire": sum(
                row["disposition"] == "retire" and row["enabled"] for row in records
            ),
            "enabled_publishers": sum(
                row["external_action"] == "publish" and row["enabled"] for row in records
            ),
        },
        "records": sorted(records, key=lambda row: (row["runtime"], row["label"], row["id"])),
    }


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parser() -> argparse.ArgumentParser:
    home = Path.home()
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--plist-dir", type=Path, default=home / "Library/LaunchAgents")
    result.add_argument("--launchctl-file", type=Path)
    result.add_argument("--openclaw-jobs", type=Path, default=home / ".openclaw/cron/jobs.json")
    result.add_argument("--monk-env", type=Path, default=home / "anicca-monk-factory/.env")
    result.add_argument("--no-openclaw-live", action="store_true")
    result.add_argument(
        "--larry-config",
        type=Path,
        default=home / "profitable-claude/config/openclaw/larry-fixed-strings.json",
    )
    result.add_argument(
        "--env-files",
        type=Path,
        nargs="*",
        default=[home / "anicca/.env", home / ".openclaw/.env"],
    )
    result.add_argument("--no-postiz", action="store_true")
    result.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    inventory = build_inventory(args)
    encoded = json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        atomic_write(args.output, encoded)
        print(json.dumps({"status": "written", "output": str(args.output), **inventory["summary"]}))
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
