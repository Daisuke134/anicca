#!/usr/bin/env bash
# capafy-ig-marketing-daily.sh — B1-B4 IG line — DETERMINISTIC daily trigger for the Capafy
# Instagram marketing loop. Mirrors capafy-x-marketing-daily.sh but for IG Reels via
# ig-reels-poster (browser-direct, @useclaudeskills — an AI-OWNED account, NOT a Dais-personal one).
# launchd -> this script -> headless `claude -p`: selector -> copy -> faceless video (B3) ->
# ig-reels-poster (B4) -> ledger -> report. Copy is agent judgment, NEVER hardcoded here.
#
# ★ LIVE is HARD-GATED on warmup being complete (ig-account-warmer day>=7). @useclaudeskills is
#   warming (day-1 was 2026-07-18; commercial Reel + bio Capafy link only AFTER ~2026-07-25).
#   Until then this runs the pipeline in DRY only (proves the flow, publishes nothing). ★
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
LOG="$HOME/.openclaw/logs/capafy-ig-marketing-daily.log"
ROT="$HOME/.openclaw/state/capafy-marketing-rotation.jsonl"
WARMUP_STATE="$HOME/.cloak/ig-warmup-useclaudeskills.json"
IG_HANDLE="useclaudeskills"   # AI-OWNED account only (never a Dais-personal handle)
mkdir -p "$(dirname "$LOG")" "$(dirname "$ROT")"
echo "=== capafy-ig-marketing-daily run $(date '+%F %T %Z') ===" >>"$LOG"

# ── IG metrics/attribution run EVERY day (deterministic; IG variants, utm_source=instagram_bio) ──
/opt/homebrew/bin/python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_metrics.py >>"$LOG" 2>&1 || echo "ig_metrics failed (non-fatal)" >>"$LOG"

# ── WARMUP GATE: decide DRY vs LIVE. LIVE only when ig-account-warmer has reached day>=7. ──
WARM_DAY="$(/opt/homebrew/bin/python3 - "$WARMUP_STATE" <<'PY' 2>/dev/null
import json,sys,os
p=sys.argv[1]
try:
    d=json.load(open(p)); log=d.get("log",[]); print(len(log))
except Exception: print(0)
PY
)"
MODE_FLAG=""   # empty = dry (post_reel.py default). --live only after warmup.
if [ "${WARM_DAY:-0}" -ge 7 ]; then MODE_FLAG="--live"; fi
echo "warmup day-count=$WARM_DAY -> post mode: ${MODE_FLAG:-DRY}" >>"$LOG"

# ── CADENCE GATE (rolling 20h, platform=ig) ──
if [ -f "$ROT" ] && /opt/homebrew/bin/python3 - "$ROT" <<'PY'
import json,sys,time
last=0
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    try: r=json.loads(line)
    except: continue
    if r.get("platform")=="ig" and r.get("ts"): last=max(last,int(r["ts"]))
sys.exit(0 if last and (time.time()-last)<72000 else 1)
PY
then
  echo "cadence gate: last IG Reel < 20h ago — no-op." >>"$LOG"
  touch "$HOME/.openclaw/state/.capafy-ig-marketing-last-pass" 2>/dev/null || true
  exit 0
fi

PROMPT='You are the Anicca Capafy IG-marketing loop (headless; goal = drive Capafy skill subscribers via Instagram Reels; revenue → Dais bank; human NOT in loop). Triggered by launchd (ai.anicca.capafy-ig-marketing-daily). You post to the AI-OWNED IG account @'"$IG_HANDLE"' (NEVER a Dais-personal account). The bash caller passed the post mode as MODE='"${MODE_FLAG:-DRY}"' — if MODE=DRY you MUST run post_reel.py WITHOUT --live (proves the flow, publishes nothing; @'"$IG_HANDLE"' is still warming — a day-0 commercial post = suspension, so DRY is correct until ~2026-07-25). Only if MODE=--live do you publish.

STEP1 SELECT (tool): python3 ~/anicca/skills/earn/capafy-marketing/scripts/select_listing.py  → one online Capafy listing {agent_id,name,desc,url}.

STEP2 COPY (YOUR judgment, no template): from name+desc write (a) a Reel caption (hook + what the skill kills + a natural CTA; the Capafy URL goes in the ACCOUNT BIO, NEVER in the caption/first-comment — IG comment links are unclickable, research MD §1) and (b) a one-line on-screen hook for the video.

STEP3 VIDEO (B3, faceless engine): build ONE 9:16 mp4 introducing the listing via ~/anicca/skills/faceless-money-factory (assemble.sh + burn-captions.sh), using YOUR hook/script about THIS skill (topic = the listing, not generic finance). Gate it: only proceed if the mp4 exists and is 9:16.

STEP4 POST (B4, tool): python3 ~/.agents/skills/ig-reels-poster/scripts/post_reel.py --video <mp4> --caption-file <caption> --handle '"$IG_HANDLE"' MODE  (MODE = the mode above; omit for DRY). The poster has an account guard that fail-closes if @'"$IG_HANDLE"' is not the active IG account on :9222 — if it aborts on the guard, switch to @'"$IG_HANDLE"' in the IG account switcher (it is logged in) and retry once; do NOT post to any other account. Capture published + profile URL.

STEP5 BIO (only once, and only when MODE=--live): ensure the ACCOUNT BIO / profile Website carries the Capafy listing URL (utm_source=instagram_bio). This is the click path on IG. Do not touch bio during DRY.

STEP6 VERIFY + LEDGER: on --live, confirm the Reel is publicly visible and record its URL in ~/.openclaw/state/capafy-marketing-ig-ledger.jsonl (platform=ig) + the post time in the rotation ledger (platform=ig). On DRY, record that the flow reached the share step cleanly.

STEP7 REPORT TO DAIS — MANDATORY every pass (Dais wants to SEE the actual output, not a summary). Send to telegram chat 8547730585 via openclaw message send:
  (a) the VIDEO itself as media:  openclaw message send --channel telegram --target 8547730585 --media <the mp4 path> --force-document --message "<caption below>" --json  (--force-document keeps it uncompressed; if the video attach fails, fall back to sending a thumbnail/first-frame png + the message).
  (b) the message body MUST contain: the promoted listing name + agent_id, the mode (DRY or LIVE), the Reel public URL (or "DRY — not posted" on a dry pass), and the FULL caption text verbatim (the exact caption you wrote for the Reel).
  On a DRY pass you STILL send this once (video + full caption + which listing) so Dais can review the creative before go-live — you just do NOT publish to IG. Confirm the send returned a real message id; also AgentMail via loop-report if that path exists.

FINALLY touch ~/.openclaw/state/.capafy-ig-marketing-last-pass. A DRY pass, a deferred cadence pass, or a caught error is a clean finish, never a hang.'

CLIPROXY_KEY="$(cat "$HOME/.cli-proxy-api-key" 2>/dev/null || true)"
if [ -n "$CLIPROXY_KEY" ]; then
  export ANTHROPIC_BASE_URL="http://127.0.0.1:8317"
  export ANTHROPIC_AUTH_TOKEN="$CLIPROXY_KEY"
fi

env -u ANTHROPIC_API_KEY "$CLAUDE" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -p "$PROMPT" >>"$LOG" 2>&1
RC=$?
echo "=== capafy-ig-marketing-daily done rc=$RC $(date '+%F %T %Z') ===" >>"$LOG"
touch "$HOME/.openclaw/state/.capafy-ig-marketing-last-pass" 2>/dev/null || true
exit 0
