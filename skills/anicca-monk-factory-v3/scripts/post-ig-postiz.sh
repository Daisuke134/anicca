#!/usr/bin/env bash
# Post a video to Instagram @monk.anicca via Postiz (interim path while {{profile.lateness.stakeholders.channel}}-manual IG is reCAPTCHA-blocked).
# Usage: post-ig-postiz.sh <video.mp4> <caption.txt>
# Needs POSTIZ_API_KEY in ~/.openclaw/.env. Posts to the "monk" instagram-standalone integration.
set -euo pipefail
V="$1"; CAPFILE="$2"
[ -f "$V" ] || { echo "FATAL: video not found: $V"; exit 1; }
[ -f "$CAPFILE" ] || { echo "FATAL: caption not found: $CAPFILE"; exit 1; }
set -a; source ~/.openclaw/.env 2>/dev/null; set +a
: "${POSTIZ_API_KEY:?POSTIZ_API_KEY missing}"
INTID="cmoopzaak04yop70y1yx1bwr1"   # Postiz integration "monk" = @monk.anicca (instagram-standalone)
CAP="$(cat "$CAPFILE")"

echo "[1/3] upload media to Postiz"
UP=$(curl -sS -X POST "https://api.postiz.com/public/v1/upload" -H "Authorization: $POSTIZ_API_KEY" -F "file=@$V")
MID=$(printf '%s' "$UP" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
MPATH=$(printf '%s' "$UP" | python3 -c "import sys,json;print(json.load(sys.stdin)['path'])")
[ -n "$MID" ] || { echo "FATAL: upload failed: $UP"; exit 1; }
echo "  media id=$MID"

echo "[2/3] create post (type=now, post_type=post)"
NOW=$(python3 -c "import datetime;print(datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%S.000Z'))")
PAYLOAD=$(python3 -c "
import json,sys,uuid
print(json.dumps({'type':'now','shortLink':False,'date':sys.argv[3],'tags':[],
 'posts':[{'integration':{'id':sys.argv[4]},
   'value':[{'content':sys.argv[1],'id':str(uuid.uuid4()),'image':[{'id':sys.argv[2],'path':sys.argv[5]}]}],
   'settings':{'post_type':'post'}}]}))
" "$CAP" "$MID" "$NOW" "$INTID" "$MPATH")
RES=$(curl -sS -X POST "https://api.postiz.com/public/v1/posts" -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" -d "$PAYLOAD")
echo "  $RES"
PID=$(printf '%s' "$RES" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0]['postId'] if isinstance(d,list) and d else '')" 2>/dev/null)
[ -n "$PID" ] || { echo "FATAL: post create failed"; exit 1; }

echo "[3/3] poll until PUBLISHED (#8 verify)"
S=$(python3 -c "import datetime;print((datetime.datetime.now(datetime.UTC)-datetime.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S.000Z'))")
E=$(python3 -c "import datetime;print((datetime.datetime.now(datetime.UTC)+datetime.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S.000Z'))")
for i in $(seq 1 25); do
  ST=$(curl -sS "https://api.postiz.com/public/v1/posts?startDate=$S&endDate=$E&display=normal" -H "Authorization: $POSTIZ_API_KEY" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);a=d.get('posts',d) if isinstance(d,dict) else d
for p in (a if isinstance(a,list) else []):
 if p.get('id')=='$PID': print(p.get('state'),'|',p.get('releaseURL') or '','|',p.get('error') or ''); break" 2>/dev/null)
  echo "  iter $i: $ST"
  case "$ST" in PUBLISHED*) echo "IG_PUBLISHED $ST"; exit 0;; *Error*|ERR*) echo "IG_ERROR $ST"; exit 2;; esac
  sleep 12
done
echo "IG_STILL_QUEUE postId=$PID (check Postiz)"; exit 0
