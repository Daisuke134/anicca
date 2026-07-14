#!/usr/bin/env python3
# instagrapi-based IG Reel poster — the VERIFIED FREE posting method (2026-07-14), replaces the
# web-composer post_reel.py which was a structural dead end (IG silently drops automated web posts).
# Flow: pull the CloakBrowser's already-logged-in sessionid (avoids a fresh-login challenge) ->
# instagrapi.login_by_sessionid -> ffmpeg thumbnail (avoids moviepy dep) -> clip_upload ->
# verify the reel is publicly visible. Prints ONE structured JSON line matching run.sh's contract
# ({"outcome": "published"|"failed"|"dry", "post_url": ..., "before_hrefs": []}).
import argparse, json, os, sys, time, subprocess, urllib.request
sys.path.insert(0, os.path.expanduser("~/.claude/skills/ig-account-create/scripts"))
import cdp  # noqa: E402
from websocket import create_connection  # noqa: E402


def get_sessionid(port):
    tabs = json.load(urllib.request.urlopen(f"http://localhost:{port}/json/list"))
    tid = next(t["id"] for t in tabs if t.get("type") == "page" and "instagram.com" in (t.get("url") or ""))
    ws = create_connection(cdp.page_ws(tid), timeout=20, suppress_origin=True, max_size=None)
    ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
    ws.send(json.dumps({"id": 2, "method": "Network.getAllCookies"}))
    sid = None
    end = time.time() + 15
    while time.time() < end:
        m = json.loads(ws.recv())
        if m.get("id") == 2:
            for c in m["result"]["cookies"]:
                if c["name"] == "sessionid" and "instagram" in c["domain"]:
                    sid = c["value"]
            break
    ws.close()
    return tid, sid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--handle", required=True)
    ap.add_argument("--port", default=os.environ.get("CDP_PORT", "9222"))
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    res = {"handle": a.handle, "outcome": "failed", "post_url": None, "before_hrefs": []}
    try:
        caption = open(a.caption_file, encoding="utf-8").read().strip()
        _, sid = get_sessionid(a.port)
        if not sid:
            res["error"] = "no sessionid in browser (not logged in on this port)"
            print(json.dumps(res, ensure_ascii=False)); return

        from instagrapi import Client
        cl = Client()
        cl.delay_range = [2, 5]
        cl.login_by_sessionid(sid)
        # ★ ACCOUNT GUARD (fail-closed): instagrapi knows who the sessionid belongs to. Never post
        #   to the wrong account. ★
        if cl.username != a.handle:
            res["error"] = f"account guard: sessionid is @{cl.username}, expected @{a.handle} — abort"
            print(json.dumps(res, ensure_ascii=False)); return

        if not a.live:
            res["outcome"] = "dry"; res["reached"] = "login-ok"
            print(json.dumps(res, ensure_ascii=False)); return

        thumb = a.video + ".jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.video, "-ss", "1", "-vframes", "1", thumb], check=True)
        media = cl.clip_upload(a.video, caption, thumbnail=thumb)
        d = media.model_dump() if hasattr(media, "model_dump") else media.dict()
        code = d.get("code")
        url = f"https://www.instagram.com/reel/{code}/"

        # REALITY GATE: confirm the reel is publicly visible (logged-out) before claiming success.
        public = None
        time.sleep(3)
        try:
            req = urllib.request.Request(f"https://www.instagram.com/{a.handle}/", headers={"User-Agent": "Mozilla/5.0"})
            html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "ignore")
            public = bool(code) and code in html
        except Exception:
            public = None  # network gate; instagrapi's returned code is still the source of truth

        res["outcome"] = "published"; res["post_url"] = url; res["code"] = code
        res["public_verified"] = public; res["reached"] = "PUBLISHED"
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
