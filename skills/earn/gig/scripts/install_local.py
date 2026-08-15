#!/usr/bin/env python3
"""Install the canonical local Gig runtime without copying private state."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


GIG_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = GIG_DIR.parents[2]
TEMPLATE_DIR = GIG_DIR / "launchd"
LOGIN_URL = "https://coconala.com/login"
REVENUE_LABELS = (
    "ai.anicca.hf-gig-storefront-direct",
    "ai.anicca.hf-gig-apply-direct",
    "ai.anicca.hf-gig-reply-detector",
    "ai.anicca.hf-gig-paid-direct",
)
BROWSER_LABEL = "ai.anicca.hf-gig-browser"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument(
        "command", nargs="?", choices=("install", "setup", "doctor", "start"),
        default="install",
    )
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
    value.add_argument("--work-profile", default="")
    value.add_argument("--marketplace-profile", default="")
    value.add_argument("--report-chat", default="")
    value.add_argument(
        "--auth-state", default="",
        help=argparse.SUPPRESS,
    )
    value.add_argument(
        "--openclaw", default="/opt/homebrew/bin/openclaw",
        help=argparse.SUPPRESS,
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
        if "__REPO_ROOT__" in encoded:
            raise SystemExit(f"unresolved repository marker: {template}")
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
        if os.environ.get("ANICCA_JOB_PROFILE"):
            environment["ANICCA_JOB_PROFILE"] = os.environ["ANICCA_JOB_PROFILE"]
        if os.environ.get("GIG_MARKETPLACE_PROFILE"):
            environment["CDP_DAILY_DRIVER_PROFILE"] = os.environ["GIG_MARKETPLACE_PROFILE"]
        units.append(value)
    return units


def onboarding_path(runtime: Path) -> Path:
    return runtime / "state" / "gig-onboarding.json"


def read_onboarding(runtime: Path) -> dict[str, Any]:
    try:
        value = json.loads(onboarding_path(runtime).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit("run install-local.sh setup first") from error
    if not isinstance(value, dict):
        raise SystemExit("invalid onboarding receipt")
    return value


def apply_onboarding(value: dict[str, Any]) -> None:
    os.environ["ANICCA_JOB_PROFILE"] = str(value["work_profile"])
    os.environ["GIG_MARKETPLACE_PROFILE"] = str(value["marketplace_profile"])
    os.environ["GIG_REPORT_CHAT"] = str(value["report_chat"])


def doctor(runtime: Path) -> dict[str, Any]:
    value = read_onboarding(runtime)
    checks: dict[str, bool] = {}
    try:
        profile = json.loads(Path(value["work_profile"]).read_text(encoding="utf-8"))
        checks["work_profile"] = isinstance(profile, dict) and bool(profile)
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        checks["work_profile"] = False
    checks["marketplace_profile"] = Path(
        str(value.get("marketplace_profile", ""))
    ).is_dir()
    try:
        auth = json.loads(Path(value["auth_state"]).read_text(encoding="utf-8"))
        checks["official_login"] = isinstance(auth, dict) and bool(auth)
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        checks["official_login"] = False
    checks["report_destination"] = bool(str(value.get("report_chat", "")).strip())
    try:
        receipt = json.loads(
            (runtime / "state" / "gig-install.json").read_text(encoding="utf-8")
        )
        checks["four_owners_rendered"] = all(
            label in receipt.get("units", []) for label in REVENUE_LABELS
        )
    except (OSError, json.JSONDecodeError, TypeError):
        checks["four_owners_rendered"] = False
    return {
        "status": "ok" if all(checks.values()) else "login_required",
        "effect": 0,
        "checks": checks,
        "login_url": LOGIN_URL,
    }


def send_daily_report(state_dir: Path, target: str, openclaw: str) -> str:
    command = [
        sys.executable, str(GIG_DIR / "scripts" / "telegram_report.py"), "daily",
        "--gig-dir", str(state_dir),
        "--telegram-database", str(state_dir / "telegram-outbox.sqlite3"),
        "--connector-database", str(state_dir / "connector-outbox.sqlite3"),
        "--target", target, "--openclaw", openclaw,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode:
        raise SystemExit(f"Telegram daily report failed: {completed.stderr.strip()}")
    with sqlite3.connect(state_dir / "telegram-outbox.sqlite3") as connection:
        row = connection.execute(
            "SELECT message_id FROM telegram_reports "
            "WHERE kind='daily' AND state='sent' ORDER BY report_id DESC LIMIT 1"
        ).fetchone()
    if not row or not row[0]:
        raise SystemExit("Telegram daily report has no provider receipt")
    return str(row[0])


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
            command = ["launchctl", "bootstrap", domain, str(output)]
            for attempt in range(5):
                completed = subprocess.run(command, check=False)
                if completed.returncode == 0:
                    break
                if attempt == 4:
                    completed.check_returncode()
                time.sleep(0.25)
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

    if arguments.command in {"doctor", "start"}:
        onboarding = read_onboarding(runtime)
        apply_onboarding(onboarding)
        diagnosis = doctor(runtime)
        if arguments.command == "doctor" or diagnosis["status"] != "ok":
            print(json.dumps(diagnosis, ensure_ascii=False, sort_keys=True))
            return 0 if diagnosis["status"] == "ok" else 2

    state_dir, adopted = select_state_dir(home, runtime)
    state_dir.mkdir(parents=True, exist_ok=True)
    (runtime / "logs").mkdir(parents=True, exist_ok=True)
    (runtime / "state").mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    os.chmod(runtime / "logs", 0o700)

    if arguments.command == "setup":
        missing = [
            flag for flag, value in (
                ("--work-profile", arguments.work_profile),
                ("--marketplace-profile", arguments.marketplace_profile),
                ("--report-chat", arguments.report_chat),
            ) if not str(value).strip()
        ]
        if missing:
            raise SystemExit("setup requires " + ", ".join(missing))
        onboarding = {
            "version": 1,
            "work_profile": str(Path(arguments.work_profile).expanduser().resolve()),
            "marketplace_profile": str(
                Path(arguments.marketplace_profile).expanduser().resolve()
            ),
            "auth_state": str(Path(
                arguments.auth_state
                or home / ".cloak/vault/gig-daily-driver/auth-state.json"
            ).expanduser().resolve()),
            "report_chat": str(arguments.report_chat).strip(),
            "openclaw": str(Path(arguments.openclaw).expanduser()),
        }
        apply_onboarding(onboarding)
        atomic_write(
            onboarding_path(runtime),
            (json.dumps(onboarding, ensure_ascii=False, sort_keys=True) + "\n").encode(),
            0o600,
        )

    units = load_templates(home, runtime, state_dir)
    if arguments.command == "start":
        selected = [
            value for value in units
            if value.get("Label") in {BROWSER_LABEL, *REVENUE_LABELS}
        ]
        if scheduler == "launchd":
            labels = render_launchd(selected, home, True)
        elif scheduler == "systemd":
            labels = render_systemd(selected, home, True)
        else:
            raise SystemExit("start requires launchd or systemd")
        message_id = send_daily_report(
            state_dir, str(onboarding["report_chat"]), str(onboarding["openclaw"])
        )
        print(json.dumps({
            "status": "started", "owners": list(REVENUE_LABELS),
            "browser_owner": BROWSER_LABEL, "telegram_message_id": message_id,
        }, ensure_ascii=False, sort_keys=True))
        return 0

    enable = not arguments.no_enable and arguments.command == "install"
    if scheduler == "launchd":
        labels = render_launchd(units, home, enable)
    elif scheduler == "systemd":
        labels = render_systemd(units, home, enable)
    else:
        labels = []

    receipt = {
        "version": 1,
        "repo_root": str(REPO_ROOT),
        "runtime_home": str(runtime),
        "state_dir": str(state_dir),
        "adopted_legacy_state": adopted,
        "scheduler": scheduler,
        "enabled": enable and scheduler != "none",
        "units": labels,
    }
    atomic_write(
        runtime / "state" / "gig-install.json",
        (json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n").encode(),
        0o600,
    )
    if arguments.command == "setup":
        receipt.update({
            "status": "login_required",
            "login_url": LOGIN_URL,
            "next_command": "skills/earn/gig/install-local.sh doctor",
        })
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
