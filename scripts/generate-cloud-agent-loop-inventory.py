#!/usr/bin/env python3
"""Emit the cloud-migration loop inventory as TSV without exposing secrets.

The generator intentionally reads only scheduler metadata. It never emits plist
EnvironmentVariables, OpenClaw payload bodies, delivery content, logs, cookies,
or credentials.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


HOME = Path.home()
LAUNCH_AGENTS = HOME / "Library" / "LaunchAgents"
OPENCLAW_JOBS = HOME / ".openclaw" / "cron" / "jobs.json"
REPO = Path(__file__).resolve().parents[1]

FIELDS = (
    "inventory_id",
    "source_type",
    "owner",
    "scope",
    "current_location",
    "trigger",
    "entrypoint",
    "state",
    "migration_target",
    "evidence",
)

PRODUCT_TERMS = re.compile(
    r"affiliate|article|bounty|capafy|cfo|clip|economy|earn|founder|franklin|gig|"
    r"hunter|marketing|money|reel|revenue|social|trade|x402",
    re.IGNORECASE,
)
RUNTIME_TERMS = re.compile(
    r"agentmail|ask|ceo|life-manager|meeting|openclaw|phone|slack|telegram",
    re.IGNORECASE,
)
OPS_TERMS = re.compile(
    r"audit|backup|cleanup|health|janitor|memory|monitor|report|sync|watchdog",
    re.IGNORECASE,
)


def compact(value: Any) -> str:
    """Return one safe TSV cell; never serialize arbitrary nested content."""
    return re.sub(r"[\t\r\n]+", " ", str(value)).strip()


def public_path(value: str | Path) -> str:
    """Normalize the local user home so tracked artifacts contain no username."""
    text = compact(value)
    home = str(HOME)
    if text == home:
        return "~"
    if text.startswith(home + os.sep):
        return "~" + text[len(home) :]
    return text


def safe_path_token(value: Any) -> str | None:
    """Return a declared script path when its syntax is fail-closed safe."""
    if not isinstance(value, str) or not value:
        return None
    if re.search(r"[\s;|&$()<>`'\"]", value):
        return None
    path = Path(value)
    if path.suffix.lower() not in {".sh", ".py", ".js", ".mjs", ".ts", ".rb"}:
        return None
    if value.startswith("~/"):
        return "~/" + Path(value[2:]).as_posix()
    if path.is_absolute():
        return public_path(path)
    if path.parts and path.parts[0] == "..":
        return None
    return path.as_posix()


def resolve_declared_script(value: str) -> Path:
    if value.startswith("~/"):
        return HOME / value[2:]
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def declared_script_path(data: dict[str, Any]) -> str | None:
    args = data.get("ProgramArguments") or []
    if not isinstance(args, list):
        return None
    raw_executable = compact(data.get("Program") or (args[0] if args else "unknown"))
    shell = Path(raw_executable).name in {"sh", "bash", "zsh", "fish", "dash", "ksh"}
    if shell and any(item in {"-c", "-lc"} for item in args[1:] if isinstance(item, str)):
        return None
    for item in args[1:]:
        safe_path = safe_path_token(item)
        if safe_path and item != raw_executable:
            return safe_path
    return None


def state_with_declared_entrypoint(state: str, script_path: str | None) -> str:
    if script_path and not resolve_declared_script(script_path).is_file():
        return f"{state};declared_entrypoint_missing"
    return state


def scope_for(name: str) -> str:
    if name.startswith("actions.runner") or name.startswith("homebrew."):
        return "developer_infrastructure"
    if PRODUCT_TERMS.search(name):
        return "product_loop_candidate"
    if RUNTIME_TERMS.search(name):
        return "product_runtime_candidate"
    if OPS_TERMS.search(name):
        return "operations_support"
    return "needs_scope_review"


def owner_for_launchd(label: str, entrypoint: str) -> str:
    if label.startswith("actions.runner"):
        return "GitHub Actions / anicca-products"
    if label.startswith("homebrew."):
        return "Local package service"
    if label.startswith("ai.openclaw") or any(
        token in entrypoint for token in ("/.openclaw/", "~/.openclaw/")
    ):
        return "Anicca OpenClaw"
    if any(token in entrypoint for token in ("/profitable-claude/", "~/profitable-claude/")):
        return "Claude-p earn loops"
    if any(token in entrypoint for token in ("/anicca-oss-pipecat/", "~/anicca-oss-pipecat/")):
        return "Anicca meeting / Pipecat"
    if any(token in entrypoint for token in ("/anicca-project/", "~/anicca-project/")):
        return "Life Manager / anicca-products"
    if any(
        token in entrypoint
        for token in ("/anicca/", "~/anicca/", "/anicca-oss/", "~/anicca-oss/")
    ):
        return "Anicca colony"
    return "Dais local automation"


def target_for(scope: str, enabled: bool = True) -> str:
    if not enabled:
        return "archive_or_remove_after_review"
    if scope == "product_loop_candidate":
        return "DigitalOcean_bridge_then_Life_Manager_module"
    if scope == "product_runtime_candidate":
        return "managed_runtime_or_Life_Manager_module"
    if scope == "operations_support":
        return "cloud_bridge_or_managed_operations"
    if scope == "developer_infrastructure":
        return "retain_local_dev_or_replace_with_managed_service"
    return "classify_in_TODO_5_and_6"


def launchctl_snapshot() -> tuple[dict[str, tuple[str, str]], set[str]]:
    loaded: dict[str, tuple[str, str]] = {}
    disabled: set[str] = set()
    domain = f"gui/{os.getuid()}"

    result = subprocess.run(
        ["launchctl", "print", domain], text=True, capture_output=True, check=False
    )
    for line in result.stdout.splitlines():
        match = re.match(r"^\s*(\d+|-)\s+(-?\d+|-)\s+(\S+)\s*$", line)
        if match:
            pid, status, label = match.groups()
            loaded[label] = (pid, status)

    result = subprocess.run(
        ["launchctl", "print-disabled", domain],
        text=True,
        capture_output=True,
        check=False,
    )
    for label, value in re.findall(r'"([^"]+)"\s*=>\s*(enabled|disabled)', result.stdout):
        if value == "disabled":
            disabled.add(label)
    return loaded, disabled


def safe_launchd_entrypoint(data: dict[str, Any]) -> str:
    args = data.get("ProgramArguments") or []
    raw_executable = compact(data.get("Program") or (args[0] if args else "unknown"))
    executable = public_path(raw_executable)
    if re.search(r"[\s;|&$()<>`'\"]", raw_executable):
        executable = "unsafe_executable_redacted"
    if not isinstance(args, list):
        return executable
    # A shell command body is opaque and may contain credentials or personal data.
    # Detect -c/-lc before looking at absolute-path-shaped arguments inside it.
    shell = Path(raw_executable).name in {"sh", "bash", "zsh", "fish", "dash", "ksh"}
    if shell and any(item in {"-c", "-lc"} for item in args[1:] if isinstance(item, str)):
        return f"{executable} <shell-command-redacted>"
    # Include at most one real, metachar-free script path. Never print arbitrary
    # arguments, flags, environment assignments, prompts, or command bodies.
    for item in args[1:]:
        safe_path = safe_path_token(item)
        if safe_path and item != raw_executable:
            return f"{executable} {safe_path}"
    return executable


def launchd_classification(
    label: str, entrypoint: str, parse_state: str | None, disabled: bool
) -> tuple[str, str, str]:
    """Return owner, scope, and target, failing closed for unparsed plists."""
    if parse_state:
        return "unverified", "needs_scope_review", "classify_before_migration"
    scope = scope_for(label)
    return owner_for_launchd(label, entrypoint), scope, target_for(scope, enabled=not disabled)


def launchd_trigger(data: dict[str, Any]) -> str:
    parts: list[str] = []
    if "StartInterval" in data:
        parts.append(f"interval={data['StartInterval']}s")
    if "StartCalendarInterval" in data:
        value = data["StartCalendarInterval"]
        if isinstance(value, dict):
            safe = ",".join(f"{k}={value[k]}" for k in sorted(value))
            parts.append(f"calendar({safe})")
        elif isinstance(value, list):
            parts.append(f"calendar_entries={len(value)}")
    if data.get("KeepAlive"):
        parts.append("keepalive")
    if data.get("RunAtLoad"):
        parts.append("run_at_load")
    return "+".join(parts) or "manual_or_event"


def launchd_rows() -> Iterable[dict[str, str]]:
    loaded, disabled = launchctl_snapshot()
    for filename in sorted(glob.glob(str(LAUNCH_AGENTS / "*.plist"))):
        path = Path(filename)
        label = path.stem
        try:
            with path.open("rb") as handle:
                data = plistlib.load(handle)
            label = compact(data.get("Label") or label)
            entrypoint = safe_launchd_entrypoint(data)
            declared_script = declared_script_path(data)
            trigger = launchd_trigger(data)
            parse_state = None
        except Exception as error:  # inventory parse failures instead of dropping them
            data = {}
            entrypoint = "unparsed_plist_entrypoint"
            declared_script = None
            trigger = "unparsed_plist_trigger"
            parse_state = f"parse_error:{error.__class__.__name__}"

        owner, scope, migration_target = launchd_classification(
            label, entrypoint, parse_state, label in disabled
        )
        if parse_state:
            state = parse_state
        elif label in disabled:
            state = "disabled_by_launchctl"
        elif label in loaded:
            state = "loaded"
        else:
            state = "installed_not_loaded"
        state = state_with_declared_entrypoint(state, declared_script)

        yield {
            "inventory_id": f"launchd:{label}",
            "source_type": "launchd",
            "owner": owner,
            "scope": scope,
            "current_location": "Mac Mini user LaunchAgent",
            "trigger": trigger,
            "entrypoint": entrypoint,
            "state": state,
            "migration_target": migration_target,
            "evidence": public_path(path),
        }


def cron_trigger(schedule: Any) -> str:
    if not isinstance(schedule, dict):
        return "unknown"
    kind = compact(schedule.get("kind", "unknown"))
    if kind == "cron":
        return f"cron:{compact(schedule.get('expr', 'unknown'))}@{compact(schedule.get('tz', 'default'))}"
    if kind == "every":
        return f"every:{compact(schedule.get('everyMs', schedule.get('intervalMs', 'unknown')))}ms"
    if kind == "at":
        return f"at:{compact(schedule.get('at', 'unknown'))}"
    return kind


def openclaw_rows() -> Iterable[dict[str, str]]:
    with OPENCLAW_JOBS.open(encoding="utf-8") as handle:
        document = json.load(handle)
    for job in document.get("jobs", []):
        job_id = compact(job.get("id") or "missing-id")
        name = compact(job.get("name") or job_id)
        agent_id = compact(job.get("agentId") or "anicca")
        enabled = bool(job.get("enabled", False))
        payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
        payload_kind = compact(payload.get("kind") or "unknown")
        scope = scope_for(name)
        state = "enabled" if enabled else "disabled"
        yield {
            "inventory_id": f"openclaw:{job_id}",
            "source_type": "openclaw_cron",
            "owner": f"Anicca OpenClaw / agent:{agent_id}",
            "scope": scope,
            "current_location": "Mac Mini OpenClaw gateway",
            "trigger": cron_trigger(job.get("schedule")),
            "entrypoint": f"openclaw_gateway:{payload_kind}:agent={agent_id}",
            "state": state,
            "migration_target": target_for(scope, enabled=enabled),
            "evidence": f"{public_path(OPENCLAW_JOBS)}#job={job_id}",
        }


def discover_package_manifests(repo: Path) -> list[Path]:
    """Discover only first-party app manifests; never traverse vendored trees."""
    manifests: set[Path] = set()
    for parent in ("apps", "web-apps"):
        manifests.update((repo / parent).glob("*/package.json"))
    return sorted(path for path in manifests if path.is_file())


def owner_for_manifest(relative: Path) -> str:
    owners = {
        "apps/api/package.json": "Anicca API",
        "apps/landing/package.json": "Anicca landing",
        "apps/x402-agents/package.json": "x402 agents",
        "web-apps/daily-dhamma-app/package.json": "Daily Dhamma app",
    }
    return owners.get(relative.as_posix(), f"First-party app / {relative.parent.name}")


def package_entrypoint_rows() -> Iterable[dict[str, str]]:
    for manifest in discover_package_manifests(REPO):
        relative = manifest.relative_to(REPO)
        with manifest.open(encoding="utf-8") as handle:
            data = json.load(handle)
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        for script_name in ("start", "worker"):
            if script_name not in scripts:
                continue
            # package scripts are repository code, not user data. Keep only start/worker.
            entrypoint = compact(scripts[script_name])
            yield {
                "inventory_id": f"package:{manifest.relative_to(REPO)}#{script_name}",
                "source_type": "repository_entrypoint",
                "owner": owner_for_manifest(relative),
                "scope": "product_runtime_candidate",
                "current_location": "repository declaration; deployment target requires runtime evidence",
                "trigger": f"npm run {script_name}",
                "entrypoint": entrypoint,
                "state": "declared_in_repository;runtime_not_verified_here",
                "migration_target": "Life_Manager_control_plane_or_workload_worker",
                "evidence": relative.as_posix(),
            }

    # Production Life Manager lives on main while this inventory branch diverges.
    yield {
        "inventory_id": "railway:life-call-main",
        "source_type": "railway_entrypoint",
        "owner": "Life Manager / anicca-products",
        "scope": "product_runtime_candidate",
        "current_location": "Railway production",
        "trigger": "npm start; HTTP/Inngest; optional 60s in-process loops",
        "entrypoint": "apps/life-call/package.json#start -> node server.js",
        "state": "present_on_origin_main;deployment_health_not_part_of_TODO_1",
        "migration_target": "Railway_API_plus_Inngest_control_plane",
        "evidence": "https://github.com/Daisuke134/anicca-products/blob/main/apps/life-call/package.json",
    }


def run_self_tests() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        safe_script = root / "safe.sh"
        safe_script.write_text("#!/bin/sh\n", encoding="utf-8")
        metachar_script = root / "unsafe;name.sh"
        metachar_script.write_text("#!/bin/sh\n", encoding="utf-8")
        missing_script = root / "declared-missing.sh"

        shell_fixture = {
            "ProgramArguments": [
                "/bin/zsh",
                "-lc",
                f"{safe_script} && PRIVATE_BODY_MUST_NOT_APPEAR",
            ]
        }
        shell_result = safe_launchd_entrypoint(shell_fixture)
        assert shell_result == "/bin/zsh <shell-command-redacted>"
        assert "PRIVATE_BODY_MUST_NOT_APPEAR" not in shell_result
        assert safe_path_token(str(metachar_script)) is None
        assert safe_launchd_entrypoint(
            {"ProgramArguments": ["/bin/bash", str(safe_script)]}
        ) == f"/bin/bash {public_path(safe_script)}"
        assert safe_path_token(str(missing_script)) == public_path(missing_script)
        missing_fixture = {"ProgramArguments": ["/bin/bash", str(missing_script)]}
        assert safe_launchd_entrypoint(missing_fixture) == (
            f"/bin/bash {public_path(missing_script)}"
        )
        assert state_with_declared_entrypoint(
            "loaded", declared_script_path(missing_fixture)
        ) == "loaded;declared_entrypoint_missing"

        owner, scope, target = launchd_classification(
            "ai.anicca.fixture", "unparsed_plist_entrypoint", "parse_error:Fixture", False
        )
        assert (owner, scope, target) == (
            "unverified",
            "needs_scope_review",
            "classify_before_migration",
        )

        app_manifest = root / "apps" / "landing" / "package.json"
        web_manifest = root / "web-apps" / "daily" / "package.json"
        nested_vendor = root / "apps" / "landing" / "vendor" / "package.json"
        for path in (app_manifest, web_manifest, nested_vendor):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"scripts":{"start":"node server.js"}}\n', encoding="utf-8")
        discovered = [path.relative_to(root).as_posix() for path in discover_package_manifests(root)]
        assert discovered == [
            "apps/landing/package.json",
            "web-apps/daily/package.json",
        ]


def rows() -> list[dict[str, str]]:
    result = [*launchd_rows(), *openclaw_rows(), *package_entrypoint_rows()]
    return sorted(result, key=lambda row: (row["source_type"], row["inventory_id"]))


def validate(result: list[dict[str, str]]) -> None:
    ids = [row["inventory_id"] for row in result]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate inventory_id detected")
    for row in result:
        missing = [field for field in FIELDS if not compact(row.get(field, ""))]
        if missing:
            raise SystemExit(f"{row.get('inventory_id')}: empty fields: {','.join(missing)}")
        joined = "\t".join(row.values())
        if str(HOME) in joined:
            raise SystemExit(f"{row['inventory_id']}: unnormalized user home path")
        if re.search(r"(?i)(token|cookie|password|secret)=", joined):
            raise SystemExit(f"{row['inventory_id']}: possible secret-like assignment")
    expected_package_ids: set[str] = set()
    for manifest in discover_package_manifests(REPO):
        with manifest.open(encoding="utf-8") as handle:
            scripts = json.load(handle).get("scripts", {})
        for name in ("start", "worker"):
            if isinstance(scripts, dict) and name in scripts:
                expected_package_ids.add(f"package:{manifest.relative_to(REPO)}#{name}")
    actual_package_ids = {
        row["inventory_id"] for row in result if row["source_type"] == "repository_entrypoint"
    }
    if actual_package_ids != expected_package_ids:
        raise SystemExit("repository entrypoint discovery mismatch")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate and print counts to stderr")
    parser.add_argument("--self-test", action="store_true", help="run regression fixtures")
    args = parser.parse_args()
    if args.check or args.self_test:
        run_self_tests()
    if args.self_test and not args.check:
        print("self-tests: PASS", file=sys.stderr)
        return
    result = rows()
    validate(result)
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(result)
    if args.check:
        counts: dict[str, int] = {}
        for row in result:
            counts[row["source_type"]] = counts.get(row["source_type"], 0) + 1
        print(json.dumps({"rows": len(result), "by_source": counts}, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    main()
