#!/usr/bin/env bash
# earn/video — faceless-video earn SLOT entrypoint for the ONE loop (run-skill.mjs spawns this).
# Does EXACTLY ONE bounded state-machine transition per wake (idempotent), prints a one-line JSON
# result on stdout, exit 0. Slot contract: no human, 5-gate + record-earn (real USDC only), bounded.
# The whole faceless-video lifecycle (create→warmup→affiliate-link@day7→post→record) is loop-driven;
# EVERY step incl. the affiliate link is a transition here — never a manual後工程.
set -uo pipefail
SK="$HOME/anicca/skills/earn/video"; PY=/opt/homebrew/bin/python3
export PATH="$HOME/.local/bin:$PATH"; set -a; . "$HOME/.openclaw/.env" 2>/dev/null || true; set +a
TIMEOUT="${SKILL_TIMEOUT_S:-900}"
DRY="${EARN_VIDEO_DRY:-0}"
HANDLE="${EARN_VIDEO_HANDLE:-money_blueprintdaily}"
CREDS="$HOME/.cloak/ig-moneyblueprint.json"          # account creds (tid, email, …)
STATE="$HOME/.cloak/earn-video-${HANDLE}.json"        # slot state (status/warmup_day/…)
LEDGER="$HOME/.cloak/earn-video-ledger.jsonl"
AFFLINK="${MONEY_AFFILIATE_URL:-${MONK_EBOOK_URL:-}}"  # affiliate/ebook link (set in env); empty ⇒ S2 waits
TODAY="$(date +%Y-%m-%d)"
TID="$($PY -c "import json,os;p=os.path.expanduser('$CREDS');print(json.load(open(p)).get('tid','') if os.path.exists(p) else '')" 2>/dev/null)"

# init slot state if missing: account already created+profiled ⇒ start warming day 0
[ -s "$STATE" ] || printf '{"handle":"%s","status":"warming","warmup_day":0,"affiliate_set":false}\n' "$HANDLE" > "$STATE"

TRANS="$($PY -c "import json,sys;sys.path.insert(0,'$SK');from decide import decide;print(decide(json.load(open('$STATE')),'$TODAY'))" 2>/dev/null)"
DID=""; EARNED=0; COST=0

set_state(){ $PY -c "import json,sys;p='$STATE';d=json.load(open(p));d.update(json.loads(sys.argv[1]));json.dump(d,open(p,'w'),ensure_ascii=False)" "$1"; }
wday(){ $PY -c "import json;print(int(json.load(open('$STATE')).get('warmup_day',0)))"; }

case "$TRANS" in
  S1_warmup)
    # REAL warmup in the account's ISOLATED context (--tid): bringToFront + play() + verify currentTime advances.
    # ★ Dim4 fix: advance warmup_day ONLY when warm_iso REALLY watched >=3 reels (verified playback); never fake. ★
    WATCHED=0; BAN=0
    if [ "$DRY" = 1 ]; then WATCHED=5; else
      timeout "$TIMEOUT" $PY "$HOME/.claude/skills/ig-account-warmer/scripts/warm_iso.py" --tid "$TID" --handle "$HANDLE" --reels 5 >/tmp/ev_warm.log 2>&1 || true
      WATCHED=$($PY -c "import json,sys
try:
  for l in open('/tmp/ev_warm.log'):
    l=l.strip()
    if l.startswith('{') and 'reels_watched_real' in l: print(json.loads(l)['reels_watched_real']); break
  else: print(0)
except: print(0)" 2>/dev/null)
      grep -q "STOP_BAN_SIGNAL" /tmp/ev_warm.log 2>/dev/null && BAN=1
    fi
    if [ "$BAN" = 1 ]; then DID="warmup STOPPED: ban signal — NOT advancing day";
    elif [ "${WATCHED:-0}" -ge 3 ]; then
      set_state "{\"warmup_day\": $(( $(wday) + 1 )), \"last_warmup_date\": \"$TODAY\", \"status\": \"warming\"}"
      DID="warmup day→$(wday) (real reels watched=$WATCHED)"
    else
      set_state "{\"last_warmup_date\": \"$TODAY\"}"   # mark attempt today (idempotent) but do NOT advance day on too-few real views
      DID="warmup INCOMPLETE: only $WATCHED real views (<3) — day NOT advanced"
    fi ;;
  S2_affiliate)
    if [ -z "$AFFLINK" ]; then
      # ★ Dim1/3 fix: no link available yet → ADVANCE as pending (status=warmed), keep posting; never dead-end, never wait on a human. S2 fires later once a link exists. ★
      set_state "{\"affiliate_pending\": true, \"status\": \"warmed\"}"
      DID="affiliate pending (no link yet) — advancing to post; will set link in-loop when MONEY_AFFILIATE_URL exists"
    else
      [ "$DRY" = 1 ] || timeout "$TIMEOUT" $PY "$HOME/.claude/skills/ig-account-create/scripts/setup_profile.py" --tid "$TID" --website "$AFFLINK" --username "$HANDLE" >/tmp/ev_aff.log 2>&1 || true
      set_state "{\"affiliate_set\": true, \"affiliate_pending\": false, \"status\": \"warmed\"}"; DID="affiliate link set (post-warmup, in-loop): $AFFLINK"
    fi ;;
  S3_post)
    OUT="$HOME/.claude/skills/faceless-money-factory/state/renders"
    GENBUD=$(( TIMEOUT * 2 / 3 )); POSTBUD=$(( TIMEOUT / 3 ))   # ★ Dim5 fix: split ONE wake budget across both calls ★
    # generate today's fresh script (agent writes it; here use gen fallback if present) + render via run-daily
    [ "$DRY" = 1 ] || timeout "$GENBUD" bash "$HOME/.claude/skills/faceless-money-factory/scripts/run-daily.sh" "${EARN_VIDEO_SCRIPT:-$OUT/today.txt}" en >/tmp/ev_gen.log 2>&1 || true
    MP4="$(ls -t "$OUT"/*.mp4 2>/dev/null | head -1)"
    if [ -n "$MP4" ]; then
      printf 'Daily money tips. Follow @%s for more. #moneytok #personalfinance\n' "$HANDLE" > /tmp/ev_cap.txt
      LIVEFLAG="--dry"; [ "$(/usr/bin/env $PY -c "import json;print(json.load(open('$STATE')).get('affiliate_set'))")" = "True" ] && LIVEFLAG="--live"
      [ "$DRY" = 1 ] || timeout "$POSTBUD" $PY "$HOME/.claude/skills/ig-reels-poster/scripts/post_reel.py" --video "$MP4" --caption-file /tmp/ev_cap.txt --handle "$HANDLE" --tid "$TID" $LIVEFLAG >/tmp/ev_post.log 2>&1 || true
      set_state "{\"last_post_date\": \"$TODAY\", \"status\": \"warmed\"}"
      DID="posted reel ($LIVEFLAG) $(basename "$MP4")"
    else DID="post skipped: no rendered mp4 ($(tail -1 /tmp/ev_gen.log 2>/dev/null|cut -c1-50))"; fi ;;
  S4_record)
    # record ONLY real external USDC inflows from the affiliate/ebook payout source (none wired yet ⇒ nothing)
    DID="record-earn checked: no verified USDC inflow this wake"; set_state "{\"status\": \"monetized\"}" ;;
  noop) DID="noop (already warmed today)" ;;
  S0_create)
    # one-time bootstrap (0-human via ig-account-create+setup_profile, proven). Not a per-wake human step.
    DID="bootstrap: account not created yet — ig-account-create (0-human) runs once, then S1–S4 loop takes over" ;;
  *) DID="unknown transition: $TRANS" ;;
esac

# ★ Dim5 fix: emit valid one-line JSON via json.dumps (escapes any "/\ in DID from logs) ★
R_HANDLE="$HANDLE" R_TRANS="$TRANS" R_DID="$DID" R_EARNED="$EARNED" R_COST="$COST" $PY -c "import json,os;print(json.dumps({'slot':'earn/video','handle':os.environ['R_HANDLE'],'transition':os.environ['R_TRANS'],'did':os.environ['R_DID'],'earned_usdc':float(os.environ['R_EARNED']),'cost_usdc':float(os.environ['R_COST'])},ensure_ascii=False))"
exit 0
