#!/usr/bin/env python3
"""Give each loop its own browser space so they stop destroying each other's work.

Every loop drives the same Chromium. When gig is halfway through a 応募 form and the clip loop
navigates "the" tab, gig's work is gone — and neither loop can tell that it happened.

CDP has the answer already: Target.createBrowserContext is "Similar to an incognito profile but you
can have more than one". So each task leases its own context, and nothing another loop does can reach
into it. Contexts do not share cookies, so the lease seeds the fresh context from the session vault —
the same trick as Playwright's storageState ("reuse this state and start already authenticated").

    python3 cdp_context_lease.py acquire gig            # -> {"context_id":..., "target_id":..., "ws":...}
    python3 cdp_context_lease.py release gig            # dispose the context (tabs die with it)
    python3 cdp_context_lease.py gc --idle-min 45       # reap contexts a crashed loop left behind
    python3 cdp_context_lease.py list
"""
import asyncio
import contextlib
import fcntl
import json
import os
import secrets
import sys
import time
import urllib.request
from urllib.parse import urlparse

try:
    import websockets
except ImportError:
    print(json.dumps({"ok": False, "reason": "pip install websockets"}))
    sys.exit(1)


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


def _operation_lock_path(target_id):
    leases_dir = os.path.dirname(_leases_path())
    return os.path.join(leases_dir, "operations", f"{target_id}.lock")


def _ledger_lock_path():
    return _leases_path() + ".lock"


@contextlib.contextmanager
def _ledger_lock():
    lock_path = _ledger_lock_path()
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _page_ws(target_id):
    return f"ws://{urlparse(_cdp_base()).netloc}/devtools/page/{target_id}"


def _browser_ws():
    d = json.loads(
        urllib.request.urlopen(f"{_cdp_base()}/json/version", timeout=8).read()
    )
    return d["webSocketDebuggerUrl"]


async def _calls(pairs, timeout=20.0):
    """Run several CDP calls on one browser connection; returns the list of results.

    The whole batch shares one deadline. recv() used to wait forever, so disposing a
    context whose renderer was wedged hung this script until the caller's subprocess limit
    killed it (measured 2026-08-06: the gig loop's target recovery died inside `release`).
    A browser that keeps the socket open while never answering must become an exception
    here, not a hang.
    """
    out = []
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    async with websockets.connect(
        _browser_ws(), max_size=64 * 1024 * 1024, open_timeout=min(10.0, timeout)
    ) as ws:
        for i, (method, params) in enumerate(pairs, start=1):
            await ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise TimeoutError(f"{method} did not answer within {timeout}s")
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
                if msg.get("id") == i:
                    if "error" in msg:
                        raise RuntimeError(f"{method}: {msg['error']}")
                    out.append(msg.get("result", {}))
                    break
    return out


def _pid_alive(pid):
    """Is the process that last proved it holds this lease still running?

    Every acquire()/heartbeat() call is a subprocess of its actual direct-loop holder
    (a one-shot owner pid, or application_parent.py's pid for LeaseHandle's background
    heartbeat thread), so os.getppid() at call time is a legitimate, stable holder id --
    the same holder keeps calling heartbeat with the same ppid until it exits or crashes.
    A -9'd holder never updates `ts` again either, so gc's existing idle_min window already
    catches it eventually; this lets gc catch it on its very next run instead of waiting up
    to idle_min. Unknown/missing pid (legacy rows, or a race writing it) means "cannot tell"
    -- never treated as dead, so it falls back to the idle_min-only path untouched.
    """
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, just not ours -- never claimed here, so leave it alone
    except OSError:
        return None  # inconclusive: do not reap on an ambiguous signal


def _leases():
    leases_path = _leases_path()
    if os.path.exists(leases_path):
        try:
            with open(leases_path, encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            pass
    return {}


def _save(d):
    leases_path = _leases_path()
    os.makedirs(os.path.dirname(leases_path), exist_ok=True)
    tmp = leases_path + f".{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, leases_path)


async def _target_answers(ws_url, timeout):
    try:
        async with websockets.connect(
            ws_url, open_timeout=timeout, ping_interval=None, max_size=1 << 20
        ) as ws:
            await ws.send(json.dumps({
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {"expression": "1", "returnByValue": True},
            }))
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return False
                message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
                if message.get("id") == 1:
                    return "error" not in message
    except Exception:
        return False


def target_responds(ws_url, timeout=6.0):
    """Does this leased page still answer, or is its renderer wedged?

    A held lease was reused on trust. When gig fills a 応募 form and then navigates that
    same target, the renderer stops and takes its CDP endpoint with it -- the loop's own
    domain-skills already record that -- and the lease keeps handing the dead target back
    on every later pass. On 2026-08-05 that turned one wedged renderer into
    cdp_Page.enable_timeout_after_30s on every B2 for hours: the apply lane could not run
    at all, and nothing in the lease could tell that the thing it was lending was gone.

    Runtime.evaluate of `1` is the cheapest question a live renderer always answers.
    """
    if not ws_url:
        return False
    try:
        return asyncio.run(_target_answers(ws_url, timeout))
    except Exception:
        return False


def acquire(task, url="about:blank", no_seed=False):
    with _ledger_lock():
        leases = _leases()
        held = leases.get(task)
        held_ws = held and (held.get("ws") or _page_ws(held.get("target_id") or ""))
        held_responds = bool(held and target_responds(held_ws))
        if held and not held_responds:
            # A busy rendered form can miss one cheap probe while processing a real click.
            # Never destroy an in-progress application on that single transient miss.
            time.sleep(0.5)
            held_responds = target_responds(held_ws)
        if held and not held_responds:
            # Dead renderer. Drop the whole context so the next block builds a fresh one;
            # reusing it would fail this lane on every pass until a human noticed.
            try:
                asyncio.run(_calls([(
                    "Target.disposeBrowserContext",
                    {"browserContextId": held.get("context_id")},
                )]))
            except Exception:
                pass
            leases.pop(task, None)
            _save(leases)
            held = None
        if held:  # one task owns one durable fence until release
            changed = False
            if not isinstance(held.get("token"), str):
                held["token"] = secrets.token_hex(16)
                changed = True
            if isinstance(held.get("generation"), bool) or not isinstance(held.get("generation"), int):
                held["generation"] = 1
                changed = True
            held["ts"] = int(time.time())
            # Whoever is calling acquire() right now is the current holder, even if a
            # different (now-dead) process originally created this row -- record its ppid so
            # gc's fast pid-liveness path tracks the real owner, not a crashed predecessor.
            held["pid"] = os.getppid()
            changed = True
            if changed:
                leases[task] = held
                _save(leases)
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

        lease = {
            "context_id": ctx_id,
            "target_id": target_id,
            "ws": _page_ws(target_id),
            "ts": int(time.time()),
            "cookies_seeded": len(cookies),
            "token": secrets.token_hex(16),
            "generation": 1,
            "pid": os.getppid(),
        }
        leases[task] = lease
        _save(leases)
        return {"ok": True, "reused": False, **lease}


def _fence_matches(held, token, generation):
    if token is None and generation is None:  # legacy callers remain supported
        return True
    return token == held.get("token") and generation == held.get("generation")


def heartbeat(task, token=None, generation=None):
    with _ledger_lock():
        leases = _leases()
        held = leases.get(task)
        if not held:
            # The ledger mtime rides inside `reason` because that is the only field
            # callers propagate: application_parent's LeaseHandle raises
            # lease_command_failed:{reason} from the returned JSON, and its stderr is
            # captured but never read. No caller string-matches "lease_not_found"
            # exactly (verified across the accepted callers), so
            # extending the string is safe -- and if any residual clobberer remains,
            # the mtime in the parent-error evidence pinpoints the overwrite.
            try:
                ledger_mtime = os.path.getmtime(_leases_path())
            except OSError:
                ledger_mtime = None
            return {"ok": False, "reason": f"lease_not_found ledger_mtime={ledger_mtime}"}
        if not _fence_matches(held, token, generation):
            return {"ok": False, "reason": "lease_fence_mismatch"}
        held["ts"] = int(time.time())
        held["pid"] = os.getppid()  # same holder proving liveness again; keep pid current
        leases[task] = held
        _save(leases)
        return {
            "ok": True,
            "task": task,
            "token": held.get("token"),
            "generation": held.get("generation"),
            "ts": held["ts"],
        }


def release(task, token=None, generation=None):
    with _ledger_lock():
        leases = _leases()
        held = leases.get(task)
        if not held:
            return {"ok": True, "note": f"{task} held no context"}
        if not _fence_matches(held, token, generation):
            return {"ok": False, "reason": "lease_fence_mismatch"}
        lock_path = _operation_lock_path(held["target_id"])
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with open(lock_path, "a+", encoding="utf-8") as operation_lock:
            fcntl.flock(operation_lock.fileno(), fcntl.LOCK_EX)
            dispose_note = None
            try:
                asyncio.run(_calls([(
                    "Target.disposeBrowserContext",
                    {"browserContextId": held["context_id"]},
                )]))
            except Exception as e:
                # A context whose renderer is wedged cannot be disposed right now, and it
                # is exactly the context the caller most needs to be rid of. Keeping the
                # row would hand the same corpse to every future acquire; gc reaps the
                # browser-side remains once it recovers or restarts. The fence was already
                # checked above -- this never weakens who may release what.
                dispose_note = f"context_left_for_gc: {e}"
            finally:
                fcntl.flock(operation_lock.fileno(), fcntl.LOCK_UN)
        leases.pop(task, None)
        _save(leases)
        result = {"ok": True, "released": task, "context_id": held["context_id"]}
        if dispose_note:
            result["note"] = dispose_note
        return result


def gc(idle_min=45):
    """A loop killed with -9 never releases. Reap whatever it left holding.

    gc used to read+dispose+save without the ledger lock -- the only such path in this
    file. Its dispose calls are slow (real CDP round trips), so any heartbeat()/acquire()
    write landing during that window got silently overwritten by gc's unconditional
    `_save(leases)` of its stale start-of-call snapshot: the victim's next heartbeat then
    returned lease_not_found. Fix: read candidates under the lock, dispose outside it (so
    other callers are not blocked on slow CDP calls), then re-open the lock per row and
    only pop it if the ledger still shows the *same* lease (same context/target id) and it
    is *still* stale -- a concurrent heartbeat or re-acquire between read and finalize
    survives untouched.

    Accepted edge: a 45-min-stale row re-acquired via acquire's reuse path during the
    dispose window survives with a dead context; the next acquire's target_responds
    check detects the corpse and rebuilds it (self-healing, reviewer-accepted).

    Pid-liveness fast path: idle_min alone means a holder killed with -9 can sit in the
    ledger for up to idle_min before this reaps it, even though acquire()/heartbeat()
    already stamp `pid` = the calling process's ppid on every successful call (D4). A row
    whose recorded pid is confirmed dead right now is reaped on this call regardless of
    idle_min -- missing/inconclusive pid (legacy rows, or _pid_alive's ambiguous-signal
    case) never triggers this path, so it only ever narrows the reap window, never widens
    who gets reaped.
    """
    now = time.time()
    with _ledger_lock():
        leases = _leases()
        candidates = {
            task: dict(held)
            for task, held in leases.items()
            if now - held.get("ts", 0) > idle_min * 60
            or _pid_alive(held.get("pid")) is False
        }

    reaped = []
    for task, held in candidates.items():
        try:
            asyncio.run(_calls([("Target.disposeBrowserContext", {"browserContextId": held["context_id"]})]))
        except Exception:
            pass
        with _ledger_lock():
            leases = _leases()
            current = leases.get(task)
            same_lease = (
                current is not None
                and current.get("context_id") == held.get("context_id")
                and current.get("target_id") == held.get("target_id")
            )
            still_stale = same_lease and (
                now - current.get("ts", 0) > idle_min * 60
                or _pid_alive(current.get("pid")) is False
            )
            if still_stale:
                leases.pop(task, None)
                _save(leases)
                reaped.append(task)

    with _ledger_lock():
        still_held = list(_leases())
    return {"ok": True, "reaped": reaped, "still_held": still_held}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        token = sys.argv[sys.argv.index("--token") + 1] if "--token" in sys.argv else None
        generation = int(sys.argv[sys.argv.index("--generation") + 1]) if "--generation" in sys.argv else None
        if cmd == "acquire":
            out = acquire(arg or "unnamed", no_seed="--no-seed" in sys.argv)
        elif cmd == "heartbeat":
            out = heartbeat(arg or "unnamed", token=token, generation=generation)
        elif cmd == "release":
            out = release(arg or "unnamed", token=token, generation=generation)
        elif cmd == "gc":
            idle = int(sys.argv[sys.argv.index("--idle-min") + 1]) if "--idle-min" in sys.argv else 45
            out = gc(idle)
        elif cmd == "list":
            out = {"ok": True, "leases": _leases()}
        else:
            out = {"ok": False, "reason": f"unknown command {cmd}"}
    except Exception as e:
        out = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)
