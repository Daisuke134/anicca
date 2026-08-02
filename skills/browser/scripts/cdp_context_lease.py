#!/usr/bin/env python3
"""Give each loop a fenced browser context lease.

Every loop drives the same Chromium.  A BrowserContext gives a task private tabs,
but context disposal must also be fenced: an old process must never dispose a
context that a newer process has acquired under the same task name.

    python3 cdp_context_lease.py acquire gig
    python3 cdp_context_lease.py heartbeat gig --token TOKEN --generation N
    python3 cdp_context_lease.py release gig --token TOKEN --generation N
    python3 cdp_context_lease.py gc --idle-min 45
    python3 cdp_context_lease.py list
"""
import asyncio
from contextlib import contextmanager
import fcntl
import json
import os
import secrets
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlparse

try:
    import websockets
except ImportError:
    print(json.dumps({"ok": False, "reason": "pip install websockets"}))
    sys.exit(1)


_LEDGER_META_KEY = "_lease_fence_meta"


def _cdp_base():
    return os.environ.get("CLOAK_CDP_BASE_URL", "http://127.0.0.1:9222").rstrip("/")


def _vault_path():
    return os.path.expanduser(
        os.environ.get(
            "CLOAK_SESSION_VAULT_FILE",
            "~/.cloak/vault/daily-driver/auth-state.json",
        )
    )


def _leases_path():
    return os.path.expanduser(
        os.environ.get("CLOAK_CONTEXT_LEASES_FILE", "~/.cloak/vault/leases.json")
    )


def _leases_dir():
    return os.path.dirname(os.path.abspath(_leases_path()))


def _ledger_lock_path():
    return _leases_path() + ".lock"


def _operation_lock_path(target_id):
    return os.path.join(_leases_dir(), "operations", f"{target_id}.lock")


def _page_ws(target_id):
    return f"ws://{urlparse(_cdp_base()).netloc}/devtools/page/{target_id}"


def _browser_ws():
    d = json.loads(
        urllib.request.urlopen(f"{_cdp_base()}/json/version", timeout=8).read()
    )
    return d["webSocketDebuggerUrl"]


async def _calls(pairs):
    """Run several CDP calls on one browser connection; returns the list of results."""
    out = []
    async with websockets.connect(_browser_ws(), max_size=64 * 1024 * 1024) as ws:
        for i, (method, params) in enumerate(pairs, start=1):
            await ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == i:
                    if "error" in msg:
                        raise RuntimeError(f"{method}: {msg['error']}")
                    out.append(msg.get("result", {}))
                    break
    return out


@contextmanager
def _ledger_lock():
    """Serialize a short lease-ledger read/modify/write transaction."""
    lock_path = _ledger_lock_path()
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _target_operation_lock(target_id):
    """Keep disposal mutually exclusive with a caller using this target."""
    lock_path = _operation_lock_path(target_id)
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as operation_lock:
        fcntl.flock(operation_lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(operation_lock.fileno(), fcntl.LOCK_UN)


def _read_ledger_locked():
    """Read the legacy-flat ledger while holding _ledger_lock()."""
    try:
        with open(_leases_path(), encoding="utf-8") as handle:
            raw = json.load(handle)
    except FileNotFoundError:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("lease ledger must be a JSON object")

    meta = raw.get(_LEDGER_META_KEY, {})
    if not isinstance(meta, dict):
        raise ValueError("lease ledger metadata must be an object")
    generations = meta.get("generations", {})
    if not isinstance(generations, dict):
        raise ValueError("lease ledger generations must be an object")
    if any(not _valid_generation(generation) for generation in generations.values()):
        raise ValueError("lease ledger contains an invalid generation")
    leases = {}
    for task, held in raw.items():
        if task == _LEDGER_META_KEY:
            continue
        if not isinstance(held, dict):
            raise ValueError("lease ledger contains an invalid lease row")
        leases[task] = held
    return {"leases": leases, "generations": generations}


def _atomic_write_ledger(data):
    """Replace the ledger durably; callers hold _ledger_lock() for the RMW."""
    leases_path = _leases_path()
    leases_dir = _leases_dir()
    os.makedirs(leases_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(leases_path)}.", suffix=".tmp", dir=leases_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, leases_path)
        directory_fd = os.open(leases_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _save_ledger_locked(ledger):
    """Persist a normalized ledger while its flock is held."""
    data = dict(ledger["leases"])
    data[_LEDGER_META_KEY] = {"generations": dict(ledger["generations"])}
    _atomic_write_ledger(data)


def _leases():
    """Return active leases without exposing fence metadata to legacy callers."""
    with _ledger_lock():
        return _read_ledger_locked()["leases"]


def _save(leases):
    """Compatibility helper for callers that previously saved a flat lease map."""
    with _ledger_lock():
        ledger = _read_ledger_locked()
        ledger["leases"] = {
            task: held for task, held in leases.items() if isinstance(held, dict)
        }
        for task, held in ledger["leases"].items():
            ledger["generations"][task] = max(
                _generation_value(ledger["generations"].get(task)),
                _generation_value(held.get("generation")),
            )
        _save_ledger_locked(ledger)


def _valid_generation(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _identity(held):
    token = held.get("token") if isinstance(held, dict) else None
    generation = held.get("generation") if isinstance(held, dict) else None
    if isinstance(token, str) and token and _valid_generation(generation):
        return token, generation
    return None


def _matches_identity(held, token, generation):
    return (
        isinstance(token, str)
        and bool(token)
        and _valid_generation(generation)
        and _identity(held) == (token, generation)
    )


def _same_lease(current, expected):
    """Compare a pinned lease, including legacy rows that predate fencing."""
    expected_identity = _identity(expected)
    if expected_identity is not None:
        return _identity(current) == expected_identity
    return all(
        current.get(field) == expected.get(field)
        for field in ("context_id", "target_id", "ws", "ts")
    )


def _generation_value(value):
    return value if _valid_generation(value) else 0


def _next_identity(ledger, task):
    held = ledger["leases"].get(task, {})
    generation = max(
        _generation_value(ledger["generations"].get(task)),
        _generation_value(held.get("generation")),
    ) + 1
    ledger["generations"][task] = generation
    return secrets.token_hex(16), generation


def _refresh_held_locked(ledger, task, held, now):
    """Give legacy rows a fence and refresh a current holder's liveness."""
    identity = _identity(held)
    if identity is None:
        token, generation = _next_identity(ledger, task)
        held["token"] = token
        held["generation"] = generation
    else:
        ledger["generations"][task] = max(
            _generation_value(ledger["generations"].get(task)), identity[1]
        )
    held.setdefault("ts", now)
    held["heartbeat_at"] = now
    return held


def _is_dispose_pending(held):
    return bool(held.get("dispose_pending"))


def _release_is_authorized(held, token, generation):
    """Fenced rows require their fence; credentialless release is legacy-only."""
    if "token" not in held and "generation" not in held:
        return token is None
    return token is not None and _matches_identity(held, token, generation)


def _already_disposed(error):
    """Treat CDP's authoritative context-absence responses as recoverable.

    Chromium TargetHandler emits ``Failed to find context with id <id>`` when the
    context is already gone, so retaining that pending ledger row would leak it.
    """
    message = str(error).lower()
    return any(
        phrase in message
        for phrase in (
            "browser context not found",
            "no browser context with given id",
            "cannot find browser context",
            "failed to find context with id",
        )
    )


def _mark_dispose_pending_locked(ledger, task, expected, idle_min=None):
    """Pin a matching row durably before its browser context can be disposed."""
    current = ledger["leases"].get(task)
    if not current or not _same_lease(current, expected):
        return None
    if not _is_dispose_pending(current):
        if idle_min is not None and not _stale(current, time.time(), idle_min):
            return None
        current["dispose_pending"] = True
        _save_ledger_locked(ledger)
    return dict(current)


def _finalize_disposal(task, expected):
    """Delete only the exact durable pending row after disposal is authoritative."""
    with _ledger_lock():
        ledger = _read_ledger_locked()
        current = ledger["leases"].get(task)
        if (
            not current
            or not _same_lease(current, expected)
            or not _is_dispose_pending(current)
        ):
            return False
        del ledger["leases"][task]
        _save_ledger_locked(ledger)
        return True


def _dispose(held):
    asyncio.run(
        _calls(
            [
                (
                    "Target.disposeBrowserContext",
                    {"browserContextId": held["context_id"]},
                )
            ]
        )
    )


def _dispose_discarded_context(held):
    """Clean up a concurrent acquire loser without holding the ledger lock."""
    with _target_operation_lock(held["target_id"]):
        _dispose(held)


def acquire(task, url="about:blank", no_seed=False):
    """Acquire or heartbeat a task lease; every result carries a fence identity."""
    with _ledger_lock():
        ledger = _read_ledger_locked()
        held = ledger["leases"].get(task)
        if held:
            if _is_dispose_pending(held):
                return {"ok": False, "reason": "lease disposal pending", "task": task}
            held = _refresh_held_locked(ledger, task, held, time.time())
            _save_ledger_locked(ledger)
            return {"ok": True, "reused": True, **held}

    cookies = []
    vault_path = _vault_path()
    if not no_seed and os.path.exists(vault_path):
        with open(vault_path, encoding="utf-8") as handle:
            cookies = json.load(handle).get("cookies", [])

    (ctx,) = asyncio.run(_calls([("Target.createBrowserContext", {})]))
    ctx_id = ctx["browserContextId"]
    calls = []
    if cookies:
        calls.append(("Storage.setCookies", {"cookies": cookies, "browserContextId": ctx_id}))
    calls.append(("Target.createTarget", {"url": url, "browserContextId": ctx_id}))
    results = asyncio.run(_calls(calls))
    target_id = results[-1]["targetId"]
    candidate = {
        "context_id": ctx_id,
        "target_id": target_id,
        "ws": _page_ws(target_id),
        "ts": time.time(),
        "cookies_seeded": len(cookies),
    }

    discarded = None
    with _ledger_lock():
        ledger = _read_ledger_locked()
        held = ledger["leases"].get(task)
        if held:
            if _is_dispose_pending(held):
                result = {"ok": False, "reason": "lease disposal pending", "task": task}
            else:
                held = _refresh_held_locked(ledger, task, held, time.time())
                _save_ledger_locked(ledger)
                result = {"ok": True, "reused": True, **held}
            discarded = candidate
        else:
            token, generation = _next_identity(ledger, task)
            candidate["token"] = token
            candidate["generation"] = generation
            candidate["heartbeat_at"] = candidate["ts"]
            ledger["leases"][task] = candidate
            _save_ledger_locked(ledger)
            result = {"ok": True, "reused": False, **candidate}

    if discarded:
        try:
            _dispose_discarded_context(discarded)
        except Exception:
            # The current lease remains usable; do not overwrite it to record a loser.
            pass
    return result


def heartbeat(task, token, generation):
    """Refresh only the exact current lease identity."""
    with _ledger_lock():
        ledger = _read_ledger_locked()
        held = ledger["leases"].get(task)
        if (
            not held
            or _is_dispose_pending(held)
            or not _matches_identity(held, token, generation)
        ):
            return {"ok": False, "reason": "stale or missing lease"}
        held["heartbeat_at"] = time.time()
        _save_ledger_locked(ledger)
        return {
            "ok": True,
            "task": task,
            "token": token,
            "generation": generation,
            "heartbeat_at": held["heartbeat_at"],
        }


def _stale(held, now, idle_min):
    try:
        heartbeat_at = float(held.get("heartbeat_at", held.get("ts", 0)))
    except (TypeError, ValueError):
        heartbeat_at = 0
    return now - heartbeat_at > idle_min * 60


def release(task, token=None, generation=None):
    """Fence and durably mark a lease before disposing its browser context."""
    if (token is None) != (generation is None):
        return {"ok": False, "reason": "token and generation must be provided together"}

    with _ledger_lock():
        ledger = _read_ledger_locked()
        held = ledger["leases"].get(task)
        if not held:
            if token is None:
                return {"ok": True, "note": f"{task} held no context"}
            return {"ok": False, "reason": "stale or missing lease"}
        if not _release_is_authorized(held, token, generation):
            return {"ok": False, "reason": "fence credentials required or stale"}
        pinned = dict(held)

    with _target_operation_lock(pinned["target_id"]):
        with _ledger_lock():
            ledger = _read_ledger_locked()
            current = ledger["leases"].get(task)
            if not current or not _same_lease(current, pinned):
                return {"ok": False, "reason": "stale or missing lease"}
            if not _release_is_authorized(current, token, generation):
                return {"ok": False, "reason": "fence credentials required or stale"}
            pending = _mark_dispose_pending_locked(ledger, task, pinned)
            if not pending:
                return {"ok": False, "reason": "stale or missing lease"}
        try:
            _dispose(pending)
        except Exception as exc:
            if not _already_disposed(exc):
                return {"ok": False, "reason": f"dispose failed: {exc}", "dispose_pending": True}
        if not _finalize_disposal(task, pending):
            return {"ok": False, "reason": "lease changed while finalizing disposal"}
    return {"ok": True, "released": task, "context_id": pending["context_id"]}


def gc(idle_min=45):
    """Reap only still-stale (or previously pending) exact lease identities."""
    with _ledger_lock():
        ledger = _read_ledger_locked()
        now = time.time()
        candidates = [
            (task, dict(held))
            for task, held in ledger["leases"].items()
            if held.get("context_id")
            and held.get("target_id")
            and (_is_dispose_pending(held) or _stale(held, now, idle_min))
        ]

    reaped = []
    dispose_failed = []
    for task, pinned in candidates:
        with _target_operation_lock(pinned["target_id"]):
            with _ledger_lock():
                ledger = _read_ledger_locked()
                pending = _mark_dispose_pending_locked(
                    ledger, task, pinned, idle_min=idle_min
                )
                if not pending:
                    continue
            try:
                _dispose(pending)
            except Exception as exc:
                if _already_disposed(exc):
                    pass
                else:
                    dispose_failed.append(task)
                    continue
            if not _finalize_disposal(task, pending):
                dispose_failed.append(task)
                continue
            reaped.append(task)

    return {
        "ok": not dispose_failed,
        "reaped": reaped,
        "still_held": list(_leases()),
        "dispose_failed": dispose_failed,
    }


def _parse_cli(argv):
    if not argv:
        return "list", [], {}
    command = argv[0]
    positionals = []
    options = {}
    index = 1
    while index < len(argv):
        argument = argv[index]
        if argument == "--no-seed":
            options["no_seed"] = True
            index += 1
        elif argument in ("--token", "--generation", "--idle-min"):
            if index + 1 >= len(argv):
                raise ValueError(f"{argument} requires a value")
            key = argument[2:].replace("-", "_")
            options[key] = argv[index + 1]
            index += 2
        elif argument.startswith("--"):
            raise ValueError(f"unknown option {argument}")
        else:
            positionals.append(argument)
            index += 1
    return command, positionals, options


def main(argv=None):
    """CLI adapter kept small so command parsing is testable without a browser."""
    try:
        command, positionals, options = _parse_cli(list(sys.argv[1:] if argv is None else argv))
        if command == "acquire":
            out = acquire(
                positionals[0] if positionals else "unnamed",
                no_seed=options.get("no_seed", False),
            )
        elif command == "heartbeat":
            if not positionals or "token" not in options or "generation" not in options:
                out = {"ok": False, "reason": "heartbeat requires TASK --token TOKEN --generation N"}
            else:
                out = heartbeat(positionals[0], options["token"], int(options["generation"]))
        elif command == "release":
            task = positionals[0] if positionals else "unnamed"
            token = options.get("token")
            generation = options.get("generation")
            if (token is None) != (generation is None):
                out = {"ok": False, "reason": "token and generation must be provided together"}
            else:
                out = release(task, token, int(generation) if generation is not None else None)
        elif command == "gc":
            out = gc(idle_min=int(options.get("idle_min", 45)))
        elif command == "list":
            out = {"ok": True, "leases": _leases()}
        else:
            out = {"ok": False, "reason": f"unknown command {command}"}
    except Exception as exc:
        out = {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
