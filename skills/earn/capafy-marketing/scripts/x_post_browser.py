#!/usr/bin/env python3
"""
B5 — Capafy marketing X poster, BROWSER-DIRECT rail (the working one).

Drives the CloakBrowser daily-driver (CDP :9222) to post, as the logged-in X account
(@aniccaen for phase 1), a 2-tweet self-thread:
  tweet 1 (root)  = native value post, NO link
  tweet 2 (reply) = "Try the skill here: <UTM-tagged Capafy URL>"

WHY browser-direct and not Postiz: the Postiz public-API strips every URL from tweet
content (verified live, 5 tests 2026-07-18), so the reply link never reaches X. The
browser compose flow posts the raw link intact — verified logged-out 2026-07-18: the
reply's t.co resolved (no auth) to the Capafy URL with UTM params, HTTP 200.

Proven flow this script reproduces (each step verified manually 2026-07-18):
  compose/post -> click tweetTextarea_0 -> insert root -> click addButton
  -> click tweetTextarea_1 -> insert reply -> click tweetButton (Post all)
  -> read the two /status/ URLs from the profile.

Deterministic TOOL: copy is the agent's input (--tweet), never invented here.
`--dry` fills the thread but does NOT click Post (discards) — proves the flow without posting.
Emits one clean JSON line on stdout. Atomic ledger append.
"""
import argparse, json, os, subprocess, sys, time

CDP = os.path.expanduser("~/.agents/skills/ig-account-create/scripts/cdp.py")
PY = "/opt/homebrew/bin/python3"
LEDGER = os.path.expanduser("~/.openclaw/state/capafy-marketing-x-ledger.jsonl")
UTM = "utm_source=x&utm_medium=x_reply&utm_campaign=capafy_marketing"


def _cdp(*args, want_out=False):
    r = subprocess.run([PY, CDP, *args], capture_output=True, text=True, timeout=60)
    return r.stdout.strip() if want_out else None


def _eval(tid, js):
    r = subprocess.run([PY, CDP, "eval", tid, "-"], input=js, capture_output=True, text=True, timeout=60)
    return r.stdout.strip().strip('"').replace('\\"', '"')


def _rect_xy(tid, selector):
    js = ('(() => { const e=document.querySelector(%s); if(!e) return "NONE"; '
          'const r=e.getBoundingClientRect(); return Math.round(r.x+r.width/2)+" "+Math.round(r.y+r.height/2); })()'
          % json.dumps(selector))
    out = _eval(tid, js)
    if out == "NONE" or not out:
        return None
    x, y = out.split()
    return int(x), int(y)


def _tag(url):
    return f"{url}{'&' if '?' in url else '?'}{UTM}"


def _append_ledger(row):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--tweet", required=True, help="native root tweet, no link, <=280")
    ap.add_argument("--reply", default="Try the skill here:")
    ap.add_argument("--handle", default="aniccaen", help="the logged-in X handle (for URL readback)")
    ap.add_argument("--live", action="store_true", help="click Post. default = dry (fill only, discard)")
    args = ap.parse_args()

    native = args.tweet.strip()
    if "http://" in native or "https://" in native:
        print(json.dumps({"ok": False, "error": "native tweet must not contain a link"})); return 2
    if len(native) > 280:
        print(json.dumps({"ok": False, "error": f"tweet too long ({len(native)})"})); return 2
    tagged = _tag(args.url)
    reply = f"{args.reply.strip()} {tagged}"

    tid = _cdp("new", "https://x.com/compose/post", want_out=True).strip('"')

    # poll for the compose editor (the shared daily-driver can be slow / redirect briefly)
    xy = None
    for _ in range(12):
        time.sleep(2)
        xy = _rect_xy(tid, '[data-testid="tweetTextarea_0"]')
        if xy:
            break
        # if it landed on home instead of the modal, re-navigate to compose
        _cdp("nav", tid, "https://x.com/compose/post")
    if not xy:
        print(json.dumps({"ok": False, "error": "compose editor not found after 24s"})); return 1
    _cdp("clickxy", tid, str(xy[0]), str(xy[1])); time.sleep(0.6)
    _cdp("insert", tid, native); time.sleep(1.2)

    # add 2nd tweet
    add = _rect_xy(tid, '[data-testid="addButton"]')
    if not add:
        print(json.dumps({"ok": False, "error": "add-tweet button not found (root may not have registered)"})); return 1
    _cdp("clickxy", tid, str(add[0]), str(add[1])); time.sleep(1.2)
    xy1 = _rect_xy(tid, '[data-testid="tweetTextarea_1"]')
    _cdp("clickxy", tid, str(xy1[0]), str(xy1[1])); time.sleep(0.6)
    _cdp("insert", tid, reply); time.sleep(1.2)

    # verify both before posting
    chk = _eval(tid, '(() => { const e0=document.querySelector(\'[data-testid="tweetTextarea_0"]\'); '
                     'const e1=document.querySelector(\'[data-testid="tweetTextarea_1"]\'); '
                     'return JSON.stringify({rootLen:(e0?e0.innerText:"").length, rootLink:/https?:\\/\\//.test(e0?e0.innerText:""), '
                     'replyCapafy:/capafy/.test(e1?e1.innerText:"")}); })()')
    try:
        chkj = json.loads(chk)
    except Exception:
        chkj = {}
    if chkj.get("rootLink") or not chkj.get("replyCapafy"):
        print(json.dumps({"ok": False, "error": "pre-post check failed", "check": chkj})); return 1

    if not args.live:
        print(json.dumps({"ok": True, "mode": "dry", "check": chkj, "note": "filled, not posted (discarded)"}))
        return 0

    # post all
    pxy = _rect_xy(tid, '[data-testid="tweetButton"]')
    _cdp("clickxy", tid, str(pxy[0]), str(pxy[1])); time.sleep(9)

    # read back the two newest /status/ urls from the profile
    _cdp("nav", tid, f"https://x.com/{args.handle}"); time.sleep(7)
    urls = _eval(tid, '(() => { const hs=[...document.querySelectorAll(\'article a[href*="/status/"]\')]'
                      '.map(a=>a.getAttribute("href")).filter(h=>/\\/status\\/\\d+$/.test(h)); '
                      'return JSON.stringify([...new Set(hs)].slice(0,2)); })()')
    try:
        u = json.loads(urls)
    except Exception:
        u = []
    root_url = ("https://x.com" + u[0]) if len(u) > 0 else None
    reply_url = ("https://x.com" + u[1]) if len(u) > 1 else None
    row = {"ts": int(time.time()), "mode": "live_browser", "account": args.handle,
           "listing_url": args.url, "tagged_url": tagged, "root_url": root_url, "reply_url": reply_url}
    _append_ledger(row)
    print(json.dumps({"ok": True, **row}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
