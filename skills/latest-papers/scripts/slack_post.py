#!/usr/bin/env python3
"""latest-papers : post the digest image to Slack #metrics with a comment.

DETERMINISTIC 3-step external upload, then VERIFIES the file is actually
shared into the channel (shares non-empty). This is the exact flow proven to
post with non-empty shares (manual run file F0B45NBMHNF). The cron model must
NOT hand-roll the upload.

Usage: python3 slack_post.py image.png comment.txt [channel_id]
Default channel = {{profile.channels.reportChannel}} (#metrics).
Exit 0 only when files.info shows the file shared into the channel.
"""
import json, os, sys, urllib.request, urllib.parse

TOKEN = os.environ["SLACK_BOT_TOKEN"]
img = sys.argv[1]
comment = open(sys.argv[2], encoding="utf-8").read()
CHAN = sys.argv[3] if len(sys.argv) > 3 else "{{profile.channels.reportChannel}}"

def api(method, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request("https://slack.com/api/" + method, data=body,
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Content-Type": "application/x-www-form-urlencoded"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

size = os.path.getsize(img)
fname = os.path.basename(img)

r1 = api("files.getUploadURLExternal", {"filename": fname, "length": size})
assert r1.get("ok"), f"getUploadURLExternal failed: {r1}"
up_url, file_id = r1["upload_url"], r1["file_id"]

with open(img, "rb") as f:
    put = urllib.request.Request(up_url, data=f.read(), method="POST")
    urllib.request.urlopen(put, timeout=120).read()

r3 = api("files.completeUploadExternal", {
    "files": json.dumps([{"id": file_id, "title": fname}]),
    "channel_id": CHAN,
    "initial_comment": comment,
})
assert r3.get("ok"), f"completeUploadExternal failed: {r3}"

# VERIFY via conversations.history (authoritative & immediate). files.info
# .shares lags after completeUploadExternal and gives false negatives, so it
# is NOT trusted here. Poll the channel for a message carrying this file_id.
import time
seen = False
for attempt in range(8):
    h = api("conversations.history", {"channel": CHAN, "limit": 12})
    if h.get("ok"):
        for m in h.get("messages", []):
            if any(f.get("id") == file_id for f in (m.get("files") or [])):
                seen = True
                ts = m.get("ts")
                break
    if seen:
        break
    time.sleep(4)

if not seen:
    print(f"ERROR: file {file_id} uploaded but NOT visible in channel "
          f"{CHAN} after retries (orphan).", file=sys.stderr)
    sys.exit(1)
print(json.dumps({"file_id": file_id, "channel": CHAN, "message_ts": ts},
                 ensure_ascii=False))
print(f"POSTED_OK file_id={file_id} channel={CHAN} ts={ts}")
