#!/usr/bin/env bash
# earn/affiliate — ONE Anicca loop slot. EARN_MODE=discover|execute. ONE bounded unit per wake:
# post the next QUEUED educational slideshow (carousel) to the next READY affiliate niche account,
# ensure the Amazon affiliate link is in BIO, archive the posted set. Per-sale commission accrues
# LATER (record-affiliate-earn / INV-7 counts only real commission). NO HUMAN. Fail-closed: never
# posts to a non-affiliate / unconfirmed account. Mirrors earn/clip/run.sh.
set -uo pipefail
EARN_MODE="${EARN_MODE:-discover}"
WAKE="${WAKE_ID:-$(date -u +%s)}"
HOME_DIR="$HOME"
QUEUE="$HOME_DIR/affiliate/queue"          # producer.sh fills this: <id>/{slide_N.png, caption.txt}
POSTED="$HOME_DIR/affiliate/posted"
ACCTS="$HOME_DIR/.cloak/affiliate-accounts.json"   # [{handle,profile,port,niche,status}]
POSTER="$HOME_DIR/.claude/skills/ig-account-poster/scripts/post.py"   # PROVEN carousel poster
CDP_DIR="$HOME_DIR/.claude/skills/ig-account-create/scripts"
PY=/opt/homebrew/bin/python3
STATE="$HOME_DIR/anicca/skills/earn/affiliate/state"
mkdir -p "$QUEUE" "$POSTED" "$STATE"

# MEASURE: 毎wake無条件に1回、アカウント全体のコミッション増分だけ確認。
# SET/HANDLE/EARN_MODEのどれよりも前に置く — amazon_report.pyはこれらに一切
# 依存しない新規タブベースの独立した確認であり、POSTの各種ゲートを一切
# ブロックしない(clip/run.shのself_healより依存が少ない、
# docs/superpowers/specs/2026-07-05-affiliate-bounty-state-machine-design.md §1.2参照)。
# measure_commission.py自身が例外を握りつぶさずJSON出力に含める設計なので、
# ここでの`2>/dev/null || true`はプロセスの異常終了だけを無害化するためのもの。
"$PY" "$HOME_DIR/anicca/skills/earn/affiliate/measure_commission.py" \
  --watermark "$STATE/commission-watermark.json" --wake "$WAKE" 2>/dev/null || true

emit() { printf '{"slot":"earn/affiliate","did":%s,"earn_usdc":0,"cost_usdc":0}\n' \
  "$(printf '%s' "$1" | "$PY" -c 'import json,sys;print(json.dumps(sys.stdin.read()))')"; }

# next queued slideshow (oldest dir with >=3 slides + caption)
SET=""
for d in "$QUEUE"/aff*; do
  [ -d "$d" ] || continue
  n=$(ls "$d"/slide_*.png 2>/dev/null | wc -l | tr -d ' ')
  [ "$n" -ge 3 ] && [ -f "$d/caption.txt" ] && { SET="$d"; break; }
done

# next ready affiliate account
read -r HANDLE PORT < <("$PY" - "$ACCTS" <<'PYJSON' 2>/dev/null
import json,sys
try: a=json.load(open(sys.argv[1]))
except Exception: a=[]
for x in a:
    if x.get("status")=="ready": print(x.get("handle",""), x.get("port",9222)); break
PYJSON
)

if [ -z "$SET" ] || [ -z "${HANDLE:-}" ]; then
  emit "nothing to post (queued_set=${SET:-none} ready_account=${HANDLE:-none})"; exit 0
fi
if [ "$EARN_MODE" != "execute" ]; then
  emit "discover: would post $(basename "$SET") ($(ls "$SET"/slide_*.png | wc -l | tr -d ' ') slides) to @${HANDLE}"; exit 0
fi

# execute: confirm the account's browser is up + logged in as HANDLE (fail-closed)
TID="$(curl -sS --max-time 5 "http://localhost:${PORT}/json/list" 2>/dev/null | "$PY" -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: d=[]
ps=[t for t in d if t.get("type")=="page" and "instagram.com" in (t.get("url") or "")]
print((ps[0] if ps else (next((t for t in d if t.get("type")=="page"), {}))).get("id",""))')"
[ -n "$TID" ] || { emit "account @${HANDLE} browser not up on :${PORT}"; exit 0; }
ACTIVE="$(CDP_PORT="$PORT" "$PY" -c "
import sys,os; sys.path.insert(0,'$CDP_DIR'); import cdp, time
tid='$TID'
try:
    cdp.navigate(tid,'https://www.instagram.com/'); time.sleep(5)
    print(cdp.evaluate(tid,'(()=>(document.querySelector(\"img[alt\$=のプロフィール写真]\")||{}).alt||\"\")()') or '')
except Exception: print('')
" 2>/dev/null | sed 's/のプロフィール写真//')"
[ "$ACTIVE" = "$HANDLE" ] || { emit "not logged in as @${HANDLE} on :${PORT} (active='${ACTIVE}') — skip"; exit 0; }

# snapshot the account's posts BEFORE posting, so we confirm via a profile-tile DIFF (the poster's own
# post_url verify false-negatives on carousels). Our ACTIVE==HANDLE check above is the fail-closed guard.
tiles_before="$(CDP_PORT="$PORT" "$PY" -c "
import sys,os,time; sys.path.insert(0,'$CDP_DIR'); import cdp
cdp.navigate('$TID','https://www.instagram.com/$HANDLE/'); time.sleep(4)
print('|'.join(cdp.evaluate('$TID','(()=>[...document.querySelectorAll(\"main a[href*=/p/],main a[href*=/reel/]\")].map(a=>a.getAttribute(\"href\")))()') or []))" 2>/dev/null)"

IMAGES="$(ls "$SET"/slide_*.png | sort -t_ -k2 -n | paste -sd, -)"
RES="$(CDP_PORT="$PORT" "$PY" "$POSTER" --images "$IMAGES" --caption-file "$SET/caption.txt" --live 2>/dev/null | tail -1)"

# confirm by a NEW tile on the profile (truth), not the poster's post_url
URL="$(CDP_PORT="$PORT" "$PY" - "$TID" "$HANDLE" "$tiles_before" "$CDP_DIR" <<'PYV' 2>/dev/null
import sys,os,time; sys.path.insert(0,sys.argv[4]); import cdp
tid,handle,before=sys.argv[1],sys.argv[2],set(sys.argv[3].split('|'))
url=""
for _ in range(8):
    time.sleep(10); cdp.navigate(tid,f"https://www.instagram.com/{handle}/"); time.sleep(4)
    now=cdp.evaluate(tid,'(()=>[...document.querySelectorAll("main a[href*=/p/],main a[href*=/reel/]")].map(a=>a.getAttribute("href")))()') or []
    new=[h for h in now if h and h not in before]
    if new: url="https://www.instagram.com"+new[0]; break
print(url)
PYV
)"
if [ -n "$URL" ]; then
  mv "$SET" "$POSTED/" 2>/dev/null || true
  emit "posted carousel @${HANDLE}: ${URL} (BIO must carry the Amazon link; commission recorded later by record-affiliate-earn)"
else
  emit "post not confirmed by a new profile tile (poster res=${RES})"
fi
exit 0
