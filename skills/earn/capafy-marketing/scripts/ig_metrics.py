#!/usr/bin/env python3
"""
B6 (IG variant) — Instagram Reel metrics (deterministic TOOL, browser-direct read).

IG sibling of x_metrics.py. For each Capafy marketing Reel in the IG ledger, opens its
permalink on the CloakBrowser daily-driver (:9222, @useclaudeskills) and reads the PUBLIC
engagement IG renders (likes / comments; views/plays when shown). Appends a dated snapshot
to `capafy-marketing-ig-metrics.jsonl`. Empty ledger (no verified Reels yet) = clean no-op.

IG attribution is handled separately by pull_attribution.py, which pulls the landing redirect
counter after this metrics pass and joins it to the Capafy sales snapshot.
"""
import json, os, re, subprocess, sys, time

CDP = os.path.expanduser("~/.agents/skills/ig-account-create/scripts/cdp.py")
PY = "/opt/homebrew/bin/python3"
IGLEDGER = os.path.expanduser("~/.openclaw/state/capafy-marketing-ig-ledger.jsonl")
METRICS = os.path.expanduser("~/.openclaw/state/capafy-marketing-ig-metrics.jsonl")
MARKETING_TERMINAL = os.path.expanduser("~/.openclaw/state/capafy-marketing-terminal.json")
ACCOUNTS = os.path.expanduser("~/.cloak/clip-accounts-capafy.json")

def _parse_count(value):
    match = re.search(r"([\d,.]+)\s*(万|億|K|M|k|m)?", str(value or ""))
    if not match:
        return None
    number, unit = match.groups()
    try:
        base = float(number.replace(",", "")) if unit else float(re.sub(r"[,.]", "", number))
    except ValueError:
        return None
    return int(base * {"万": 1e4, "億": 1e8, "K": 1e3, "k": 1e3, "M": 1e6, "m": 1e6}.get(unit, 1))


def _resolve_port(handle):
    try:
        rows = json.load(open(ACCOUNTS))
    except Exception:
        return 9222
    matches = [
        row for row in rows
        if row.get("handle") == handle and row.get("session_owner") == "browser"
        and int(row.get("port") or 0) > 0
    ]
    return int(matches[-1]["port"]) if matches else 9222


def _read(url, handle, port):
    code_match = re.search(r"/(?:reel|reels)/([^/?#]+)", url)
    if not code_match or not handle:
        return {}
    code = code_match.group(1)
    profile_url = f"https://www.instagram.com/{handle}/reels/"
    env = {**os.environ, "CDP_PORT": str(port)}
    tid = subprocess.run([PY, CDP, "new", profile_url], capture_output=True, text=True, timeout=60, env=env).stdout.strip().strip('"')
    if not tid:
        return {}
    time.sleep(7)
    expression = """(()=>{const code=%s;const links=[...document.querySelectorAll('a[href*="/reel/"]')];const a=links.find(x=>x.href.includes('/reel/'+code+'/'));return JSON.stringify({found:!!a,text:a?(a.innerText||a.textContent||''):''});})()""" % json.dumps(code)
    raw = subprocess.run([PY, CDP, "eval", tid, "-"], input=expression, capture_output=True, text=True, timeout=60, env=env).stdout.strip()
    subprocess.run([PY, CDP, "close", tid], capture_output=True, text=True, timeout=30, env=env)
    try:
        value = json.loads(raw)
        if isinstance(value, str):
            value = json.loads(value)
        views = _parse_count(value.get("text")) if isinstance(value, dict) and value.get("found") else None
        if views is None:
            return {}
        return {"views": views, "likes": None, "comments": None}
    except Exception:
        return {}


def main():
    reels = {}
    if os.path.exists(IGLEDGER):
        for line in open(IGLEDGER):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("reel_url"):
                reels[r["reel_url"]] = r
    try:
        terminal = json.load(open(MARKETING_TERMINAL))
        outcome = terminal.get("outcome") or {}
        if (
            str(terminal.get("telegram_message_id") or "").isdigit()
            and outcome.get("kind") == "marketing_published"
            and outcome.get("owner_session_verified") is True
            and outcome.get("reel_url")
        ):
            handle = outcome.get("handle")
            reels = {outcome["reel_url"]: {
                "reel_url": outcome["reel_url"],
                "agent_id": outcome.get("agent_id"),
                "listing_name": outcome.get("title"),
                "handle": handle,
                "port": _resolve_port(handle),
            }}
    except Exception:
        pass
    if not reels:
        print(json.dumps({"ok": True, "measured": 0, "note": "no reel_url rows yet — no-op"})); return 0
    snapshots = []
    for url, r in reels.items():
        handle = r.get("handle") or r.get("account")
        port = int(r.get("port") or _resolve_port(handle))
        s = _read(url, handle, port)
        values = [s.get(field) for field in ("views", "likes", "comments")] if isinstance(s, dict) else []
        if not isinstance(s, dict) or set(("views", "likes", "comments")) - set(s) or not any(
            isinstance(value, int) and value >= 0 for value in values
        ):
            print(
                json.dumps({"ok": False, "error": f"browser metrics read failed for {url}"}),
                file=sys.stderr,
            )
            return 1
        row = {"ts": int(time.time()), "reel_url": url, "agent_id": r.get("agent_id"),
               "listing_name": r.get("listing_name"), **{k: s.get(k, 0) for k in ("views", "likes", "comments")}}
        snapshots.append(row)
    os.makedirs(os.path.dirname(METRICS), exist_ok=True)
    for row in snapshots:
        with open(METRICS, "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({"snapshot": row}, ensure_ascii=False))
    event_sync = os.environ.get(
        "CAPAFY_EVENT_SYNC", os.path.join(os.path.dirname(__file__), "capafy_event_sync.py")
    )
    command = [
        sys.executable,
        event_sync,
        "sync-metrics",
        "--metrics-ledger",
        METRICS,
        "--ledger",
        os.environ.get(
            "CAPAFY_EVENT_LEDGER",
            os.path.expanduser("~/.openclaw/state/capafy-revenue-events.jsonl"),
        ),
        "--evidence-dir",
        os.environ.get(
            "CAPAFY_EVENT_EVIDENCE_DIR",
            os.path.expanduser("~/.openclaw/state/capafy-revenue-evidence"),
        ),
    ]
    synced = subprocess.run(command, capture_output=True, text=True, check=False)
    if synced.returncode != 0:
        print(
            json.dumps(
                {"ok": False, "error": f"event sync failed rc={synced.returncode}: {synced.stderr.strip()}"}
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"ok": True, "measured": len(snapshots)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
