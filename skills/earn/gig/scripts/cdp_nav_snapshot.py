#!/usr/bin/env python3
"""cdp_nav_snapshot.py — DETERMINISTIC navigate+screenshot helper for the gig reality-verifier
(feature gig-reality-verify, fresh-adversary FIND-001 fix: docs/loop-engineering/26-...md §8).

Unlike cdp_snapshot.py (which only screenshots whatever tab is ALREADY open), this helper actually
performs a real CDP `Page.navigate(url)` call, WAITS for the page to finish loading (Page.loadEventFired
event, with a document.readyState poll fallback), THEN captures a screenshot and appends a trajectory
row — so the fresh judge's navigation is a reproducible tool call, not freeform LLM-improvised Bash/CDP
that happened to work once.

get_tab()/navigate mechanics below are self-contained (copied IN, not imported from any path outside
this repo — behavioral-spec REQ-006 requires no dangling cross-repo reference).

Usage:
  python3 cdp_nav_snapshot.py <pass_id> <seq> <label> <url> [action_note]
    e.g. python3 cdp_nav_snapshot.py reality-1783800000 01 reality_check_01 https://coconala.com/mypage/services_lists

Writes:
  ~/gig/trajectory/<pass_id>/<seq>-<label>.png
  appends {ts,pass_id,seq,label,url,title,action,navigated_ok} to ~/gig/trajectory/<pass_id>/trajectory.jsonl
Prints the png path on success, or ERROR:<reason> on failure (never raises — capture must never abort
a verification run).
"""
import asyncio, base64, json, os, sys, subprocess, time, urllib.request

try:
    import websockets
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "websockets", "-q"], capture_output=True)
    import websockets

CDP = "http://localhost:9222"
LOAD_TIMEOUT_SECS = 15  # bounded — never hang the judge indefinitely on a page that never settles


def get_tab():
    data = json.loads(urllib.request.urlopen(f"{CDP}/json/list", timeout=8).read())
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
        f"ws://localhost:9222/devtools/page/{tab}",
        ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024,
    )


async def _call(ws, method, params, cid):
    await ws.send(json.dumps({"id": cid, "method": method, "params": params}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=25)
        d = json.loads(raw)
        if d.get("id") == cid:
            return d


async def _wait_for_load(ws, deadline, start_cid):
    """Wait for Page.loadEventFired, falling back to a document.readyState poll if the event never
    arrives within the deadline (bounded — REQ-006 edge case: never hang indefinitely)."""
    cid = start_cid
    loop = asyncio.get_event_loop()
    while loop.time() < deadline:
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=min(1.0, remaining))
        except asyncio.TimeoutError:
            continue
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if d.get("method") == "Page.loadEventFired":
            return True, cid
    # fallback: poll document.readyState directly
    while loop.time() < deadline:
        r = await _call(ws, "Runtime.evaluate",
                         {"expression": "document.readyState", "returnByValue": True}, cid)
        cid += 1
        val = r.get("result", {}).get("result", {}).get("value")
        if val == "complete":
            return True, cid
        await asyncio.sleep(0.5)
    return False, cid


async def navigate_and_snapshot(pass_id, seq, label, url, action):
    outdir = os.path.expanduser(f"~/gig/trajectory/{pass_id}")
    os.makedirs(outdir, exist_ok=True)
    png_path = os.path.join(outdir, f"{seq}-{label}.png")
    final_url, title, navigated_ok = "", "", False

    async with await _connect() as ws:
        cid = 1
        r = await _call(ws, "Page.enable", {}, cid); cid += 1
        await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": url}}))
        cid += 1

        deadline = asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS
        navigated_ok, cid = await _wait_for_load(ws, deadline, cid)

        # page state (url + title) — evidence beyond the pixels, and proof navigation actually landed
        try:
            r = await _call(ws, "Runtime.evaluate",
                             {"expression": "document.location.href+'|||'+document.title",
                              "returnByValue": True}, cid); cid += 1
            v = r.get("result", {}).get("result", {}).get("value", "") or ""
            if "|||" in v:
                final_url, title = v.split("|||", 1)
        except Exception:
            pass

        # screenshot (source of truth) — captured regardless of navigated_ok (never lose evidence)
        r = await _call(ws, "Page.captureScreenshot", {"format": "png"}, cid); cid += 1
        b64 = r.get("result", {}).get("data")
        if not b64:
            return f"ERROR:no_screenshot_data:{r.get('error')}"
        with open(png_path, "wb") as f:
            f.write(base64.b64decode(b64))

    row = {"ts": int(time.time()), "pass_id": str(pass_id), "seq": str(seq), "label": label,
           "requested_url": url, "url": final_url, "title": title, "action": action,
           "navigated_ok": navigated_ok, "png": png_path}
    with open(os.path.join(outdir, "trajectory.jsonl"), "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return png_path


def main():
    if len(sys.argv) < 5:
        print("ERROR:usage: cdp_nav_snapshot.py <pass_id> <seq> <label> <url> [action_note]")
        return
    pass_id, seq, label, url = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    action = sys.argv[5] if len(sys.argv) > 5 else ""
    try:
        print(asyncio.run(navigate_and_snapshot(pass_id, seq, label, url, action)))
    except Exception as e:
        # capture must never abort a verification run
        print(f"ERROR:{type(e).__name__}:{e}")


if __name__ == "__main__":
    main()
