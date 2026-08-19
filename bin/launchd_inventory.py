#!/usr/bin/env python3
"""Read-only launchd inventory: declared ownership plus live launchctl truth."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.parsers.expat import ExpatError
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
JST = ZoneInfo("Asia/Tokyo")
DEFAULT_USAGE_LEDGER = Path.home() / ".local" / "state" / "anicca" / "telemetry" / "agent-usage.jsonl"


def load_registry(registry_path: Path) -> dict[str, Any]:
    """Load one legacy fixture or the production domain-fragment directory."""
    if registry_path.is_file():
        value = json.loads(registry_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("agents"), dict):
            raise ValueError(f"invalid launchd registry: {registry_path}")
        return value
    if not registry_path.is_dir():
        raise ValueError(f"launchd registry missing: {registry_path}")
    merged: dict[str, Any] = {}
    domains: list[str] = []
    for fragment_path in sorted(registry_path.glob("*.json")):
        fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
        if (
            not isinstance(fragment, dict)
            or fragment.get("version") != 1
            or not isinstance(fragment.get("domain"), str)
            or not fragment["domain"].strip()
            or not isinstance(fragment.get("agents"), dict)
        ):
            raise ValueError(f"invalid launchd registry fragment: {fragment_path}")
        if fragment["domain"] in domains:
            raise ValueError(f"duplicate launchd domain: {fragment['domain']}")
        domains.append(fragment["domain"])
        for label, metadata in fragment["agents"].items():
            if label in merged:
                raise ValueError(f"duplicate launchd label: {label}")
            if not isinstance(metadata, dict):
                raise ValueError(f"invalid launchd agent metadata: {label}")
            merged[label] = metadata
    if not domains:
        raise ValueError(f"launchd registry has no fragments: {registry_path}")
    return {"version": 1, "domains": domains, "agents": merged}


def schedule_from_plist(plist: dict[str, Any]) -> dict[str, Any]:
    if plist.get("KeepAlive"):
        return {"kind": "continuous", "when": "KeepAlive", "runs_per_day": None}
    calendar = plist.get("StartCalendarInterval")
    if isinstance(calendar, dict):
        hour, minute = calendar.get("Hour"), int(calendar.get("Minute", 0))
        clock = f"{int(hour or 0):02d}:{minute:02d}"
        if "Month" in calendar:
            when = f"month {int(calendar['Month'])} day {int(calendar.get('Day', 1))} {clock}"
            return {"kind": "calendar", "when": when, "runs_per_day": 1 / 365.2425}
        if "Day" in calendar:
            when = f"day {int(calendar['Day'])} {clock}"
            return {"kind": "calendar", "when": when, "runs_per_day": 12 / 365.2425}
        if "Weekday" in calendar:
            names = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
            weekday = int(calendar["Weekday"])
            when = f"{names[weekday] if 0 <= weekday < len(names) else f'weekday {weekday}'} {clock}"
            return {"kind": "calendar", "when": when, "runs_per_day": 1 / 7}
        if hour is None:
            return {"kind": "calendar", "when": f"hourly at :{minute:02d}", "runs_per_day": 24}
        return {"kind": "calendar", "when": f"{int(hour):02d}:{minute:02d}", "runs_per_day": 1}
    if isinstance(calendar, list):
        times = [schedule_from_plist({"StartCalendarInterval": item}) for item in calendar]
        return {
            "kind": "calendar",
            "when": ", ".join(item["when"] for item in times),
            "runs_per_day": sum(item["runs_per_day"] for item in times),
        }
    interval = plist.get("StartInterval")
    if isinstance(interval, int) and interval > 0:
        if interval % 3600 == 0:
            when = f"every {interval // 3600}h"
        elif interval % 60 == 0:
            when = f"every {interval // 60}m"
        else:
            when = f"every {interval}s"
        return {"kind": "interval", "when": when, "runs_per_day": 86400 // interval}
    if plist.get("RunAtLoad"):
        return {"kind": "load", "when": "on load", "runs_per_day": None}
    return {"kind": "on-demand", "when": "on demand", "runs_per_day": None}


def _normalized_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": candidate.get("provider"),
        "model": candidate.get("model"),
        "effort": candidate.get("effort"),
    }


def resolve_model_routes(metadata: dict[str, Any], runner_config: dict[str, Any]) -> list[dict[str, Any]]:
    declared = metadata.get("model_routes")
    if isinstance(declared, list):
        return [{
            "task_class": route.get("task_class", "external"),
            "candidates": [_normalized_candidate(item) for item in route.get("candidates", [])],
        } for route in declared]
    explicit = metadata.get("model_route")
    if isinstance(explicit, list):
        return [{"task_class": metadata.get("model_policy", "external"),
                 "candidates": [_normalized_candidate(item) for item in explicit]}]
    routes = []
    for task_class in metadata.get("task_classes", []):
        task = runner_config.get("task_classes", {}).get(task_class, {})
        routes.append({
            "task_class": task_class,
            "candidates": [_normalized_candidate(item) for item in task.get("candidates", [])],
        })
    return routes


def model_summary(routes: list[dict[str, Any]]) -> str:
    if not routes:
        return "none"
    rendered = []
    for route in routes:
        candidates = []
        for candidate in route["candidates"]:
            text = f"{candidate['provider']}/{candidate['model']}"
            if candidate.get("effort"):
                text += f" ({candidate['effort']})"
            candidates.append(text)
        chain = " → ".join(candidates) if candidates else "unconfigured"
        rendered.append(chain if len(routes) == 1 else f"{route['task_class']}: {chain}")
    return "; ".join(rendered)


def build_row(plist_path: Path, plist: dict[str, Any], metadata: dict[str, Any] | None,
              *, loaded: dict[str, dict[str, Any]], disabled: dict[str, bool],
              runner_config: dict[str, Any]) -> dict[str, Any]:
    label = str(plist["Label"])
    registered = metadata is not None
    metadata = metadata or {}
    if disabled.get(label) is True:
        actual_state = "disabled"
    elif label in loaded:
        actual_state = "loaded-running" if loaded[label].get("pid") else "loaded-idle"
    else:
        actual_state = "unloaded"
    schedule = schedule_from_plist(plist)
    override = metadata.get("schedule_override")
    if isinstance(override, dict):
        schedule = {
            "kind": override.get("kind", schedule["kind"]),
            "when": override.get("when", schedule["when"]),
            "runs_per_day": override.get("runs_per_day", schedule["runs_per_day"]),
        }
    routes = resolve_model_routes(metadata, runner_config)
    return {
        "label": label,
        "loop": metadata.get("loop", "unregistered"),
        "role": metadata.get("role", "unregistered"),
        "owner": metadata.get("owner", "unregistered"),
        "desired_state": metadata.get("desired_state", "unregistered"),
        "actual_state": actual_state,
        "registered": registered,
        "plist_path": str(plist_path),
        "source_path": metadata.get("source_path"),
        "program_arguments": plist.get("ProgramArguments", []),
        "schedule_kind": schedule["kind"],
        "when": schedule["when"],
        "runs_per_day": schedule["runs_per_day"],
        "max_runs_per_day": override.get("max_runs_per_day") if isinstance(override, dict) else None,
        "model_routes": routes,
        "model_summary": model_summary(routes),
        "usage_owner": metadata.get("usage_owner", bool(routes)),
        "tokens_per_day": None,
        "token_measurement": "unmeasured",
    }


def build_invalid_row(plist_path: Path, metadata: dict[str, Any] | None,
                      runner_config: dict[str, Any], error: Exception) -> dict[str, Any]:
    metadata = metadata or {}
    routes = resolve_model_routes(metadata, runner_config)
    return {
        "label": plist_path.stem,
        "loop": metadata.get("loop", "unregistered"),
        "role": metadata.get("role", "invalid-plist"),
        "owner": metadata.get("owner", "unregistered"),
        "desired_state": metadata.get("desired_state", "unregistered"),
        "actual_state": "invalid-plist",
        "registered": bool(metadata),
        "plist_path": str(plist_path),
        "source_path": metadata.get("source_path"),
        "program_arguments": [],
        "schedule_kind": "invalid",
        "when": "invalid plist",
        "runs_per_day": None,
        "max_runs_per_day": None,
        "model_routes": routes,
        "model_summary": model_summary(routes),
        "usage_owner": False,
        "tokens_per_day": None,
        "token_measurement": "unmeasured",
        "error": str(error),
    }


def parse_launchctl_list(text: str) -> dict[str, dict[str, Any]]:
    loaded = {}
    for line in text.splitlines():
        fields = line.split(maxsplit=2)
        if len(fields) != 3 or fields[0] == "PID":
            continue
        pid = int(fields[0]) if fields[0].isdigit() else None
        last_exit = int(fields[1]) if re.fullmatch(r"-?\d+", fields[1]) else None
        loaded[fields[2]] = {"pid": pid, "last_exit": last_exit}
    return loaded


def parse_disabled(text: str) -> dict[str, bool]:
    return {label: state == "disabled" for label, state in re.findall(
        r'"([^"]+)"\s*=>\s*(enabled|disabled)', text
    )}


def _launchctl(args: list[str]) -> str:
    completed = subprocess.run(args, text=True, capture_output=True, check=False, timeout=10)
    return completed.stdout


def load_plist(plist_path: Path) -> dict[str, Any]:
    try:
        with plist_path.open("rb") as handle:
            return plistlib.load(handle)
    except (plistlib.InvalidFileException, ExpatError) as parse_error:
        try:
            native = subprocess.run(
                ["plutil", "-convert", "json", "-o", "-", str(plist_path)],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
        except OSError:
            raise parse_error
        if native.returncode == 0:
            try:
                parsed = json.loads(native.stdout)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        raise parse_error


def attach_token_usage(rows: list[dict[str, Any]], ledger_path: Path, date_jst: str) -> None:
    totals: dict[str, int] = {}
    measured: dict[str, int] = {}
    unavailable: dict[str, int] = {}
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            event = json.loads(line)
            event_date = datetime.fromisoformat(
                str(event["timestamp"]).replace("Z", "+00:00")
            ).astimezone(JST).date().isoformat()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        if event_date != date_jst or not isinstance(event.get("loop"), str):
            continue
        loop = event["loop"]
        token_total = event.get("tokens", {}).get("total")
        if event.get("measurement") == "provider_reported" and isinstance(token_total, int):
            totals[loop] = totals.get(loop, 0) + token_total
            measured[loop] = measured.get(loop, 0) + 1
        else:
            unavailable[loop] = unavailable.get(loop, 0) + 1
    for row in rows:
        if not row.get("usage_owner", True):
            continue
        loop = row["loop"]
        measured_count = measured.get(loop, 0)
        unavailable_count = unavailable.get(loop, 0)
        if measured_count:
            row["tokens_per_day"] = totals.get(loop, 0)
            row["token_measurement"] = (
                f"provider_reported:{measured_count}; unavailable:{unavailable_count}"
            )
        elif unavailable_count:
            row["token_measurement"] = f"unavailable:{unavailable_count}"


def collect_rows(registry_path: Path, launch_agents: Path,
                 runner_config_path: Path) -> list[dict[str, Any]]:
    registry = load_registry(registry_path)
    runner_config = json.loads(runner_config_path.read_text(encoding="utf-8"))
    loaded = parse_launchctl_list(_launchctl(["launchctl", "list"]))
    disabled = parse_disabled(_launchctl(["launchctl", "print-disabled", f"gui/{os.getuid()}"]))
    agents = registry.get("agents", {})
    rows, seen = [], set()
    for plist_path in sorted(launch_agents.glob("*.plist")):
        try:
            plist = load_plist(plist_path)
        except (plistlib.InvalidFileException, ExpatError) as error:
            inferred_label = plist_path.stem
            rows.append(build_invalid_row(
                plist_path, agents.get(inferred_label), runner_config, error
            ))
            seen.add(inferred_label)
            continue
        label = plist.get("Label")
        if not isinstance(label, str):
            continue
        rows.append(build_row(plist_path, plist, agents.get(label), loaded=loaded,
                              disabled=disabled, runner_config=runner_config))
        seen.add(label)
    for label, metadata in agents.items():
        if label not in seen:
            rows.append(build_row(Path(metadata.get("source_path", "missing")), {"Label": label}, metadata,
                                  loaded=loaded, disabled=disabled, runner_config=runner_config))
    return sorted(rows, key=lambda row: (not row["registered"], row["loop"], row["label"]))


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Loop | Label | State | Model / effort | When | Runs/day | Tokens/day | Coverage | Owner |",
        "|---|---|---|---|---|---:|---:|---|---|",
    ]
    for row in rows:
        runs = row["runs_per_day"]
        maximum = row.get("max_runs_per_day")
        if maximum is not None:
            runs = f"{runs} normal; ≤{maximum} failure"
        elif isinstance(runs, float) and not runs.is_integer():
            runs = f"{runs:.3f} avg"
        elif runs is None:
            runs = "continuous"
        values = [row["loop"], row["label"], row["actual_state"], row["model_summary"], row["when"],
                  runs, row["tokens_per_day"] if row["tokens_per_day"] is not None else "unmeasured",
                  row.get("token_measurement", "unmeasured"), row["owner"]]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in values) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=ROOT / "config" / "launchd" / "agents")
    parser.add_argument("--launch-agents", type=Path, default=Path.home() / "Library" / "LaunchAgents")
    parser.add_argument("--runner-config", type=Path, default=ROOT / "skills" / "agent-runner" / "config.json")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--registered-only", action="store_true")
    parser.add_argument("--usage-ledger", type=Path, default=DEFAULT_USAGE_LEDGER)
    parser.add_argument("--usage-date")
    args = parser.parse_args()
    rows = collect_rows(args.registry, args.launch_agents, args.runner_config)
    usage_date = args.usage_date or (datetime.now(JST).date() - timedelta(days=1)).isoformat()
    attach_token_usage(rows, args.usage_ledger, usage_date)
    if args.registered_only:
        rows = [row for row in rows if row["registered"]]
    if args.format == "json":
        print(json.dumps({"version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
                          "agents": rows}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(rows), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
