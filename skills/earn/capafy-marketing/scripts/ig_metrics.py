#!/usr/bin/env python3
"""
B6 (IG variant) — Instagram Reel metrics (deterministic TOOL, browser-direct read).

IG sibling of x_metrics.py. For each Capafy marketing Reel in the IG ledger, opens its
permalink on the CloakBrowser daily-driver (:9222, @useclaudeskills) and reads the PUBLIC
engagement IG renders (likes / comments; views/plays when shown). Appends a dated snapshot
to `capafy-marketing-ig-metrics.jsonl`. Empty ledger (no Reels yet — account still warming)
= clean no-op.

IG attribution is handled separately by pull_attribution.py, which pulls the landing redirect
counter after this metrics pass and joins it to the Capafy sales snapshot.
"""
import json, os, subprocess, sys, time

CDP = os.path.expanduser("~/.agents/skills/ig-account-create/scripts/cdp.py")
PY = "/opt/homebrew/bin/python3"
IGLEDGER = os.path.expanduser("~/.local/state/life-manager/state/capafy-marketing-ig-ledger.jsonl")
METRICS = os.path.expanduser("~/.local/state/life-manager/state/capafy-marketing-ig-metrics.jsonl")

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
    if not os.path.exists(IGLEDGER):
        print(json.dumps({"ok": True, "measured": 0, "note": "no IG Reels yet (account warming) — no-op"})); return 0
    reels = {}
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
    if not reels:
        print(json.dumps({"ok": True, "measured": 0, "note": "no reel_url rows yet — no-op"})); return 0
    os.makedirs(os.path.dirname(METRICS), exist_ok=True)
    measured = 0
    for url, r in reels.items():
        s = _read(url)
        row = {"ts": int(time.time()), "reel_url": url, "agent_id": r.get("agent_id"),
               "listing_name": r.get("listing_name"), **{k: s.get(k, 0) for k in ("views", "likes", "comments")}}
        with open(METRICS, "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        measured += 1
        print(json.dumps({"snapshot": row}, ensure_ascii=False))
    print(json.dumps({"ok": True, "measured": measured}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
