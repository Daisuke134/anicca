#!/usr/bin/env python3
"""
B6 — X thread metrics (deterministic TOOL, browser-direct read).

For each Capafy marketing thread in the X ledger, open its root tweet on the CloakBrowser
daily-driver (:9222, @aniccaen logged in) and read the PUBLIC engagement numbers X renders
on the tweet (views / replies / reposts / likes / bookmarks — pulled from the button
aria-labels, which carry the exact counts). Appends one dated snapshot per thread to
`capafy-marketing-metrics.jsonl` so the reflect stage (7+ posts) can learn which copy won.

No login, no analytics scope needed — the numbers are on the public tweet. Honest: if a
number is not rendered yet (fresh post), it records 0 rather than guessing.
"""
import json, os, re, subprocess, sys, time

CDP = os.path.expanduser("~/.agents/skills/ig-account-create/scripts/cdp.py")
PY = "/opt/homebrew/bin/python3"
XLEDGER = os.path.expanduser("~/.openclaw/state/capafy-marketing-x-ledger.jsonl")
METRICS = os.path.expanduser("~/.openclaw/state/capafy-marketing-metrics.jsonl")

READ_JS = r'''(() => {
  const a=document.querySelector('article'); if(!a) return '{}';
  const out={};
  // X puts exact counts in the aria-labels of the action buttons + the views link
  const grab=(re)=>{
    for (const el of a.querySelectorAll('[aria-label]')){
      const m=(el.getAttribute('aria-label')||'').match(re);
      if(m) return parseInt(m[1].replace(/[,\.]/g,''))||0;
    }
    return 0;
  };
  out.replies  = grab(/([\d,\.]+)\s+repl/i);
  out.reposts  = grab(/([\d,\.]+)\s+(repost|retweet)/i);
  out.likes    = grab(/([\d,\.]+)\s+like/i);
  out.bookmarks= grab(/([\d,\.]+)\s+bookmark/i);
  out.views    = grab(/([\d,\.]+)\s+view/i);
  return JSON.stringify(out);
})()'''


def _read_stats(url):
    tid = subprocess.run([PY, CDP, "new", url], capture_output=True, text=True, timeout=60).stdout.strip().strip('"')
    time.sleep(7)
    r = subprocess.run([PY, CDP, "eval", tid, "-"], input=READ_JS, capture_output=True, text=True, timeout=60).stdout.strip().strip('"').replace('\\"', '"')
    subprocess.run([PY, CDP, "close", tid], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r)
    except Exception:
        return {}


def main():
    if not os.path.exists(XLEDGER):
        print(json.dumps({"ok": True, "measured": 0, "note": "no x-ledger yet"})); return 0
    threads = {}
    for line in open(XLEDGER):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("mode") == "live_browser" and r.get("root_url"):
            threads[r["root_url"]] = r  # latest row per root_url
    measured = 0
    os.makedirs(os.path.dirname(METRICS), exist_ok=True)
    for url, r in threads.items():
        stats = _read_stats(url)
        row = {"ts": int(time.time()), "root_url": url, "agent_id": r.get("agent_id"),
               "listing_name": r.get("listing_name"), **{k: stats.get(k, 0) for k in
               ("views", "replies", "reposts", "likes", "bookmarks")}}
        with open(METRICS, "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        measured += 1
        print(json.dumps({"snapshot": row}, ensure_ascii=False))
    print(json.dumps({"ok": True, "measured": measured}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
