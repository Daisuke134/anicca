"""Bounded, read-only host inventory for the Life Manager disk governor."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = "life-manager-host-inventory-v1"
# Full census is hourly and runs behind the governor's outer 120-second bound.
# A 3-second probe systematically missed otherwise bounded repository roots
# (measured 5–9s on the Mac mini), leaving their size unattributed. Ten seconds
# keeps the probe bounded while allowing those roots to be measured.
DU_TIMEOUT_SECONDS = 10
BUILD_TOOL_DU_TIMEOUT_SECONDS = 30
FULL_INVENTORY_BUDGET_SECONDS = 90
MAX_CHILDREN_PER_ROOT = 512

# These are observation families, not deletion roots.  A missing or unreadable
# family is recorded as a coverage gap instead of being silently skipped.
ROOT_FAMILIES = (
    ("user-home", "{home}"),
    ("repository-worktree", "{home}/Projects"),
    ("repository-worktree", "{home}/Projects/life-manager-main"),
    ("repository-worktree", "{home}/anicca-project"),
    ("repository-worktree", "{home}/anicca"),
    ("repository-worktree", "{home}/anicca-docs-tools"),
    ("repository-worktree", "{home}/anicca-portfolio-self-improve"),
    ("repository-worktree", "{home}/anicca-rtdash"),
    ("repository-worktree", "{home}/life-manager-repo-v0-retire"),
    ("repository-worktree", "{home}/.codex-worktrees"),
    ("gig-deliverable", "{home}/gig"),
    ("agent-runtime", "{home}/.openclaw"),
    ("agent-session", "{home}/.claude"),
    ("agent-session", "{home}/.codex"),
    ("browser-identity", "{home}/.cloak"),
    ("user-library", "{home}/Library"),
    ("downloads-trash", "{home}/Downloads"),
    ("downloads-trash", "{home}/.Trash"),
    ("system-library", "/Library"),
    ("system-temp", "/private/tmp"),
    ("system-temp", "/private/var/folders"),
    ("volume", "/Volumes"),
    ("build-tool", "/opt/homebrew"),
)

SIZE_PROBE_FAMILIES = {
    "repository-worktree",
    "gig-deliverable",
    "agent-runtime",
    "user-library",
    "system-temp",
    "build-tool",
}


def _run(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _parse_df(output: str) -> list[dict[str, Any]]:
    mounts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in output.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 6:
            continue
        filesystem, total, used, available, capacity = fields[:5]
        mount = fields[-1]
        if not mount.startswith("/") or mount in seen:
            continue
        try:
            values = {
                "total_bytes": int(total) * 1024,
                "used_bytes": int(used) * 1024,
                "available_bytes": int(available) * 1024,
            }
        except ValueError:
            continue
        seen.add(mount)
        mounts.append(
            {
                "filesystem": filesystem,
                "mount": mount,
                "capacity": capacity,
                "writable": os.access(mount, os.W_OK),
                **values,
            }
        )
    return mounts


def _mounts(run: Runner = _run, *, timeout: float = 5) -> tuple[list[dict[str, Any]], list[str]]:
    gaps: list[str] = []
    try:
        result = run(["/bin/df", "-P"], timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], [f"mount-census:{type(exc).__name__}"]
    if result.returncode != 0:
        gaps.append(f"mount-census:rc-{result.returncode}")
    mounts = _parse_df(result.stdout)
    if not mounts:
        gaps.append("mount-census:no-readable-mounts")
    return mounts, gaps


def _children(path: Path) -> tuple[dict[str, Any], list[str]]:
    gaps: list[str] = []
    record: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists() or path.is_symlink(),
        "symlink": path.is_symlink(),
        "measurement": "metadata-only",
        "children_seen": 0,
        "files_seen": 0,
        "directories_seen": 0,
        "symlinks_seen": 0,
    }
    if not record["exists"]:
        gaps.append(f"missing:{path}")
        return record, gaps
    if record["symlink"]:
        gaps.append(f"symlink-root:{path}")
        return record, gaps
    try:
        with os.scandir(path) as entries:
            for index, entry in enumerate(entries):
                if index >= MAX_CHILDREN_PER_ROOT:
                    record["truncated"] = True
                    gaps.append(f"child-limit:{path}")
                    break
                record["children_seen"] += 1
                try:
                    if entry.is_symlink():
                        record["symlinks_seen"] += 1
                    elif entry.is_dir(follow_symlinks=False):
                        record["directories_seen"] += 1
                    else:
                        record["files_seen"] += 1
                except OSError:
                    gaps.append(f"stat-error:{entry.path}")
    except PermissionError:
        gaps.append(f"permission-limited:{path}")
    except OSError as exc:
        gaps.append(f"scan-error:{path}:{type(exc).__name__}")
    return record, gaps


def _bounded_size(
    path: Path,
    run: Runner = _run,
    *,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[int | None, str, str | None]:
    timeout = BUILD_TOOL_DU_TIMEOUT_SECONDS if path == Path("/opt/homebrew") else DU_TIMEOUT_SECONDS
    if deadline is not None:
        remaining = deadline - clock()
        if remaining <= 0:
            return None, "budget-exhausted", "size-budget-exhausted"
        timeout = min(timeout, remaining)
    try:
        result = run(["/usr/bin/du", "-x", "-sk", str(path)], timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout", "size-timeout"
    except OSError as exc:
        return None, "error", f"size-error:{type(exc).__name__}"
    fields = result.stdout.split()
    parsed_size: int | None = None
    if fields:
        try:
            parsed_size = int(fields[0]) * 1024
        except ValueError:
            parsed_size = None
    if result.returncode != 0:
        if parsed_size is not None:
            error_text = (result.stderr or "").lower()
            gap = (
                "size-permission-partial"
                if "permission" in error_text or "not permitted" in error_text
                else f"size-partial-rc-{result.returncode}"
            )
            return parsed_size, "bounded-du-partial", gap
        return None, "error", f"size-rc-{result.returncode}"
    if parsed_size is None:
        return None, "error", "size-empty" if not fields else "size-invalid"
    return parsed_size, "bounded-du", None


def collect_host_inventory(
    *,
    home: Path,
    state_dir: Path,
    full: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    clock: Callable[[], float] = time.monotonic,
    budget_seconds: float | None = None,
) -> dict[str, Any]:
    """Collect and atomically persist a read-only, bounded host census."""

    run = runner or _run
    if full:
        budget = FULL_INVENTORY_BUDGET_SECONDS if budget_seconds is None else max(0.0, budget_seconds)
        deadline = clock() + budget
    else:
        deadline = None
    if full and deadline is not None:
        mount_remaining = deadline - clock()
        if mount_remaining <= 0:
            mounts, gaps = [], ["inventory-budget-exhausted"]
        else:
            mounts, gaps = _mounts(run, timeout=min(5, mount_remaining))
    else:
        mounts, gaps = _mounts(run)
    roots: list[dict[str, Any]] = []
    root_gaps = list(gaps)
    for family, template in ROOT_FAMILIES:
        path = Path(template.format(home=home))
        record, record_gaps = _children(path)
        record["owner_family"] = family
        if full and family in SIZE_PROBE_FAMILIES and record["exists"] and not record["symlink"]:
            size, measurement, size_gap = _bounded_size(path, run, deadline=deadline, clock=clock)
            record["size_bytes"] = size
            record["measurement"] = measurement
            if size_gap:
                record_gaps.append(f"{size_gap}:{path}")
        else:
            record["size_bytes"] = None
            if family in SIZE_PROBE_FAMILIES:
                record_gaps.append(f"size-deferred:{path}")
        roots.append(record)
        root_gaps.extend(record_gaps)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": "cleanup-control-v1",
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "full" if full else "fast",
        "mounts": mounts,
        "roots": roots,
        "coverage": {
            "mount_count": len(mounts),
            "root_count": len(roots),
            "gaps": sorted(set(root_gaps)),
            "unattributed_size_bytes": None,
            "complete": not root_gaps,
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload["inventory_sha256"] = hashlib.sha256(encoded).hexdigest()
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / "host-inventory.json"
    with tempfile.NamedTemporaryFile("w", dir=state_dir, prefix=".host-inventory.", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, target)
    payload["path"] = str(target)
    return payload
