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
    """parse IG count text → int. Handles 1,234 / 2万 / 1.2万 / 12.3K / 1.2M. Fail-soft: malformed → None (never crash,
    never fabricate). A unit suffix (万/K/M) keeps the decimal; a bare integer with thousands-commas/periods is treated
    as an integer (locale-safe: drop both separators when no unit)."""
    if s is None:
        return None
    s = str(s).strip()
    m = re.search(r"([\d.,]+)\s*(万|億|K|M|k|m)?", s)
    if not m:
        return None
    num, unit = m.group(1), m.group(2)
    try:
        if unit:
            val = float(num.replace(",", ""))          # "1.2万" → 1.2 * 1e4
        else:
            val = float(re.sub(r"[.,]", "", num))      # "1,234"/"1.234" thousands → 1234 (no decimal without a unit)
    except ValueError:
        return None
    return int(val * {"万": 1e4, "億": 1e8, "K": 1e3, "k": 1e3, "M": 1e6, "m": 1e6}.get(unit, 1))


def read_reel_metrics(url, tid, port):
    # use the STANDALONE reel page (singular /reel/) — its og:description meta reliably carries "N likes, M comments"
    surl = re.sub(r"/reels/", "/reel/", url)
    subprocess.run([PYB, CDP, "nav", tid, surl], capture_output=True, env={**os.environ, "CDP_PORT": str(port)})
    import time; time.sleep(5)
    raw = _ev(tid, r"""(()=>{
      const out={desc:null,views:null};
      const og=document.querySelector('meta[property="og:description"]');
      out.desc = og?og.getAttribute('content'):null;          // e.g. "20K likes, 198 comments - user on Instagram: ..."
      // ★ FIND-D1-01: take views ONLY from the reel's OWN counter element (aria-label on a span inside the main
      //   article), NOT page-wide innerText (which mixes in suggested-reel / comment view counts → misattribution).
      //   If no anchored element is found, leave views null (honest) rather than a wrong number. ★
      const main=document.querySelector('main')||document;
      const ve=[...main.querySelectorAll('span,div')].find(e=>{const t=(e.getAttribute&&e.getAttribute('aria-label'))||'';return /(回再生|再生回数|plays|views)/i.test(t)&&/[\d]/.test(t)&&e.getBoundingClientRect().top<400;});
      if(ve){const t=(ve.getAttribute('aria-label')||'');const m=t.match(/([\d.,]+\s*[万億KMkm]?)/);if(m)out.views=m[1];}
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
