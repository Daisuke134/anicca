#!/usr/bin/env python3
"""warm_step.py — deterministic WARM step for clip_pass.sh (bookkeeping only, no LLM judgment;
per building-agents: this is pure counting/subprocess-dispatch, not a place for model judgment).

For every account with status=="warming" in clip-accounts.json:
  1. Record started_warming (once) — backfilled from the account's real
     ~/.cloak/ig-warmup-<handle>.json log if one already exists, else today. Never invented.
  2. If the account's CDP browser is reachable on its port, run ig-account-warmer's warm.py
     once (warm.py itself is idempotent — it no-ops if already warmed today). If the browser
     is down, DO NOT attempt to warm (no browser = no session) — log a WARN and skip.
  3. Promote warming -> ready when BOTH: >=3 days elapsed since started_warming AND
     >=3 successful warm.py log entries exist. Dais 2026-07-15 instruction sets this 3-day
     floor; ig-account-warmer's SKILL.md recommends 7 days as the safer default — the 3-day
     floor is used here per explicit instruction, and the tradeoff is recorded in the note.
     Promotion is based on ACCUMULATED history, not on whether warm.py ran THIS pass — an
     account that already cleared the bar promotes even on a pass where its browser is down.

Safety: backs up clip-accounts.json before any mutation, edits ONLY the touched account
objects in place (never drops/reorders/duplicates other entries), and verifies the row
count is unchanged both in-memory and after re-reading the written file before keeping it
(state-cleanup rule: never drop rows, backup -> in-place -> verify count).

Usage: warm_step.py [path-to-clip-accounts.json]   (defaults to ~/.cloak/clip-accounts.json)
"""
import sys, os, json, subprocess, shutil, datetime, time, urllib.request

WARM_PY = os.path.expanduser("~/.claude/skills/ig-account-warmer/scripts/warm.py")
PY = "/opt/homebrew/bin/python3"
PROMOTE_DAYS = 3
PROMOTE_RUNS = 3


def warmup_log(handle):
    p = os.path.expanduser(f"~/.cloak/ig-warmup-{handle}.json")
    try:
        d = json.load(open(p))
        dates = sorted(r.get("date") for r in d.get("log", []) if r.get("date"))
        return len(dates), dates
    except Exception:
        return 0, []


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


def main():
    accts_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.cloak/clip-accounts.json")
    try:
        accts = json.load(open(accts_path))
    except Exception as e:
        print(f"WARM: cannot read {accts_path}: {e}")
        return 1
    n_before = len(accts)
    today = datetime.date.today()
    changed = False

    for a in accts:
        if a.get("status") != "warming":
            continue
        handle = a.get("handle")
        port = a.get("port")

        if not a.get("started_warming"):
            _, dates = warmup_log(handle)
            started = dates[0] if dates else today.isoformat()
            a["started_warming"] = started
            changed = True
            print(f"WARM {handle}: recorded started_warming={started}")
        started = datetime.date.fromisoformat(a["started_warming"])

        if browser_up(port):
            try:
                r = subprocess.run(
                    [PY, WARM_PY, handle],
                    env={**os.environ, "CDP_PORT": str(port)},
                    capture_output=True, text=True, timeout=600,
                )
                out = (r.stdout or "").strip()
                append_warmlog(handle, {"action": "warm_run", "rc": r.returncode, "out": out[:500]})
                print(f"WARM {handle}: warm.py rc={r.returncode} out={out[:200]}")
            except Exception as e:
                append_warmlog(handle, {"action": "warm_run_error", "error": repr(e)[:200]})
                print(f"WARM {handle}: warm.py FAILED {e!r}")
        else:
            append_warmlog(handle, {"action": "skip_browser_down", "port": port})
            print(f"WARM {handle}: WARN browser down on :{port} -- skip warm.py this pass")

        days_elapsed = (today - started).days
        run_count, _ = warmup_log(handle)
        if days_elapsed >= PROMOTE_DAYS and run_count >= PROMOTE_RUNS:
            prior_note = (a.get("note") or "")[:300]
            a["status"] = "ready"
            a["note"] = (
                f"{today.isoformat()} warm_step.py: PROMOTED warming->ready "
                f"({days_elapsed}d since started_warming={a['started_warming']}, "
                f"{run_count} warm.py log entries >= {PROMOTE_DAYS}d/{PROMOTE_RUNS}run floor "
                f"per Dais 2026-07-15 instruction; ig-account-warmer SKILL.md recommends 7d "
                f"but Dais's 3-day floor takes precedence here). prior note: {prior_note}"
            )
            changed = True
            print(f"WARM {handle}: PROMOTED to ready ({days_elapsed}d, {run_count} runs)")
            append_warmlog(handle, {"action": "promoted", "days_elapsed": days_elapsed, "run_count": run_count})

    if not changed:
        print("WARM: no changes this pass")
        return 0

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

    # verify by re-reading the file we just wrote
    written = json.load(open(accts_path))
    if len(written) != n_before:
        print(f"WARM: POST-WRITE row count mismatch ({len(written)} != {n_before}) -- restoring backup")
        shutil.copyfile(bak, accts_path)
        return 1
    print(f"WARM: wrote {accts_path} ({len(written)} rows, backup={bak})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
