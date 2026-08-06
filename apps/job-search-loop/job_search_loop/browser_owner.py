from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import signal
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


def probe_cdp(endpoint: str) -> dict[str, str]:
    base = endpoint.rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/json/version", timeout=5) as response:
            payload: Any = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        return {"status": "unavailable", "endpoint": base, "error": str(error)}
    browser = payload.get("Browser") if isinstance(payload, dict) else None
    websocket = payload.get("webSocketDebuggerUrl") if isinstance(payload, dict) else None
    if not isinstance(browser, str) or not isinstance(websocket, str):
        return {"status": "unavailable", "endpoint": base, "error": "CDP version response is incomplete"}
    return {"status": "ready", "endpoint": base, "browser": browser, "websocket": websocket}


def attach_browser_use_cdp(endpoint: str) -> dict[str, Any]:
    from .browser_use_adapter import PinnedBrowserUseBackend

    backend = PinnedBrowserUseBackend(endpoint, allowed_domains=["jobs.ashbyhq.com"])
    try:
        backend.connect()
        snapshot = backend.snapshot()
        frames = snapshot.get("frames") if isinstance(snapshot, dict) else None
        if not isinstance(frames, list) or not frames:
            raise RuntimeError("CloakBrowser default context is missing")
        return {
            "browser": "browser-use/0.13.7",
            "context_count": len(frames),
        }
    finally:
        backend.close()


def _restart_browser_launchagent(label: str) -> None:
    if label != "ai.anicca.job-search-browser":
        raise RuntimeError("browser recovery label is not authorized")
    completed = subprocess.run(
        ["/bin/launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{label}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("browser LaunchAgent restart failed")


def _browser_pid(port: int) -> int:
    completed = subprocess.run(
        ["/usr/sbin/lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        capture_output=True, text=True, check=False,
    )
    pids = {int(row) for row in completed.stdout.splitlines() if row.isdigit()}
    if len(pids) != 1:
        raise RuntimeError("browser listener is not unique")
    return pids.pop()


def _private_write(path: Path, value: dict[str, Any] | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    os.chmod(path, 0o600)


@dataclass
class BrowserLease:
    guard: Path
    identity: str
    owner: str
    receipt_path: Path
    lease_path: Path
    fence_path: Path
    holder_pid: int = os.getpid()
    browser_pid_reader: Callable[[int], int] = _browser_pid

    def _held_by_self(self, receipt: dict[str, Any] | None = None) -> bool:
        try:
            held = json.loads(self.lease_path.read_text(encoding="utf-8").splitlines()[-1])
        except (OSError, json.JSONDecodeError, IndexError):
            return False
        matches = held.get("identity") == self.identity and held.get("pid") == self.holder_pid
        if receipt is not None:
            matches = matches and held.get("acquired_at") == receipt.get("lease_acquired_at")
        return matches

    def _guard_release(self) -> bool:
        completed = subprocess.run(
            [str(self.guard), "release", self.identity], capture_output=True,
            text=True, check=False,
        )
        return completed.returncode == 0

    def acquire(self) -> dict[str, Any]:
        environment = os.environ.copy()
        environment["AI_BROWSER_HOLDER_PID"] = str(self.holder_pid)
        completed = subprocess.run(
            [str(self.guard), "acquire", self.identity], capture_output=True,
            text=True, check=False, env=environment,
        )
        if completed.returncode == 9:
            raise RuntimeError("browser lease busy")
        if completed.returncode != 0:
            raise RuntimeError("browser lease unavailable")
        try:
            endpoint = completed.stdout.strip().rstrip("/")
            parsed = urlsplit(endpoint)
            if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port:
                raise RuntimeError("browser guard returned an invalid endpoint")
            held = json.loads(self.lease_path.read_text(encoding="utf-8").splitlines()[-1])
            if (
                held.get("identity") != self.identity or held.get("pid") != self.holder_pid
                or held.get("host") != socket.gethostname().split(".")[0]
                or held.get("port") != parsed.port or not isinstance(held.get("uuid"), str)
                or not held.get("uuid") or not isinstance(held.get("acquired_at"), int)
            ):
                raise RuntimeError("browser lease receipt mismatch")
            try:
                fence = int(self.fence_path.read_text(encoding="utf-8").strip()) + 1
            except (OSError, ValueError):
                fence = 1
            _private_write(self.fence_path, f"{fence}\n")
            now = datetime.now(timezone.utc).isoformat()
            lease_material = f"{self.identity}\n{held['host']}\n{self.holder_pid}\n{held['acquired_at']}\n{held['uuid']}"
            receipt = {
                "version": 2, "status": "leased", "owner": self.owner,
                "identity": self.identity, "endpoint": endpoint,
                "lease_id": hashlib.sha256(lease_material.encode()).hexdigest(),
                "fence": fence, "holder_pid": self.holder_pid,
                "browser_pid": self.browser_pid_reader(parsed.port),
                "acquired_at": now, "heartbeat_at": now,
                "lease_acquired_at": held["acquired_at"],
            }
            _private_write(self.receipt_path, receipt)
            return receipt
        except Exception:
            if self._held_by_self():
                self._guard_release()
            raise

    def beat(self) -> bool:
        try:
            receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not self._held_by_self(receipt):
            return False
        completed = subprocess.run(
            [str(self.guard), "beat", self.identity], capture_output=True,
            text=True, check=False,
        )
        if completed.returncode != 0:
            return False
        receipt["heartbeat_at"] = datetime.now(timezone.utc).isoformat()
        _private_write(self.receipt_path, receipt)
        return True

    def release(self) -> bool:
        try:
            receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
            held = json.loads(self.lease_path.read_text(encoding="utf-8").splitlines()[-1])
        except (OSError, json.JSONDecodeError, IndexError):
            return False
        same_holder = self._held_by_self(receipt) and (
            receipt.get("owner") == self.owner
            and receipt.get("identity") == self.identity
            and receipt.get("holder_pid") == self.holder_pid
        )
        if not same_holder:
            return False
        if not self._guard_release():
            return False
        receipt["status"] = "released"
        receipt["released_at"] = datetime.now(timezone.utc).isoformat()
        _private_write(self.receipt_path, receipt)
        return True


def acquire_with_attach_recovery(
    lease: BrowserLease,
    *,
    attach_probe: Callable[[str], dict[str, Any]] = attach_browser_use_cdp,
    restart_browser: Callable[[str], Any] = _restart_browser_launchagent,
    readiness_wait: Callable[[float], Any] = time.sleep,
) -> dict[str, Any]:
    attempts = 0
    while attempts < 2:
        if attempts == 0:
            receipt = lease.acquire()
        else:
            for readiness_attempt in range(30):
                try:
                    receipt = lease.acquire()
                    break
                except RuntimeError as error:
                    if str(error) != "browser lease unavailable" or readiness_attempt == 29:
                        raise
                    readiness_wait(0.5)
        attempts += 1
        try:
            attached = attach_probe(str(receipt["endpoint"]))
        except Exception:
            if not lease.release():
                raise RuntimeError("failed CDP attach lease could not be released")
            if attempts == 2:
                raise
            restart_browser("ai.anicca.job-search-browser")
            continue
        receipt["attach_status"] = "ready"
        receipt["status"] = "ready"
        receipt["attach_attempts"] = attempts
        receipt["attach_browser"] = str(attached.get("browser") or "")
        receipt["attach_context_count"] = int(attached.get("context_count") or 0)
        receipt["attach_verified_at"] = datetime.now(timezone.utc).isoformat()
        if lease.receipt_path.is_file():
            _private_write(lease.receipt_path, receipt)
        return receipt
    raise RuntimeError("CDP attach recovery exhausted")


def _defaults(args: argparse.Namespace) -> BrowserLease:
    identity = args.identity
    lease_name = identity.replace("/", "_").replace(":", "_") + ".lease"
    return BrowserLease(
        guard=args.guard.expanduser(), identity=identity, owner=args.owner,
        receipt_path=args.output.expanduser(),
        lease_path=args.lease_dir.expanduser() / lease_name,
        fence_path=args.fence.expanduser(), holder_pid=args.holder_pid,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("acquire", "beat", "hold", "release"))
    parser.add_argument("--identity", default="job-search:dais")
    parser.add_argument("--owner", default="ai.anicca.job-search-daily")
    parser.add_argument("--guard", type=Path, default=Path("~/.config/ai/bin/browser-guard.sh"))
    parser.add_argument("--lease-dir", type=Path, default=Path("~/.cloak/leases"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fence", type=Path, required=True)
    parser.add_argument("--holder-pid", type=int, default=os.getppid())
    args = parser.parse_args()
    lease = _defaults(args)
    if args.action == "acquire":
        result = acquire_with_attach_recovery(lease)
        print(json.dumps({"status": result["status"], "fence": result["fence"]}))
    elif args.action == "beat":
        if not lease.beat():
            raise SystemExit(1)
        print(json.dumps({"status": "renewed"}))
    elif args.action == "hold":
        stopped = threading.Event()
        signal.signal(signal.SIGTERM, lambda signum, frame: stopped.set())
        signal.signal(signal.SIGINT, lambda signum, frame: stopped.set())
        while not stopped.wait(300):
            if not lease.beat():
                raise SystemExit(1)
    else:
        if not lease.release():
            raise SystemExit(1)
        print(json.dumps({"status": "released"}))


if __name__ == "__main__":
    main()
