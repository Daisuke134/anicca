#!/usr/bin/env python3
# store-recordings.py — pull EVERY Telnyx call recording (LM wake calls) → store mp3 locally forever.
# Idempotent (skips downloaded ids). Cron this for continuous storage.
import json, os, urllib.request
KEY = os.environ["TELNYX_API_KEY"]
STORE = os.path.expanduser("~/.openclaw/state/lm-video/recordings")
MAN = os.path.join(STORE, "manifest.jsonl")
os.makedirs(STORE, exist_ok=True)
req = urllib.request.Request("https://api.telnyx.com/v2/recordings?page%5Bsize%5D=50",
                             headers={"Authorization": f"Bearer {KEY}"})
recs = json.loads(urllib.request.urlopen(req, timeout=20).read())["data"]
have = set()
if os.path.exists(MAN):
    for ln in open(MAN):
        try: have.add(json.loads(ln)["id"])
        except: pass
new = 0
for r in recs:
    rid = r.get("id"); url = (r.get("download_urls") or {}).get("mp3")
    if not rid or not url or rid in have or r.get("status") != "completed": continue
    out = os.path.join(STORE, f"{(r.get('created_at') or '').replace(':','-')}-{rid}.mp3")
    try:
        urllib.request.urlretrieve(url, out)
        with open(MAN, "a") as f:
            f.write(json.dumps({"id": rid, "created_at": r.get("created_at"), "file": out,
                                "duration_millis": r.get("duration_millis"), "call": r.get("call_control_id")}) + "\n")
        new += 1; print("stored", os.path.basename(out))
    except Exception as e:
        print("fail", rid, str(e)[:60])
print(f"done: {new} new, {len(recs)} listed")
