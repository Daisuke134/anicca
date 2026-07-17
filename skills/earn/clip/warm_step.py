#!/usr/bin/env python3
"""warm_step.py — deterministic WARM step for clip_pass.sh (bookkeeping + subprocess dispatch
only, no LLM judgment; per building-agents this is mechanical, not a place for model judgment).

Per pass, picks the SINGLE OLDEST warming account (earliest started_warming -- backfilled from
its own ~/.cloak/ig-warmup-<handle>.json log history the first time it's seen) and, serially:
  1. Ensures that ONE account's isolated CloakBrowser is up + logged in via
     ig-account-warmer's ensure_warmup_browser.py (idempotent launcher: starts the browser on
     the account's OWN port/profile if it's down, logs in with ~/.cloak/ig-<handle>.json creds,
     no-ops if already up+logged in). Needs creds + a profile dir -- WARNs and skips the whole
     account this pass if either is missing (never guesses a profile/port).
  2. Runs warm.py once (CDP_PORT=<port>) if the browser ended up reachable -- warm.py itself is
     idempotent (no-ops if already warmed today).
  3. Reads the account's warmup state back and decides:
       - a ban signal anywhere in the log/aborts history -> status: investigating + WARN (never
         auto-promote a banned account).
       - day >= 3 (the LAST successful run's own recorded "day", not a recomputed calendar
         guess) and not banned -> status: ready. Dais 2026-07-15 sets this 3-day floor;
         ig-account-warmer's SKILL.md recommends 7 days as the safer default -- the 3-day floor
         is used here per explicit instruction (can be extended later), and the tradeoff is
         recorded in the promotion note every time.
Only ONE account is touched per pass (deliberately serial -- keeps resource use minimal and
each promotion decision individually auditable) and only accounts with status=="warming" are
ever touched -- a live "ready" posting account's browser (e.g. the daily-driver-adjacent
aiclipsvault instance) is never started/stopped/touched by this script.

Safety: clip-accounts.json edits are backup -> in-place (edit only the touched account object,
never drop/reorder/duplicate rows) -> row-count-verified before AND after the write.

Usage: warm_step.py [path-to-clip-accounts.json]   (defaults to ~/.cloak/clip-accounts.json)
"""
import sys, os, json, subprocess, shutil, datetime, time, urllib.request

ENSURE_PY = os.path.expanduser("~/.claude/skills/ig-account-warmer/scripts/ensure_warmup_browser.py")
WARM_PY = os.path.expanduser("~/.claude/skills/ig-account-warmer/scripts/warm.py")
PY = "/opt/homebrew/bin/python3"
PROMOTE_DAY = 3


def load_warmup_state(handle):
    p = os.path.expanduser(f"~/.cloak/ig-warmup-{handle}.json")
    try:
        return json.load(open(p))
    except Exception:
        return {"handle": handle, "log": []}


def state_summary(st):
    """day = the last successful run's own recorded day (honest: what was actually reached,
    not a recomputed calendar guess). banned = any log/abort entry ever showed a ban signal."""
    log = st.get("log", [])
    aborts = st.get("aborts", [])
    day = log[-1].get("day", 0) if log else 0
    banned = any(
        e.get("ban") is True or e.get("ban_signal")
        or (isinstance(e.get("ABORT"), str) and "ban" in e["ABORT"].lower())
        for e in (log + aborts)
    )
    dates = sorted(r.get("date") for r in log if r.get("date"))
    return day, banned, (dates[0] if dates else None)


def recent_abort_after_last_log(st):
    """True if the most recent aborts entry (a login failure) is dated AFTER the most
    recent log entry (a successful day). Guards against promoting off a stale
    log[-1].day when the account has actually failed to log in since that success --
    the real bug: state_summary()'s day/banned alone missed this because a plain
    'not logged in' abort never sets a ban signal. Compares by 'date' (fallback to
    'day' if a date is missing on either side)."""
    log = st.get("log", [])
    aborts = st.get("aborts", [])
    if not aborts:
        return False
    if not log:
        return True  # only failures ever recorded, nothing successful to promote on
    last_log, last_abort = log[-1], aborts[-1]
    log_date, abort_date = last_log.get("date"), last_abort.get("date")
    if log_date and abort_date:
        return abort_date > log_date
    return last_abort.get("day", 0) > last_log.get("day", 0)


def browser_up(port, timeout=4):
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/json/list", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def append_warmlog(handle, entry):
    p = os.path.expanduser(f"~/.cloak/warmlog-{handle}.jsonl")
    entry = dict(entry, ts=int(time.time()), date=datetime.date.today().isoformat())
    with open(p, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def pick_target(accts):
    """The single oldest warming account this pass. started_warming is backfilled (once) from
    the account's own log history when missing, then the earliest started_warming wins; a tie
    falls back to list order (deterministic, no randomness)."""
    warming = [a for a in accts if a.get("status") == "warming"]
    changed = False
    for a in warming:
        if not a.get("started_warming"):
            _, _, first_date = state_summary(load_warmup_state(a.get("handle")))
            a["started_warming"] = first_date or datetime.date.today().isoformat()
            changed = True
            print(f"WARM {a.get('handle')}: recorded started_warming={a['started_warming']}")
    warming.sort(key=lambda a: a["started_warming"])
    return (warming[0] if warming else None), changed


def _write(accts_path, accts, n_before):
    n_after = len(accts)
    if n_after != n_before:
        print(f"WARM: ABORT -- in-memory row count changed {n_before}->{n_after}, not writing")
        return 1
    bak = accts_path + f".bak-{int(time.time())}"
    shutil.copyfile(accts_path, bak)
    tmp = accts_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(accts, f, ensure_ascii=False, indent=2)
    os.replace(tmp, accts_path)
    written = json.load(open(accts_path))
    if len(written) != n_before:
        print(f"WARM: POST-WRITE row count mismatch ({len(written)} != {n_before}) -- restoring backup")
        shutil.copyfile(bak, accts_path)
        return 1
    print(f"WARM: wrote {accts_path} ({len(written)} rows, backup={bak})")
    return 0


def main():
    accts_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.cloak/clip-accounts.json")
    try:
        accts = json.load(open(accts_path))
    except Exception as e:
        print(f"WARM: cannot read {accts_path}: {e}")
        return 1
    n_before = len(accts)

    target, changed = pick_target(accts)
    if not target:
        print("WARM: no warming accounts this pass")
        return _write(accts_path, accts, n_before) if changed else 0

    handle, port, profile = target["handle"], target.get("port"), target.get("profile")
    print(f"WARM: target this pass = {handle} (started_warming={target.get('started_warming')})")

    if not browser_up(port):
        creds = os.path.expanduser(f"~/.cloak/ig-{handle}.json")
        if not os.path.exists(creds) or not profile:
            append_warmlog(handle, {"action": "skip_no_creds_or_profile", "port": port})
            print(f"WARM {handle}: WARN browser down on :{port} and no creds/profile to launch it -- skip")
        else:
            profdir = os.path.expanduser(f"~/.cloak/profiles/{profile}")
            try:
                r = subprocess.run(
                    [PY, ENSURE_PY, "--handle", handle, "--port", str(port), "--profile", profdir, "--creds", creds],
                    capture_output=True, text=True, timeout=300,
                )
                out = (r.stdout or "").strip()
                append_warmlog(handle, {"action": "ensure_browser", "rc": r.returncode, "out": out[:300]})
                print(f"WARM {handle}: ensure_warmup_browser rc={r.returncode} out={out[:200]!r}")
            except Exception as e:
                append_warmlog(handle, {"action": "ensure_browser_error", "error": repr(e)[:200]})
                print(f"WARM {handle}: ensure_warmup_browser FAILED {e!r}")

    if browser_up(port):
        try:
            r = subprocess.run(
                [PY, WARM_PY, handle],
                env={**os.environ, "CDP_PORT": str(port)},
                capture_output=True, text=True, timeout=600,
            )
            out = (r.stdout or "").strip()
            append_warmlog(handle, {"action": "warm_run", "rc": r.returncode, "out": out[:500]})
            print(f"WARM {handle}: warm.py rc={r.returncode} out={out[:300]}")
        except Exception as e:
            append_warmlog(handle, {"action": "warm_run_error", "error": repr(e)[:200]})
            print(f"WARM {handle}: warm.py FAILED {e!r}")
    else:
        append_warmlog(handle, {"action": "skip_browser_still_down", "port": port})
        print(f"WARM {handle}: WARN browser still down on :{port} after launch attempt -- warm.py not run")

    warmup_state = load_warmup_state(handle)
    day, banned, _ = state_summary(warmup_state)
    recent_failure = recent_abort_after_last_log(warmup_state)
    for a in accts:
        if a.get("handle") != handle:
            continue
        if banned:
            a["status"] = "investigating"
            a["note"] = (
                f"{datetime.date.today().isoformat()} warm_step.py: WARN ban signal detected in "
                f"warmup log -- moved warming->investigating (day={day})."
            )
            changed = True
            print(f"WARM {handle}: BAN SIGNAL -- moved to investigating")
            append_warmlog(handle, {"action": "ban_detected", "day": day})
        elif recent_failure:
            print(f"WARM {handle}: HELD (day={day} >= {PROMOTE_DAY} but a login abort was "
                  f"recorded after the last successful log day -- not promoting)")
            append_warmlog(handle, {"action": "held_recent_abort", "day": day})
        elif day >= PROMOTE_DAY:
            prior_note = (a.get("note") or "")[:300]
            a["status"] = "ready"
            a["note"] = (
                f"{datetime.date.today().isoformat()} warm_step.py: PROMOTED warming->ready "
                f"(day={day} >= {PROMOTE_DAY}d floor per Dais 2026-07-15 instruction; "
                f"ig-account-warmer SKILL.md recommends 7d but Dais's 3-day floor takes "
                f"precedence -- can extend later). prior note: {prior_note}"
            )
            changed = True
            print(f"WARM {handle}: PROMOTED to ready (day={day})")
            append_warmlog(handle, {"action": "promoted", "day": day})
        else:
            print(f"WARM {handle}: not yet promotable (day={day} < {PROMOTE_DAY})")
        break

    return _write(accts_path, accts, n_before) if changed else (print("WARM: no changes this pass") or 0)


if __name__ == "__main__":
    sys.exit(main())
