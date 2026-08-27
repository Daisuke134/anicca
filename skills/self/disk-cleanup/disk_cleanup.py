#!/usr/bin/env python3
"""Fail-closed, host-wide disk governor for Life Manager.

The governor only removes explicitly classified, closed, regenerable artifacts.
Unknown paths, sessions, state, credentials, source, and probe failures remain.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, suppress
import errno
import fcntl
import json
import math
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

from host_inventory import FULL_INVENTORY_BUDGET_SECONDS, collect_host_inventory

GiB = 1024**3
PRODUCER_BLOCK_FLOOR_BYTES = 512 * 1024**2
PRODUCER_BLOCK_CLEAR_BYTES = GiB
FULL_INVENTORY_INTERVAL_SECONDS = 3600
GOVERNOR_BUDGET_SECONDS = 90
LSOF_TIMEOUT_SECONDS = 15
POST_SWEEP_RESERVE_SECONDS = 30
HEALTH_CHECK_TIMEOUT_SECONDS = 5
CANONICAL_LABEL = "ai.anicca.life-manager-disk-cleanup"
THRESHOLDS = ((20 * GiB, "NORMAL"), (11 * GiB, "PREVENTIVE"), (6 * GiB, "PRESSURE"), (3 * GiB, "CRITICAL"))
RECEIPT_RESERVE_BYTES = 1024 * 1024
RECEIPT_PAYLOAD_MAX_BYTES = 64 * 1024
SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".go", ".h", ".hpp", ".java", ".js", ".jsx",
    ".kt", ".kts", ".m", ".md", ".mm", ".py", ".rb", ".rs", ".sh", ".swift",
    ".ts", ".tsx",
}
SECRET_SUFFIXES = {".env", ".key", ".p12", ".pem", ".pfx"}


class _ReceiptAtomicFailure(Exception):
    def __init__(self, error: OSError) -> None:
        self.error = error


def classify_tier(free_bytes: int) -> str:
    for floor, tier in THRESHOLDS:
        if free_bytes >= floor:
            return tier
    return "ULTRA"


def _session_recovery_receipt() -> dict[str, object]:
    return {
        "authority": "gui-session-owner",
        "process_kill_authority": False,
        "required_readback": ["uid", "gui-domain", "canonical-label"],
        "stale_app_server_action": "observe-only",
    }


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


def _default_bootstrap_health(home: Path, state_dir: Path) -> dict[str, object]:
    """Read-only Directory Services and launchd preflight for the real Mac user."""
    if sys.platform != "darwin":
        return {"status": "not-applicable"}

    try:
        uid = os.getuid()
        username = pwd.getpwuid(uid).pw_name
    except (KeyError, OSError) as exc:
        return {
            "status": "failure",
            "error_code": "uid-resolution",
            "detail": type(exc).__name__,
            "domain": f"gui/{os.getuid()}",
            "label": CANONICAL_LABEL,
        }

    marker = state_dir / "host-inventory-full.at"
    try:
        known_good_marker: str | None = marker.read_text(encoding="utf-8").strip() or None
    except OSError:
        known_good_marker = None

    dscl_path = f"/Users/{username}"
    try:
        dscl = subprocess.run(
            ["/usr/bin/dscl", ".", "-read", dscl_path, "UniqueID", "NFSHomeDirectory"],
            capture_output=True,
            text=True,
            timeout=HEALTH_CHECK_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "failure",
            "error_code": "dscl-unavailable",
            "detail": type(exc).__name__,
            "domain": f"gui/{uid}",
            "label": CANONICAL_LABEL,
            "known_good_marker": known_good_marker,
        }
    if dscl.returncode != 0:
        return {
            "status": "failure",
            "error_code": f"dscl-rc-{dscl.returncode}",
            "domain": f"gui/{uid}",
            "label": CANONICAL_LABEL,
            "known_good_marker": known_good_marker,
        }
    uid_match = re.search(r"^UniqueID:\s*(\d+)\s*$", dscl.stdout, re.MULTILINE)
    home_match = re.search(r"^NFSHomeDirectory:\s*(\S+)\s*$", dscl.stdout, re.MULTILINE)
    if not uid_match or int(uid_match.group(1)) != uid or not home_match or home_match.group(1) != str(home):
        return {
            "status": "failure",
            "error_code": "uid-readback-mismatch",
            "domain": f"gui/{uid}",
            "label": CANONICAL_LABEL,
            "known_good_marker": known_good_marker,
        }

    domain = f"gui/{uid}"
    target = f"{domain}/{CANONICAL_LABEL}"
    try:
        launchctl = subprocess.run(
            ["/bin/launchctl", "print", target],
            capture_output=True,
            text=True,
            timeout=HEALTH_CHECK_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "failure",
            "error_code": "launchctl-unavailable",
            "detail": type(exc).__name__,
            "domain": domain,
            "label": CANONICAL_LABEL,
            "known_good_marker": known_good_marker,
        }
    if launchctl.returncode != 0:
        return {
            "status": "failure",
            "error_code": f"launchctl-{launchctl.returncode}",
            "domain": domain,
            "label": CANONICAL_LABEL,
            "known_good_marker": known_good_marker,
        }
    return {
        "status": "ok",
        "uid": uid,
        "domain": domain,
        "label": CANONICAL_LABEL,
        "known_good_marker": known_good_marker,
    }


class HostDiskGovernor:
    def __init__(
        self,
        *,
        home: Path | None = None,
        state_dir: Path | None = None,
        lsof: Callable[[Path], str] = _default_lsof,
        usage: Callable[[], tuple[int, int]] | None = None,
        clock: Callable[[], float] = time.monotonic,
        bootstrap_health: Callable[[], dict[str, object]] | None = None,
    ) -> None:
        self.home = (home or Path.home()).resolve()
        self.state_dir = (state_dir or self.home / ".openclaw/state").resolve()
        self.lock_dir = self.state_dir / ".life-manager-disk-cleanup.lock"
        self._lock_fd: int | None = None
        self.full_inventory_marker = self.state_dir / "host-inventory-full.at"
        self.lsof = lsof
        self.usage = usage or self._usage
        self.clock = clock
        self.bootstrap_health = bootstrap_health or (
            lambda: _default_bootstrap_health(self.home, self.state_dir)
        )

    def _checked_bootstrap_health(self) -> dict[str, object]:
        try:
            return self.bootstrap_health()
        except Exception as exc:  # fail closed if the preflight itself is broken
            return {
                "status": "failure",
                "error_code": "health-check-exception",
                "detail": type(exc).__name__,
            }

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

    @staticmethod
    def _active_lease(item: dict) -> bool:
        lease = item.get("lease")
        if lease is None:
            return False
        lease_path = lease.get("path") if isinstance(lease, dict) else lease
        if not isinstance(lease_path, (str, os.PathLike)):
            return True
        try:
            modified_at = Path(lease_path).expanduser().stat().st_mtime
        except FileNotFoundError:
            return False
        except OSError:
            return True
        if not isinstance(lease, dict):
            return True
        max_age = lease.get("max_age_seconds")
        if (
            isinstance(max_age, bool)
            or not isinstance(max_age, (int, float))
            or not math.isfinite(max_age)
            or max_age <= 0
        ):
            return True
        age = time.time() - modified_at
        return age < 0 or age <= max_age

    def acquire_lock(self) -> bool:
        if self._lock_fd is not None:
            return False
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            try:
                info = self.lock_dir.lstat()
            except FileNotFoundError:
                info = None
            except OSError:
                return False
            if info is not None:
                if stat.S_ISLNK(info.st_mode):
                    return False
                if stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) != 0o600:
                    return False
                if stat.S_ISDIR(info.st_mode):
                    return False
                elif not stat.S_ISREG(info.st_mode):
                    return False
            flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
            created = info is None
            if created:
                try:
                    fd = os.open(self.lock_dir, flags | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    created = False
                    fd = os.open(self.lock_dir, flags)
            else:
                fd = os.open(self.lock_dir, flags)
            opened = True
            try:
                if created:
                    os.fchmod(fd, 0o600)
                current = os.fstat(fd)
                if not stat.S_ISREG(current.st_mode) or stat.S_IMODE(current.st_mode) != 0o600:
                    return False
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._lock_fd = fd
                opened = False
                return True
            finally:
                if opened:
                    with suppress(OSError):
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    with suppress(OSError):
                        os.close(fd)
        except (BlockingIOError, OSError):
            return False

    def release_lock(self) -> None:
        fd, self._lock_fd = self._lock_fd, None
        if fd is None:
            return
        with suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        with suppress(OSError):
            os.close(fd)

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
        lowered_parts = {part.lower() for part in parts}
        if lowered_parts.intersection({".claude", ".codex", ".cloak", "anicca-rtdash", "anicca-monk-factory"}):
            return True
        protected_pairs = {
            (".config", "ai"),
            (".openclaw", "identity"),
            (".openclaw", "state"),
            (".openclaw", "workspace"),
        }
        if any(tuple(part.lower() for part in parts[index:index + 2]) in protected_pairs for index in range(len(parts) - 1)):
            return True
        if ".git" in parts or lowered_parts.intersection({"memory", "source", "src"}):
            return True
        if path.suffix.lower() in {".sqlite", ".db"} | SOURCE_SUFFIXES | SECRET_SUFFIXES:
            return True
        if len(parts) >= 2 and parts[-2] == "state" and path.suffix == ".jsonl":
            return True
        if path.name == ".env" or path.name.startswith(".env."):
            return True
        return any(
            token in path.name.lower()
            for token in (
                "auth", "cookie", "credential", "ledger", "login data", "payment",
                "publication", "receipt", "secret", "session", "transcript",
            )
        )

    def _protected_descendant(self, path: Path, *, deadline: float | None = None) -> str | None:
        errors: list[OSError] = []
        for root, directories, files in os.walk(
            path,
            topdown=True,
            followlinks=False,
            onerror=errors.append,
        ):
            if errors:
                return "descendant_probe_error"
            for name in directories + files:
                if deadline is not None and self.clock() >= deadline:
                    return "probe-budget-exhausted"
                descendant = Path(root) / name
                try:
                    if descendant.is_symlink() or self._protected(descendant):
                        return "protected_descendant"
                except OSError:
                    return "descendant_probe_error"
        return "descendant_probe_error" if errors else None

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
        if item.get("class") == "regenerable_output" and item.get("owner") == "codex-app-updater":
            installation = (
                self.home
                / "Library/Caches/com.openai.codex/org.sparkle-project.Sparkle/Installation"
            ).resolve()
            return (
                resolved.parent == installation
                and re.fullmatch(r"[A-Za-z0-9]{6,64}", resolved.name) is not None
            )
        if item.get("class") == "regenerable_output":
            exact_caches = {
                "codex-runtime-cache": (self.home / ".cache/codex-runtimes").resolve(),
                "whisper-model-cache": (self.home / ".cache/whisper").resolve(),
            }
            expected = exact_caches.get(item.get("owner"))
            if expected is not None:
                return resolved == expected
        return False

    @staticmethod
    def _receipt_reserve_valid(path: Path) -> bool:
        try:
            info = path.lstat()
        except OSError:
            return False
        return stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size == RECEIPT_RESERVE_BYTES and getattr(info, "st_blocks", 0) * 512 >= RECEIPT_RESERVE_BYTES

    @contextmanager
    def _staged_receipt_file(self, data: bytes, parent: Path, prefix: str, *, retryable: bool = False):
        fd, temporary_name = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=str(parent))
        temporary = Path(temporary_name)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                fd = -1
                try:
                    written = stream.write(data)
                    if written != len(data):
                        raise OSError(errno.EIO, "short receipt write")
                    stream.flush()
                    os.fsync(stream.fileno())
                except OSError as exc:
                    if retryable:
                        raise _ReceiptAtomicFailure(exc) from exc
                    raise
            yield temporary
        finally:
            with suppress(OSError):
                os.close(fd)
            temporary.unlink(missing_ok=True)

    def _receipt_reserve(self, *, recreate: bool = False) -> None:
        reserve = self.state_dir / ".receipt-reserve"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self._receipt_reserve_valid(reserve) and not recreate:
            return
        try:
            info = reserve.lstat()
        except FileNotFoundError:
            info = None
        if info is not None and stat.S_ISDIR(info.st_mode):
            raise IsADirectoryError(errno.EISDIR, "receipt reserve is a directory", reserve)
        if info is not None:
            reserve.unlink()
        with self._staged_receipt_file(
            b"\0" * RECEIPT_RESERVE_BYTES, self.state_dir, ".receipt-reserve."
        ) as temporary:
            if not self._receipt_reserve_valid(temporary) or len(temporary.read_bytes()) != RECEIPT_RESERVE_BYTES:
                raise OSError(errno.EIO, "receipt reserve readback failed")
            os.replace(temporary, reserve)
        self._fsync_receipt_parent(self.state_dir)

    def _consume_receipt_reserve(self) -> None:
        reserve = self.state_dir / ".receipt-reserve"
        if not self._receipt_reserve_valid(reserve):
            raise OSError(errno.EIO, "receipt reserve validation failed")
        reserve.unlink()

    @staticmethod
    def _fsync_receipt_parent(parent: Path) -> None:
        fd = -1
        try:
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            fd = os.open(str(parent), flags)
            os.fsync(fd)
        except OSError:
            pass
        with suppress(OSError):
            os.close(fd)

    def _atomic_receipt_write(self, data: bytes, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._staged_receipt_file(
            data, target.parent, f".{target.name}.", retryable=True
        ) as temporary:
            try:
                os.replace(temporary, target)
            except OSError as exc:
                raise _ReceiptAtomicFailure(exc) from exc
        self._fsync_receipt_parent(target.parent)

    def _receipt(self, payload: dict, filename: str = "last-receipt.json") -> None:
        payload.setdefault("observed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        if len(data) > RECEIPT_PAYLOAD_MAX_BYTES:
            raise ValueError("receipt payload exceeds 64 KiB")
        self._receipt_reserve()
        target = self.state_dir / filename
        try:
            self._atomic_receipt_write(data, target)
            return
        except _ReceiptAtomicFailure as failure:
            if failure.error.errno != errno.ENOSPC:
                raise failure.error
        self._consume_receipt_reserve()
        try:
            self._atomic_receipt_write(data, target)
        except _ReceiptAtomicFailure as failure:
            raise failure.error
        self._receipt_reserve(recreate=True)

    def _canary_receipt(self, payload: dict[str, object]) -> None:
        """Keep the initial effect and the immediate replay in one receipt."""
        target = self.state_dir / "canary-last-receipt.json"
        if payload.get("reason") == "canary-path-missing":
            try:
                previous = json.loads(target.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, ValueError):
                previous = None
            if isinstance(previous, dict) and previous.get("canary_path") == payload.get("canary_path"):
                initial = previous.get("initial", previous)
                envelope = {
                    "schema_version": "life-manager-canary-receipt-v1",
                    "phase": "replay",
                    "canary_path": payload.get("canary_path"),
                    "initial": initial,
                    "replay": payload,
                }
                self._receipt(envelope, "canary-last-receipt.json")
                return
        if payload.get("removed") is True:
            payload = {
                "schema_version": "life-manager-canary-receipt-v1",
                "phase": "initial",
                "canary_path": payload.get("canary_path"),
                "initial": payload,
            }
        self._receipt(payload, "canary-last-receipt.json")

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
            if self._active_lease(item):
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
            descendant_state = self._protected_descendant(path, deadline=deadline)
            if descendant_state is not None:
                result["errors"] += descendant_state == "descendant_probe_error"
                preserve(descendant_state)
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
            descendant_state = self._protected_descendant(path, deadline=deadline)
            if descendant_state is not None:
                result["errors"] += descendant_state == "descendant_probe_error"
                preserve(descendant_state)
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
            if self._active_lease(item):
                preserve("active_lease")
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
        for relative, owner in (
            (".cache/codex-runtimes", "codex-runtime-cache"),
            (".cache/whisper", "whisper-model-cache"),
        ):
            cache = self.home / relative
            if cache.is_dir() and not cache.is_symlink():
                candidates.append({
                    "path": cache,
                    "class": "regenerable_output",
                    "owner": owner,
                    "discovery": "allowlisted",
                })
        sparkle_installation = (
            self.home
            / "Library/Caches/com.openai.codex/org.sparkle-project.Sparkle/Installation"
        )
        if sparkle_installation.is_dir() and not sparkle_installation.is_symlink():
            for child in sorted(sparkle_installation.iterdir()):
                if (
                    child.is_dir()
                    and not child.is_symlink()
                    and re.fullmatch(r"[A-Za-z0-9]{6,64}", child.name) is not None
                ):
                    candidates.append(
                        {
                            "path": child,
                            "class": "regenerable_output",
                            "owner": "codex-app-updater",
                            "discovery": "allowlisted",
                        }
                    )
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

    def run_once(self) -> dict[str, object]:
        deadline = self.clock() + GOVERNOR_BUDGET_SECONDS
        free_before, _ = self.usage()
        health = self._checked_bootstrap_health()
        if health.get("status") not in {"ok", "not-applicable"}:
            result: dict[str, object] = {
                "tier": classify_tier(free_before),
                "evaluated": 0,
                "reclaimed": 0,
                "preserved": 0,
                "errors": 1,
                "protected_deletions": 0,
                "reason": "gui-bootstrap-health-failure",
                "health": health,
                "session_recovery": _session_recovery_receipt(),
                "free_before": free_before,
                "free_after": free_before,
                "preserved_reasons": {"gui-bootstrap-health-failure": 1},
            }
            self._receipt(result)
            return result
        result = self.sweep(
            self.discover_candidates(),
            write_receipt=False,
            deadline=deadline,
        )
        free_after = int(result["free_after"])
        pressure_file = self.state_dir / "disk-pressure.block"
        if free_after < PRODUCER_BLOCK_FLOOR_BYTES:
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
        elif free_after >= PRODUCER_BLOCK_CLEAR_BYTES:
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

    def run_canary(self, path: Path) -> dict[str, object]:
        """Reclaim one exact, allow-listed temporary canary and record replay proof."""
        deadline = self.clock() + GOVERNOR_BUDGET_SECONDS
        free_before, _ = self.usage()
        canary_path = str(path.expanduser().resolve())
        health = self._checked_bootstrap_health()
        if health.get("status") not in {"ok", "not-applicable"}:
            result: dict[str, object] = {
                "tier": classify_tier(free_before),
                "evaluated": 0,
                "reclaimed": 0,
                "preserved": 0,
                "errors": 1,
                "protected_deletions": 0,
                "reason": "gui-bootstrap-health-failure",
                "health": health,
                "session_recovery": _session_recovery_receipt(),
                "canary_path": canary_path,
                "before_bytes": 0,
                "after_bytes": 0,
                "removed": False,
                "duplicate_effect": 0,
            }
            self._canary_receipt(result)
            return result

        try:
            requested = path.expanduser()
            resolved = requested.resolve()
            temporary = Path(tempfile.gettempdir()).resolve()
        except OSError:
            resolved = Path(canary_path)
            temporary = Path(tempfile.gettempdir()).resolve()
            requested = path.expanduser()
        if (
            requested.is_symlink()
            or resolved.parent != temporary
            or not resolved.name.startswith("cfo-")
            or resolved.name == "cfo-"
        ):
            result = {
                "tier": classify_tier(free_before),
                "evaluated": 0,
                "reclaimed": 0,
                "preserved": 0,
                "errors": 0,
                "protected_deletions": 0,
                "reason": "canary-path-not-allowlisted",
                "canary_path": canary_path,
                "before_bytes": 0,
                "after_bytes": 0,
                "removed": False,
                "duplicate_effect": 0,
            }
            self._canary_receipt(result)
            return result
        if not resolved.exists():
            result = {
                "tier": classify_tier(free_before),
                "evaluated": 0,
                "reclaimed": 0,
                "preserved": 0,
                "errors": 0,
                "protected_deletions": 0,
                "reason": "canary-path-missing",
                "canary_path": canary_path,
                "before_bytes": 0,
                "after_bytes": 0,
                "removed": False,
                "duplicate_effect": 0,
            }
            self._canary_receipt(result)
            return result

        before = _bytes(resolved, deadline=deadline, clock=self.clock)
        if before is None:
            result = {
                "tier": classify_tier(free_before),
                "evaluated": 0,
                "reclaimed": 0,
                "preserved": 1,
                "errors": 0,
                "protected_deletions": 0,
                "reason": "canary-budget-exhausted",
                "canary_path": canary_path,
                "before_bytes": 0,
                "after_bytes": 0,
                "removed": False,
                "duplicate_effect": 0,
            }
            self._canary_receipt(result)
            return result

        candidate = {
            "path": resolved,
            "class": "ephemeral",
            "owner": "temporary-run",
            "discovery": "allowlisted",
        }
        result = dict(self.sweep([candidate], write_receipt=False, deadline=deadline))
        removed = not resolved.exists() and not resolved.is_symlink()
        after = 0 if removed else (_bytes(resolved, deadline=deadline, clock=self.clock) or 0)
        result.update(
            {
                "canary_path": canary_path,
                "before_bytes": before,
                "after_bytes": after,
                "removed": removed,
                "duplicate_effect": 0,
            }
        )
        if not removed and "reason" not in result:
            result["reason"] = "canary-preserved"
        self._canary_receipt(result)
        return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--candidate", action="append", type=Path, default=[])
    parser.add_argument("--canary", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.candidate and args.canary:
        raise SystemExit("--candidate and --canary cannot be combined")
    if args.candidate:
        raise SystemExit(
            "--candidate is disabled; cleanup candidates must come from the allow-listed discovery"
        )
    governor = HostDiskGovernor(home=args.home, state_dir=args.state_dir)
    if not governor.acquire_lock():
        return 0
    try:
        result = governor.run_canary(args.canary) if args.canary else governor.run_once()
        print(json.dumps(result, sort_keys=True))
    finally:
        governor.release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
