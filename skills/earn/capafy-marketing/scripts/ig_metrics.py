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
import json, os, subprocess, sys, time

CDP = os.path.expanduser("~/.agents/skills/ig-account-create/scripts/cdp.py")
PY = "/opt/homebrew/bin/python3"
IGLEDGER = os.path.expanduser("~/.openclaw/state/capafy-marketing-ig-ledger.jsonl")
METRICS = os.path.expanduser("~/.openclaw/state/capafy-marketing-ig-metrics.jsonl")
MARKETING_TERMINAL = os.path.expanduser("~/.openclaw/state/capafy-marketing-terminal.json")

READ_JS = r'''(() => {
  const a=document.querySelector('article'); if(!a) return '{}';
  const num=(s)=>{ if(!s) return 0; s=s.replace(/[,\s]/g,''); const m=s.match(/([\d\.]+)([KMkm]?)/); if(!m) return 0;
    let n=parseFloat(m[1]); if(/[Kk]/.test(m[2]))n*=1000; if(/[Mm]/.test(m[2]))n*=1e6; return Math.round(n); };
  const out={likes:0,comments:0,views:0};
  for (const el of a.querySelectorAll('[aria-label],span,a')){
    const t=(el.getAttribute('aria-label')||el.innerText||'');
    let m;
    if((m=t.match(/([\d,\.KMkm]+)\s*(likes|いいね)/i))) out.likes=Math.max(out.likes,num(m[1]));
    if((m=t.match(/([\d,\.KMkm]+)\s*(comments|コメント)/i))) out.comments=Math.max(out.comments,num(m[1]));
    if((m=t.match(/([\d,\.KMkm]+)\s*(views|plays|回視聴|再生)/i))) out.views=Math.max(out.views,num(m[1]));
  }
  return JSON.stringify(out);
})()'''


def _read(url):
    tid = subprocess.run([PY, CDP, "new", url], capture_output=True, text=True, timeout=60).stdout.strip().strip('"')
    time.sleep(7)
    r = subprocess.run([PY, CDP, "eval", tid, "-"], input=READ_JS, capture_output=True, text=True, timeout=60).stdout.strip().strip('"').replace('\\"', '"')
    subprocess.run([PY, CDP, "close", tid], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r)
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
            reels[outcome["reel_url"]] = {
                "reel_url": outcome["reel_url"],
                "agent_id": outcome.get("agent_id"),
                "listing_name": outcome.get("title"),
            }
    except Exception:
        pass
    if not reels:
        print(json.dumps({"ok": True, "measured": 0, "note": "no reel_url rows yet — no-op"})); return 0
    snapshots = []
    for url, r in reels.items():
        s = _read(url)
        if not isinstance(s, dict) or set(("views", "likes", "comments")) - set(s):
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
