#!/usr/bin/env python3
"""Record secret-free, read-only host evidence once per macOS boot."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPORT_ROOT = Path("/Library/Logs/DiagnosticReports")
BROWSER = re.compile(r"(?i)(?:Google Chrome|Chromium|Cloak|Brave Browser|Microsoft Edge)")


def _run(*command: str) -> str:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True,
                              timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _boot_time() -> tuple[int | None, str | None]:
    match = re.search(r"sec\s*=\s*(\d+)", _run("sysctl", "kern.boottime"))
    if not match:
        return None, None
    epoch = int(match.group(1))
    return epoch, datetime.fromtimestamp(epoch).astimezone().isoformat()


def _orderly_shutdown_before(boot_epoch: int | None) -> bool | None:
    if boot_epoch is None:
        return None
    year = datetime.fromtimestamp(boot_epoch).year
    for line in _run("last", "shutdown").splitlines():
        match = re.search(r"shutdown time\s+(?:\S+\s+)?([A-Z][a-z]{2}\s+\d+\s+\d\d:\d\d)", line)
        if not match:
            continue
        try:
            stamp = datetime.strptime(f"{match.group(1)} {year}", "%b %d %H:%M %Y")
            shutdown_epoch = stamp.replace(tzinfo=datetime.now().astimezone().tzinfo).timestamp()
        except ValueError:
            continue
        if 0 <= boot_epoch - shutdown_epoch <= 30 * 60:
            return True
    return False


def _report_names(pattern: str, limit: int = 20) -> list[str]:
    try:
        paths = sorted(REPORT_ROOT.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    except OSError:
        return []
    return [path.name for path in paths[:limit]]


def _latest_panic_text(names: list[str]) -> str:
    if not names:
        return ""
    try:
        with (REPORT_ROOT / names[0]).open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(8 * 1024 * 1024)
    except OSError:
        return ""


def _report_mentions(names: list[str]) -> dict[str, bool]:
    found = {name: False for name in ("WindowServer", "tccd", "sandboxd")}
    for report_name in names:
        try:
            with (REPORT_ROOT / report_name).open("r", encoding="utf-8", errors="replace") as handle:
                text = handle.read(16 * 1024 * 1024).lower()
        except OSError:
            continue
        for name in found:
            found[name] = found[name] or name.lower() in text
    return found


def _memory() -> dict[str, int | None]:
    vm = _run("vm_stat")
    page_match = re.search(r"page size of (\d+) bytes", vm)
    values = {}
    for key, label in (("pages_free", "Pages free"),
                       ("pages_compressed", "Pages stored in compressor"),
                       ("compressor_pages_occupied", "Pages occupied by compressor")):
        match = re.search(rf"^{re.escape(label)}:\s+(\d+)\.", vm, re.MULTILINE)
        values[key] = int(match.group(1)) if match else None
    swap = _run("sysctl", "-n", "vm.swapusage")
    match = re.search(r"used\s*=\s*([0-9.]+)([MGT])", swap)
    factor = {"M": 1024**2, "G": 1024**3, "T": 1024**4}
    values["page_size_bytes"] = int(page_match.group(1)) if page_match else None
    values["swap_used_bytes"] = int(float(match.group(1)) * factor[match.group(2)]) if match else None
    return values


def _browser_counts() -> dict[str, int]:
    commands = [line for line in _run("ps", "-axo", "comm=").splitlines() if BROWSER.search(line)]
    renderers = sum("Renderer" in line for line in commands)
    endpoints: set[tuple[int, int]] = set()
    for line in _run("lsof", "-nP", "-iTCP", "-sTCP:LISTEN").splitlines()[1:]:
        fields = line.split()
        if len(fields) < 9 or not BROWSER.search(fields[0]):
            continue
        match = re.search(r"(?:127\.0\.0\.1|\[::1\]):(\d+)", fields[-2])
        if match and fields[1].isdigit():
            endpoints.add((int(fields[1]), int(match.group(1))))
    tab_count = 0
    valid_endpoints = 0
    owners: set[int] = set()
    for pid, port in endpoints:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=0.2) as response:
                payload = json.load(response)
            if isinstance(payload, list):
                valid_endpoints += 1
                owners.add(pid)
                tab_count += len(payload)
        except Exception:
            continue
    return {"owner_count": len(owners), "process_count": len(commands),
            "renderer_count": renderers, "debug_endpoint_count": valid_endpoints,
            "tab_count": tab_count}


def classify_component_boundary(panic_text: str) -> str:
    lower = panic_text.lower()
    if "userspace watchdog" in lower and "windowserver" in lower:
        return "WindowServer"
    if panic_text:
        return "kernel_or_hardware"
    return "no_panic_evidence"


def build_receipt(raw: dict, *, collected_at: str | None = None) -> dict:
    return {
        "version": 1,
        "collected_at": collected_at or datetime.now(timezone.utc).isoformat(),
        "boot": {"id": raw["boot_session_uuid"], "time": raw["boot_time"],
                 "prior_orderly_shutdown": raw["orderly_shutdown_before_boot"]},
        "component_boundary": classify_component_boundary(raw.get("panic_text", "")),
        "panic_reports": raw["panic_reports"],
        "reset_reports": raw["reset_reports"],
        "watchdog_evidence": {
            name: {
                "report_names": raw["watchdog_reports"][name],
                "mentioned_in_reports": raw.get("watchdog_mentions", {}).get(
                    name, name.lower() in raw.get("panic_text", "").lower()
                ),
            }
            for name in ("WindowServer", "tccd", "sandboxd")
        },
        "memory": raw["memory"],
        "disk": raw["disk"],
        "browser": raw["browser"],
    }


def write_receipt(state_root: Path, receipt: dict) -> Path:
    safe_boot_id = re.sub(r"[^A-Za-z0-9._-]", "_", receipt["boot"]["id"])
    target = state_root / "boots" / safe_boot_id / "summary.json"
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.parent.chmod(0o700)
    fd, name = tempfile.mkstemp(prefix=".summary.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(receipt, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o600)
        os.replace(name, target)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
    return target


def collect() -> dict:
    boot_epoch, boot_time = _boot_time()
    panic_reports = _report_names("panic-full-*.panic") + _report_names("*.panic")
    panic_reports = list(dict.fromkeys(panic_reports))[:20]
    reset_reports = _report_names("ResetCounter-*.diag") + _report_names("forceReset-*.diag")
    watchdog = {
        name: _report_names(f"{name}_*watchdog*") + _report_names(f"{name}_*.spin")
        for name in ("WindowServer", "tccd", "sandboxd")
    }
    watchdog_names = [name for values in watchdog.values() for name in values]
    return build_receipt({
        "boot_session_uuid": _run("sysctl", "-n", "kern.bootsessionuuid").strip() or "unknown",
        "boot_time": boot_time,
        "orderly_shutdown_before_boot": _orderly_shutdown_before(boot_epoch),
        "panic_reports": panic_reports,
        "reset_reports": list(dict.fromkeys(reset_reports))[:20],
        "watchdog_reports": {key: list(dict.fromkeys(value))[:20] for key, value in watchdog.items()},
        "watchdog_mentions": _report_mentions(panic_reports + watchdog_names),
        "panic_text": _latest_panic_text(panic_reports),
        "memory": _memory(),
        "disk": {"root_free_bytes": shutil.disk_usage("/").free},
        "browser": _browser_counts(),
    })


def main() -> int:
    state_root = Path(os.environ.get(
        "LIFE_MANAGER_STATE_ROOT", "~/.local/state/life-manager/boot-panic-evidence"
    )).expanduser()
    target = write_receipt(state_root, collect())
    print(json.dumps({"ok": True, "receipt": f"state://boot-panic-evidence/{target.parent.name}/summary.json"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
