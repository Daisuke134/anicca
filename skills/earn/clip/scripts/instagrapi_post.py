import json, os, sys, time, traceback
from websocket import create_connection
sys.path.insert(0, os.path.expanduser("~/.claude/skills/ig-account-create/scripts"))
import cdp
from instagrapi import Client

PORT = os.environ.get("CDP_PORT", "9223")
VIDEO = sys.argv[1] if len(sys.argv) > 1 else "/tmp/small-test.mp4"
def log(m): print(m, flush=True)

# 1) pull sessionid from the already-logged-in browser via CDP Network.getAllCookies
import urllib.request
tabs = json.load(urllib.request.urlopen(f"http://localhost:{PORT}/json/list"))
tid = next(t["id"] for t in tabs if t.get("type") == "page" and "instagram.com" in (t.get("url") or ""))
ws = create_connection(cdp.page_ws(tid), timeout=20, suppress_origin=True, max_size=None)
ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
ws.send(json.dumps({"id": 2, "method": "Network.getAllCookies"}))
sessionid = ds_user_id = None
end = time.time() + 15
while time.time() < end:
    m = json.loads(ws.recv())
    if m.get("id") == 2:
        for c in m["result"]["cookies"]:
            if c["name"] == "sessionid" and "instagram" in c["domain"]:
                sessionid = c["value"]
            if c["name"] == "ds_user_id" and "instagram" in c["domain"]:
                ds_user_id = c["value"]
        break
ws.close()
log(f"sessionid found={bool(sessionid)} ds_user_id={ds_user_id}")
if not sessionid:
    log("NO sessionid in browser — abort"); sys.exit(1)

# 2) instagrapi login via the browser's trusted sessionid (no fresh-login challenge)
cl = Client()
cl.delay_range = [2, 5]
try:
    cl.login_by_sessionid(sessionid)
    log(f"LOGIN_BY_SESSIONID OK as {cl.username} (pk={cl.user_id})")
    cl.dump_settings("/Users/operator/.cloak/instagrapi-aiclipsvault.json")
except Exception as e:
    log(f"SESSIONID LOGIN ERR: {type(e).__name__}: {str(e)[:300]}"); sys.exit(1)

# 3) upload the reel — generate thumbnail via ffmpeg (avoid moviepy dep)
import subprocess
thumb = VIDEO + ".jpg"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", VIDEO, "-ss", "1", "-vframes", "1", thumb], check=True)
log(f"thumbnail generated: {os.path.basename(thumb)}")
try:
    log(f"clip_upload {os.path.basename(VIDEO)} ...")
    media = cl.clip_upload(VIDEO, "AI clips daily #ai #money #investing", thumbnail=thumb)
    d = media.dict() if hasattr(media, "dict") else {}
    log(f"UPLOAD OK code={d.get('code')} url=https://www.instagram.com/reel/{d.get('code')}/")
except Exception as e:
    log(f"UPLOAD ERR: {type(e).__name__}: {str(e)[:400]}"); traceback.print_exc()
