#!/usr/bin/env python3
"""Install the canonical local Gig runtime without copying private state."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


GIG_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = GIG_DIR.parents[2]
TEMPLATE_DIR = GIG_DIR / "launchd"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument(
        "--scheduler",
        choices=("auto", "launchd", "systemd", "none"),
        default="auto",
    )
    value.add_argument(
        "--no-enable",
        action="store_true",
        help="render units without loading or enabling them",
    )
    return value


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def select_state_dir(home: Path, runtime: Path) -> tuple[Path, bool]:
    configured = os.environ.get("GIG_STATE_DIR")
    if configured:
        return Path(configured).expanduser().resolve(), False

    legacy = home / "gig"
    if legacy.exists():
        if not legacy.is_dir():
            raise SystemExit(f"legacy Gig state is not a directory: {legacy}")
        return legacy.resolve(), True
    return (runtime / "state" / "gig").resolve(), False


def replace_markers(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        for marker, replacement in replacements.items():
            value = value.replace(marker, replacement)
        return value
    if isinstance(value, list):
        return [replace_markers(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: replace_markers(item, replacements)
            for key, item in value.items()
        }
    return value


def load_templates(
    home: Path, runtime: Path, state_dir: Path
) -> list[dict[str, Any]]:
    python3 = shutil.which("python3") or sys.executable
    replacements = {
        "__LIFE_MANAGER_REPO__": str(REPO_ROOT),
        "__LIFE_MANAGER_HOME__": str(runtime),
        "__GIG_STATE_DIR__": str(state_dir),
        "__HOME__": str(home),
        "/opt/homebrew/bin/python3": python3,
    }
    units: list[dict[str, Any]] = []
    for template in sorted(TEMPLATE_DIR.glob("*.plist")):
        value = replace_markers(
            plistlib.loads(template.read_bytes()), replacements
        )
        encoded = json.dumps(value, ensure_ascii=False)
        if "__LIFE_MANAGER_" in encoded or "__HOME__" in encoded:
            raise SystemExit(f"unresolved template marker: {template}")
        if "__GIG_STATE_DIR__" in encoded:
            raise SystemExit(f"unresolved Gig state marker: {template}")
        environment = value.setdefault("EnvironmentVariables", {})
        environment.update(
            {
                "LIFE_MANAGER_REPO": str(REPO_ROOT),
                "LIFE_MANAGER_HOME": str(runtime),
                "GIG_STATE_DIR": str(state_dir),
                "GIG_ENV_FILE": str(runtime / ".env"),
            }
        )
        # User-specific report routing belongs to the rendered private unit,
        # never the public template or install receipt.
        if os.environ.get("GIG_REPORT_CHAT"):
            environment["GIG_REPORT_CHAT"] = os.environ["GIG_REPORT_CHAT"]
        units.append(value)
    return units


def render_launchd(
    units: list[dict[str, Any]], home: Path, enable: bool
) -> list[str]:
    target = Path(
        os.environ.get(
            "GIG_LAUNCH_AGENT_DIR", home / "Library" / "LaunchAgents"
        )
    )
    labels: list[str] = []
    for value in units:
        label = value["Label"]
        labels.append(label)
        output = target / f"{label}.plist"
        atomic_write(
            output,
            plistlib.dumps(value, sort_keys=False),
            0o644,
        )
        if enable:
            domain = f"gui/{os.getuid()}"
            subprocess.run(
                ["launchctl", "bootout", f"{domain}/{label}"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["launchctl", "bootstrap", domain, str(output)],
                check=True,
            )
    return labels


def systemd_quote(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def calendar_expression(value: dict[str, Any]) -> str:
    minute = int(value.get("Minute", 0))
    hour = value.get("Hour")
    weekday = value.get("Weekday")
    if weekday is not None:
        # launchd numbers weekdays Sunday=1 through Saturday=7.
        names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        name = names[(int(weekday) - 1) % 7]
        return f"{name} *-*-* {int(hour or 0):02d}:{minute:02d}:00"
    if hour is not None:
        return f"*-*-* {int(hour):02d}:{minute:02d}:00"
    return f"*-*-* *:{minute:02d}:00"


def timer_for(value: dict[str, Any]) -> str | None:
    interval = value.get("StartInterval")
    if interval:
        return "\n".join(
            (
                "[Unit]",
                f"Description=Schedule for {value['Label']}",
                "",
                "[Timer]",
                "OnBootSec=60",
                f"OnUnitActiveSec={int(interval)}",
                "Persistent=true",
                "",
                "[Install]",
                "WantedBy=timers.target",
                "",
            )
        )
    calendar = value.get("StartCalendarInterval")
    if calendar:
        entries = calendar if isinstance(calendar, list) else [calendar]
        lines = [
            "[Unit]",
            f"Description=Schedule for {value['Label']}",
            "",
            "[Timer]",
        ]
        lines.extend(
            f"OnCalendar={calendar_expression(entry)}" for entry in entries
        )
        lines.extend(
            ("Persistent=true", "", "[Install]", "WantedBy=timers.target", "")
        )
        return "\n".join(lines)
    return None


def service_for(value: dict[str, Any], home: Path) -> str:
    environment = value.get("EnvironmentVariables", {})
    arguments = [str(item) for item in value["ProgramArguments"]]
    working_directory = str(value.get("WorkingDirectory", home))
    keep_alive = bool(value.get("KeepAlive"))
    lines = [
        "[Unit]",
        f"Description={value['Label']}",
        "After=network-online.target",
        "",
        "[Service]",
        f"Type={'simple' if keep_alive else 'oneshot'}",
        f"WorkingDirectory={systemd_quote(working_directory)}",
    ]
    for key in sorted(environment):
        lines.append(
            f"Environment={systemd_quote(f'{key}={environment[key]}')}"
        )
    lines.append(f"ExecStart={shlex.join(arguments)}")
    if keep_alive:
        lines.extend(("Restart=always", "RestartSec=5"))
    lines.extend(("", "[Install]", "WantedBy=default.target", ""))
    return "\n".join(lines)


def render_systemd(
    units: list[dict[str, Any]], home: Path, enable: bool
) -> list[str]:
    target = Path(
        os.environ.get(
            "GIG_SYSTEMD_USER_DIR",
            Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
            / "systemd"
            / "user",
        )
    )
    labels: list[str] = []
    scheduled: list[str] = []
    resident: list[str] = []
    for value in units:
        label = value["Label"]
        labels.append(label)
        atomic_write(
            target / f"{label}.service",
            service_for(value, home).encode(),
            0o600,
        )
        timer = timer_for(value)
        if timer is not None:
            atomic_write(
                target / f"{label}.timer",
                timer.encode(),
                0o600,
            )
            scheduled.append(f"{label}.timer")
        elif value.get("KeepAlive") or value.get("RunAtLoad"):
            resident.append(f"{label}.service")

    if enable:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        if scheduled or resident:
            subprocess.run(
                ["systemctl", "--user", "enable", "--now", *scheduled, *resident],
                check=True,
            )
    return labels


def main() -> int:
    arguments = parser().parse_args()
    home = Path(os.environ["HOME"]).expanduser().resolve()
    runtime = Path(
        os.environ.get(
            "LIFE_MANAGER_HOME",
            os.environ.get(
                "ANICCA_HOME",
                Path(os.environ.get("XDG_STATE_HOME", home / ".local/state"))
                / "life-manager",
            ),
        )
    ).expanduser().resolve()
    scheduler = arguments.scheduler
    if scheduler == "auto":
        scheduler = "launchd" if sys.platform == "darwin" else "systemd"

    state_dir, adopted = select_state_dir(home, runtime)
    state_dir.mkdir(parents=True, exist_ok=True)
    (runtime / "logs").mkdir(parents=True, exist_ok=True)
    (runtime / "state").mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    os.chmod(runtime / "logs", 0o700)

    units = load_templates(home, runtime, state_dir)
    if scheduler == "launchd":
        labels = render_launchd(units, home, not arguments.no_enable)
    elif scheduler == "systemd":
        labels = render_systemd(units, home, not arguments.no_enable)
    else:
        labels = []

    receipt = {
        "version": 1,
        "repo_root": str(REPO_ROOT),
        "runtime_home": str(runtime),
        "state_dir": str(state_dir),
        "adopted_legacy_state": adopted,
        "scheduler": scheduler,
        "enabled": not arguments.no_enable and scheduler != "none",
        "units": labels,
    }
    atomic_write(
        runtime / "state" / "gig-install.json",
        (json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n").encode(),
        0o600,
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
