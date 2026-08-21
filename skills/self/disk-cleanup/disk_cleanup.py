#!/usr/bin/env python3
"""Fail-closed, host-wide disk governor for Life Manager.

The governor only removes explicitly classified, closed, regenerable artifacts.
Unknown paths, sessions, state, credentials, source, and probe failures remain.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

from host_inventory import FULL_INVENTORY_BUDGET_SECONDS, collect_host_inventory

GiB = 1024**3
FULL_INVENTORY_INTERVAL_SECONDS = 3600
GOVERNOR_BUDGET_SECONDS = 90
LSOF_TIMEOUT_SECONDS = 15
POST_SWEEP_RESERVE_SECONDS = 30
THRESHOLDS = ((20 * GiB, "NORMAL"), (11 * GiB, "PREVENTIVE"), (6 * GiB, "PRESSURE"), (3 * GiB, "CRITICAL"))


def classify_tier(free_bytes: int) -> str:
    for floor, tier in THRESHOLDS:
        if free_bytes >= floor:
            return tier
    return "ULTRA"


def _bytes(
    path: Path,
    *,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> int | None:
    if deadline is not None and clock() >= deadline:
        return None
    if not path.exists() and not path.is_symlink():
        return 0
    if path.is_file() or path.is_symlink():
        return path.stat().st_size
    total = 0
    for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
        if deadline is not None and clock() >= deadline:
            return None
        dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
        for name in files:
            item = Path(root) / name
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _default_lsof(path: Path) -> str:
    try:
        result = subprocess.run(
            ["/usr/sbin/lsof", "-nP", "+D", str(path)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "probe-error"
    if result.stdout.strip():
        return "open"
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return "confirmed-closed"
    return "probe-error"


class HostDiskGovernor:
    def __init__(
        self,
        *,
        home: Path | None = None,
        state_dir: Path | None = None,
        lsof: Callable[[Path], str] = _default_lsof,
        usage: Callable[[], tuple[int, int]] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.home = (home or Path.home()).resolve()
        self.state_dir = (state_dir or self.home / ".openclaw/state").resolve()
        self.lock_dir = self.state_dir / ".life-manager-disk-cleanup.lock"
        self.full_inventory_marker = self.state_dir / "host-inventory-full.at"
        self.lsof = lsof
        self.usage = usage or self._usage
        self.clock = clock

    def _full_inventory_due(self) -> bool:
        try:
            last = int(self.full_inventory_marker.read_text().strip())
        except (FileNotFoundError, OSError, ValueError):
            return True
        return int(time.time()) - last >= FULL_INVENTORY_INTERVAL_SECONDS

    def _mark_full_inventory(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.full_inventory_marker.with_name(f".{self.full_inventory_marker.name}.tmp")
        temporary.write_text(str(int(time.time())) + "\n")
        os.replace(temporary, self.full_inventory_marker)

    def _usage(self) -> tuple[int, int]:
        usage = shutil.disk_usage("/System/Volumes/Data" if Path("/System/Volumes/Data").exists() else "/")
        return usage.free, usage.total

    def acquire_lock(self) -> bool:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.lock_dir.mkdir()
        except FileExistsError:
            pid_file = self.lock_dir / "pid"
            try:
                pid = int(pid_file.read_text())
                os.kill(pid, 0)
                return False
            except (OSError, ValueError):
                shutil.rmtree(self.lock_dir, ignore_errors=True)
                try:
                    self.lock_dir.mkdir()
                except FileExistsError:
                    return False
        (self.lock_dir / "pid").write_text(str(os.getpid()))
        return True

    def release_lock(self) -> None:
        shutil.rmtree(self.lock_dir, ignore_errors=True)

    def _protected(self, path: Path) -> bool:
        try:
            relative = path.resolve().relative_to(self.home)
        except ValueError:
            relative = Path("/") / path.resolve().relative_to(path.anchor).as_posix()
        parts = relative.parts
        protected_roots = {
            ".claude", ".codex", ".config/ai", ".openclaw/state", ".openclaw/identity",
            ".openclaw/workspace", ".cloak", "anicca-rtdash", "anicca-monk-factory",
        }
        text = "/".join(parts)
        if any(text == root or text.startswith(root + "/") for root in protected_roots):
            return True
        if ".git" in parts or path.suffix in {".sqlite", ".db"}:
            return True
        if len(parts) >= 2 and parts[-2] == "state" and path.suffix == ".jsonl":
            return True
        return any(token in path.name.lower() for token in ("cookie", "login data", "auth.json"))

    def _allowlisted_candidate(self, path: Path, item: dict) -> bool:
        """Require discovery proof and an exact regenerable path family."""
        if item.get("discovery") != "allowlisted":
            return False
        try:
            resolved = path.resolve()
            temporary = Path(tempfile.gettempdir()).resolve()
        except OSError:
            return False
        if item.get("class") == "ephemeral" and item.get("owner") == "temporary-run":
            return (
                resolved.parent == temporary
                and resolved.name.startswith("cfo-")
                and resolved.name != "cfo-"
            )
        if item.get("class") == "regenerable_output" and item.get("owner") == "browser":
            clone_root = temporary.parent / "X"
            return (
                resolved.parent.parent == clone_root
                and resolved.parent.name
                in {"com.google.Chrome.code_sign_clone", "org.chromium.Chromium.code_sign_clone"}
                and resolved.name.startswith("code_sign_clone.")
            )
        return False

    def _receipt(self, payload: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload.setdefault("observed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        temporary = self.state_dir / ".last-receipt.tmp"
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(temporary, self.state_dir / "last-receipt.json")

    def sweep(
        self,
        candidates: list[dict],
        *,
        write_receipt: bool = True,
        deadline: float | None = None,
    ) -> dict[str, int | str]:
        free_before, _ = self.usage()
        result: dict[str, int | str] = {
            "tier": classify_tier(free_before),
            "evaluated": len(candidates),
            "reclaimed": 0,
            "preserved": 0,
            "errors": 0,
            "protected_deletions": 0,
        }
        reasons: dict[str, int] = {}

        def preserve(reason: str) -> None:
            result["preserved"] += 1
            reasons[reason] = reasons.get(reason, 0) + 1

        for item in candidates:
            path = Path(item["path"]).expanduser()
            if deadline is not None and self.clock() >= deadline:
                preserve("probe-budget-exhausted")
                continue
            if self._protected(path):
                preserve("protected_path")
                continue
            if item.get("class") not in {"ephemeral", "regenerable_output"}:
                preserve("unknown_class")
                continue
            if not self._allowlisted_candidate(path, item):
                preserve("unknown_artifact")
                continue
            if item.get("lease") and Path(item["lease"]).exists():
                preserve("active_lease")
                continue
            if not path.exists() or path.is_symlink():
                preserve("path_missing_or_symlink")
                continue
            if deadline is not None and self.clock() + LSOF_TIMEOUT_SECONDS + POST_SWEEP_RESERVE_SECONDS >= deadline:
                preserve("probe-budget-exhausted")
                continue
            state = self.lsof(path)
            if deadline is not None and self.clock() >= deadline:
                preserve("probe-budget-exhausted")
                continue
            if state != "confirmed-closed":
                result["errors"] += state == "probe-error"
                preserve(state)
                continue
            if deadline is not None and self.clock() >= deadline:
                preserve("probe-budget-exhausted")
                continue
            if deadline is not None and self.clock() + POST_SWEEP_RESERVE_SECONDS >= deadline:
                preserve("probe-budget-exhausted")
                continue
            before = _bytes(path, deadline=deadline, clock=self.clock)
            if before is None:
                preserve("probe-budget-exhausted")
                continue
            if deadline is not None and self.clock() + POST_SWEEP_RESERVE_SECONDS >= deadline:
                preserve("probe-budget-exhausted")
                continue
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except OSError:
                result["errors"] += 1
                preserve("remove_failed")
                continue
            if path.exists() or path.is_symlink():
                result["errors"] += 1
                preserve("path_still_present")
                continue
            result["reclaimed"] += before
        free_after, _ = self.usage()
        result["free_before"] = free_before
        result["free_after"] = free_after
        result["preserved_reasons"] = reasons
        if write_receipt:
            self._receipt(result)
        return result

    def discover_candidates(self) -> list[dict]:
        """Return only allow-listed regenerable families.

        Discovery is intentionally narrower than census: an unclassified path
        can be measured and reported by another observer, but it cannot become
        a deletion candidate merely because it is large.
        """
        candidates: list[dict] = []
        temporary = Path(tempfile.gettempdir())
        temp_parent = temporary.parent
        clone_root = temp_parent / "X"
        for collection_name in (
            "com.google.Chrome.code_sign_clone",
            "org.chromium.Chromium.code_sign_clone",
        ):
            collection = clone_root / collection_name
            if collection.is_dir() and not collection.is_symlink():
                for child in sorted(collection.glob("code_sign_clone.*")):
                    if child.is_dir() and not child.is_symlink():
                        candidates.append(
                            {
                                "path": child,
                                "class": "regenerable_output",
                                "owner": "browser",
                                "discovery": "allowlisted",
                            }
                        )
        # These are owned one-shot test/build homes. The prefix is the proof;
        # arbitrary /private/tmp directories remain unknown and are preserved.
        if temporary.is_dir():
            for child in sorted(temporary.iterdir()):
                if child.is_dir() and any(
                    child.name.startswith(prefix)
                    for prefix in ("cfo-",)
                ):
                    candidates.append(
                        {
                            "path": child,
                            "class": "ephemeral",
                            "owner": "temporary-run",
                            "discovery": "allowlisted",
                        }
                    )
        return candidates

    def run_once(self) -> dict[str, int | str]:
        deadline = self.clock() + GOVERNOR_BUDGET_SECONDS
        free_before, _ = self.usage()
        result = self.sweep(
            self.discover_candidates(),
            write_receipt=False,
            deadline=deadline,
        )
        free_after = int(result["free_after"])
        pressure_file = self.state_dir / "disk-pressure.block"
        if free_after < 11 * GiB:
            pressure_file.write_text(
                json.dumps(
                    {
                        "tier": classify_tier(free_after),
                        "free_bytes": free_after,
                        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        elif free_after >= 20 * GiB:
            pressure_file.unlink(missing_ok=True)
        full_inventory = (
            os.environ.get("EMERGENCY_GUARD_FULL_PASS") == "1" or self._full_inventory_due()
        )
        try:
            inventory_kwargs = {
                "home": self.home,
                "state_dir": self.state_dir,
                "full": full_inventory,
            }
            if full_inventory:
                inventory_kwargs["budget_seconds"] = min(
                    FULL_INVENTORY_BUDGET_SECONDS,
                    max(0.0, deadline - self.clock()),
                )
            inventory = collect_host_inventory(**inventory_kwargs)
            inventory_budget_exhausted = any(
                gap.startswith("size-budget-exhausted:")
                for gap in inventory["coverage"]["gaps"]
            )
            if full_inventory and not inventory_budget_exhausted:
                self._mark_full_inventory()
            result["inventory_mode"] = "full" if full_inventory else "fast"
            result["inventory_mounts"] = int(inventory["coverage"]["mount_count"])
            result["inventory_roots"] = int(inventory["coverage"]["root_count"])
            result["inventory_gaps"] = len(inventory["coverage"]["gaps"])
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            result["inventory_error"] = type(exc).__name__
        self._receipt(result)
        result["free_before"] = free_before
        return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--candidate", action="append", type=Path, default=[])
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.candidate:
        raise SystemExit(
            "--candidate is disabled; cleanup candidates must come from the allow-listed discovery"
        )
    governor = HostDiskGovernor(home=args.home, state_dir=args.state_dir)
    if not governor.acquire_lock():
        return 0
    try:
        print(json.dumps(governor.run_once(), sort_keys=True))
    finally:
        governor.release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
