#!/usr/bin/env python3
"""metrics.py — read a posted reel's REAL engagement (views / likes / comments) from Instagram via CDP, so the
self-improving eval loop can measure what works. The ULTIMATE metric is money (USDC, see onchain.py); views +
engagement are the LEADING indicators the agent uses to iterate the script before money data accrues.

read_reel_metrics(url, tid, port) → {url, views, likes, comments, ok}. Fail-soft: missing fields → None (never
fabricate a number). Pure-ish: drives the existing cdp.py against a logged-in tab; no judgment here (the agent
decides how to improve — AI-agnostic). CLI: metrics.py <reel_url> [--tid T] [--port P] [--handle H] appends to
the content-state so the agent can read performance history.
"""
import argparse, json, os, re, subprocess

CDP = os.path.expanduser("~/.claude/skills/ig-account-create/scripts/cdp.py")
PYB = "/opt/homebrew/bin/python3"


def _ev(tid, js, port):
    open("/tmp/_metrics.js", "w").write(js)
    env = {**os.environ, "CDP_PORT": str(port)}
    o = subprocess.run([PYB, CDP, "eval", tid, "/tmp/_metrics.js"], capture_output=True, text=True, env=env).stdout.strip()
    v = o
    for _ in range(2):
        if isinstance(v, str):
            try: v = json.loads(v)
            except Exception: break
    return v


def _num(s):
    """parse IG count text → int. Handles 1,234 / 2万 / 1.2万 / 12.3K / 1.2M."""
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    m = re.search(r"([\d.]+)\s*(万|億|K|M|k|m)?", s)
    if not m:
        return None
    n = float(m.group(1)); unit = m.group(2)
    return int(n * {"万": 1e4, "億": 1e8, "K": 1e3, "k": 1e3, "M": 1e6, "m": 1e6}.get(unit, 1))


def read_reel_metrics(url, tid, port):
    # use the STANDALONE reel page (singular /reel/) — its og:description meta reliably carries "N likes, M comments"
    surl = re.sub(r"/reels/", "/reel/", url)
    subprocess.run([PYB, CDP, "nav", tid, surl], capture_output=True, env={**os.environ, "CDP_PORT": str(port)})
    import time; time.sleep(5)
    raw = _ev(tid, r"""(()=>{
      const out={likes:null,comments:null,views:null,desc:null};
      const og=document.querySelector('meta[property="og:description"]');
      out.desc = og?og.getAttribute('content'):null;          // e.g. "20K likes, 198 comments - user on Instagram: ..."
      // owner/standalone view sometimes exposes a "N回再生 / N views / N plays" line in the body
      const body=document.body.innerText||'';
      const vm=body.match(/([\d.,]+\s*[万億KMkm]?)\s*(回再生|回視聴|plays|views)/i)||body.match(/(再生回数|視聴回数|Views|Plays)[\s:]*([\d.,]+\s*[万億KMkm]?)/i);
      if(vm) out.views = (vm[2]&&/[\d]/.test(vm[2]))? vm[2] : vm[1];
      return JSON.stringify(out);
    })()""", port)
    d = raw if isinstance(raw, dict) else {}
    likes = comments = None
    desc = d.get("desc") or ""
    lm = re.search(r"([\d.,]+\s*[万億KMkm]?)\s*(?:likes?|いいね)", desc, re.I)
    cm = re.search(r"([\d.,]+\s*[万億KMkm]?)\s*(?:comments?|コメント)", desc, re.I)
    if lm: likes = lm.group(1)
    if cm: comments = cm.group(1)
    return {
        "url": url,
        "views": _num(d.get("views")),
        "likes": _num(likes),
        "comments": _num(comments),
        "og_desc": (desc[:120] or None),
        "ok": any(x is not None for x in (_num(d.get("views")), _num(likes), _num(comments))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--tid", required=True)
    ap.add_argument("--port", default="9334")
    ap.add_argument("--handle", default="money_blueprintdaily")
    ap.add_argument("--date", default="")   # measurement date (caller passes; no Date.now in scripts)
    a = ap.parse_args()
    m = read_reel_metrics(a.url, a.tid, a.port)
    m["measured_date"] = a.date
    # append to the per-handle content-state metrics history (the agent reads this to iterate)
    cs = os.path.expanduser(f"~/.cloak/earn-video-metrics-{a.handle}.jsonl")
    with open(cs, "a") as f:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(json.dumps(m, ensure_ascii=False))


if __name__ == "__main__":
    main()
