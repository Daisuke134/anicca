#!/usr/bin/env python3
"""cdp_snapshot.py — trajectory capture for the gig browser-use loop (BP: docs/loop-engineering/25).

Captures a screenshot + page state of the CURRENT :9222 page tab and appends one trajectory row,
so the report-skeptical reality-verifier (gig_judge, copied from browser-use/benchmark/judge.py) can
later judge from the SCREENSHOT+final-state — not from the core's self-reported jsonl.

The core calls this RIGHT AFTER each key browser action (出品 create/edit submit, 応募 submit,
納品 submit, 返信 send) so the captured page reflects the post-action state (screenshot is the
source of truth — Browserbase: "just record what was on the screen").

Usage:
  python3 cdp_snapshot.py <pass_id> <seq> <label> [action_note]
    e.g. python3 cdp_snapshot.py 1782940000 03 shuppin_submit "created service AI資料作成"

Writes:
  ~/gig/trajectory/<pass_id>/<seq>-<label>.png
  appends {ts,pass_id,seq,label,url,title,action} to ~/gig/trajectory/<pass_id>/trajectory.jsonl
Prints the png path on success, or ERROR:<reason> on failure (never raises — capture must never
abort a pass).
"""
import asyncio, base64, json, os, sys, subprocess, time, urllib.request
from urllib.parse import urlparse

try:
    import websockets
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "websockets", "-q"], capture_output=True)
    import websockets

def _cdp_base():
    # No silent default. The old fallback was http://127.0.0.1:9222, which on this host
    # is a proxy onto the SAME browser as gig production :9223 -- the 2026-07-26
    # collision. Whenever the env is set (gig_pass.sh exports :9223) nothing changes;
    # when it is missing we now fail loudly instead of quietly attaching to whatever
    # answers on the interactive port.
    base = os.environ.get("CLOAK_CDP_BASE_URL")
    if not base:
        raise RuntimeError(
            "CLOAK_CDP_BASE_URL is unset. Lease a browser first: "
            "~/.config/ai/bin/browser-guard.sh acquire <identity> "
            "(identities in ~/.config/ai/registry/browsers.toml). "
            "Refusing to guess a CDP port."
        )
    return base.rstrip("/")


def get_tab():
    data = json.loads(
        urllib.request.urlopen(f"{_cdp_base()}/json/list", timeout=8).read()
    )
    # prefer a coconala page tab; else the first page tab
    pages = [t for t in data if t.get("type") == "page"]
    for t in pages:
        if "coconala.com" in (t.get("url") or ""):
            return t["id"]
    if pages:
        return pages[0]["id"]
    raise RuntimeError("no page tab on :9222")


async def _connect():
    tab = get_tab()
    return await websockets.connect(
        f"ws://{urlparse(_cdp_base()).netloc}/devtools/page/{tab}",
        ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024,
    )


async def _call(ws, method, params, cid):
    await ws.send(json.dumps({"id": cid, "method": method, "params": params}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=25)
        d = json.loads(raw)
        if d.get("id") == cid:
            return d


async def snapshot(pass_id, seq, label, action):
    outdir = os.path.expanduser(f"~/gig/trajectory/{pass_id}")
    os.makedirs(outdir, exist_ok=True)
    png_path = os.path.join(outdir, f"{seq}-{label}.png")
    url, title = "", ""
    async with await _connect() as ws:
        cid = 1
        # page state (url + title) — evidence beyond the pixels
        try:
            r = await _call(ws, "Runtime.evaluate",
                            {"expression": "document.location.href+'|||'+document.title",
                             "returnByValue": True}, cid); cid += 1
            v = r.get("result", {}).get("result", {}).get("value", "") or ""
            if "|||" in v:
                url, title = v.split("|||", 1)
        except Exception:
            pass
        # screenshot (source of truth)
        r = await _call(ws, "Page.captureScreenshot", {"format": "png"}, cid); cid += 1
        b64 = r.get("result", {}).get("data")
        if not b64:
            return f"ERROR:no_screenshot_data:{r.get('error')}"
        with open(png_path, "wb") as f:
            f.write(base64.b64decode(b64))
    row = {"ts": int(time.time()), "pass_id": str(pass_id), "seq": str(seq),
           "label": label, "url": url, "title": title, "action": action, "png": png_path}
    with open(os.path.join(outdir, "trajectory.jsonl"), "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return png_path


def main():
    if len(sys.argv) < 4:
        print("ERROR:usage: cdp_snapshot.py <pass_id> <seq> <label> [action_note]")
        return
    pass_id, seq, label = sys.argv[1], sys.argv[2], sys.argv[3]
    action = sys.argv[4] if len(sys.argv) > 4 else ""
    try:
        print(asyncio.run(snapshot(pass_id, seq, label, action)))
    except Exception as e:
        # capture must never abort a pass
        print(f"ERROR:{type(e).__name__}:{e}")


if __name__ == "__main__":
    main()
