#!/usr/bin/env bash
# capafy-ig-marketing-daily.sh — B1-B4 IG line — DETERMINISTIC daily trigger for the Capafy
# Instagram marketing loop. Mirrors capafy-x-marketing-daily.sh but for IG Reels via
# instagrapi (private API, @useclaudeskills — an AI-OWNED account, NOT a Dais-personal one).
# launchd -> this script -> headless `claude -p`: selector -> copy -> faceless video (B3) ->
# instagrapi post (B4) -> ledger -> report. Copy is agent judgment, NEVER hardcoded here.
# LaunchAgent: ai.anicca.capafy-ig-marketing-daily at 16:00 local; stdout/stderr use LOG below.
#
# ★ LIVE starts from the first completed warmup day. Initial posts stay NON-COMMERCIAL: no bio
#   link and no commercial CTA until the reach-health marker exists. Warmup continues in parallel. ★
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
LOG="$HOME/.openclaw/logs/capafy-ig-marketing-daily.log"
ROT="$HOME/.openclaw/state/capafy-marketing-rotation.jsonl"
WARMUP_STATE="$HOME/.cloak/ig-warmup-useclaudeskills.json"
LANDING_URL="https://capafy-skills-daily.netlify.app"
LANDING_SITE_ID="41c8e52e-b163-442a-84ff-fd866269bf6c"
IG_HANDLE="useclaudeskills"   # AI-OWNED account only (never a Dais-personal handle)
mkdir -p "$(dirname "$LOG")" "$(dirname "$ROT")"
echo "=== capafy-ig-marketing-daily run $(date '+%F %T %Z') ===" >>"$LOG"

# ── IG metrics/attribution run EVERY day (deterministic; IG variants, utm_source=instagram_bio) ──
/opt/homebrew/bin/python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_metrics.py >>"$LOG" 2>&1 || echo "ig_metrics failed (non-fatal)" >>"$LOG"

# ── All-skills bio landing refreshes on EVERY pass, including cadence no-op days. ──
/opt/homebrew/bin/python3 "$HOME/anicca/skills/earn/capafy-marketing/scripts/build_landing.py" >>"$LOG" 2>&1 && netlify deploy --prod --dir "$HOME/anicca/skills/earn/capafy-marketing/site" --site "$LANDING_SITE_ID" >>"$LOG" 2>&1 || echo "landing regenerate/deploy failed (non-fatal)" >>"$LOG"

# ── WARMUP GATE: decide DRY vs LIVE. LIVE from the first completed warmup day. ──
WARM_DAY="$(/opt/homebrew/bin/python3 - "$WARMUP_STATE" <<'PY' 2>/dev/null
import json,sys,os
p=sys.argv[1]
try:
    d=json.load(open(p)); log=d.get("log",[]); print(len(log))
except Exception: print(0)
PY
)"
# ★STRATEGY (2026-07-19 Dais, WHOLE marketing engine): warm up for 2 days, post from DAY 3.
# day1-2 = warmup ONLY (no posting) so the fresh account is NOT poisoned/cooled/polluted by
# early posting. instagrapi CAN post (proven) — the failure mode was posting too early, not the
# poster. From day3 the account is warm enough to post daily 100%. First live posts stay
# NON-COMMERCIAL (no bio link, pure-info caption) to measure reach before adding a commercial
# link. COMMERCIAL_OK only after the reach-check step writes the healthy marker.
MODE_FLAG=""   # empty = dry (build video+copy only, publish nothing). --live from day>=3.
COMMERCIAL_MARKER="$HOME/.openclaw/state/.capafy-ig-reach-healthy"
if [ "${WARM_DAY:-0}" -ge 3 ]; then MODE_FLAG="--live"; fi
COMMERCIAL_OK="no"; [ -f "$COMMERCIAL_MARKER" ] && COMMERCIAL_OK="yes"
echo "warmup day-count=$WARM_DAY -> post mode: ${MODE_FLAG:-DRY} | commercial_ok=$COMMERCIAL_OK" >>"$LOG"

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

PROMPT='You are the Anicca Capafy IG-marketing loop (headless; goal = drive Capafy skill subscribers via Instagram Reels; revenue → Dais bank; human NOT in loop). Triggered by launchd (ai.anicca.capafy-ig-marketing-daily). You post to the AI-OWNED IG account @'"$IG_HANDLE"' (NEVER a Dais-personal account). The bash caller passed the post mode as MODE='"${MODE_FLAG:-DRY}"'. If MODE=DRY you do NOT publish this pass (the working poster is instagrapi, which has no dry mode — so DRY simply means: build the video + copy, then stop before STEP4, publishing nothing). Only if MODE=--live do you actually publish via instagrapi (STEP4).

STEP1 SELECT (tool): python3 ~/anicca/skills/earn/capafy-marketing/scripts/select_listing.py  → one online Capafy listing {agent_id,name,desc,url}.

COMMERCIAL GATE: commercial_ok='"$COMMERCIAL_OK"'. While commercial_ok=no, EVERY post is NON-COMMERCIAL: pure-info caption ("here is a Claude skill that does X" — NO "buy/subscribe/link in bio" push), and DO NOT add any Capafy link to the bio yet. This avoids the day-0 commercial-link suspension trigger while we measure reach. Only when commercial_ok=yes do you add the bio link + a soft CTA.

STEP2 COPY (YOUR judgment, no template): from name+desc write (a) a Reel caption (hook + what the skill does; if commercial_ok=yes add a soft "link in bio" CTA, else pure info, NO push, NO link in caption/comment — IG comment links are unclickable) and (b) a one-line on-screen hook for the video. Before writing, if ~/anicca/skills/earn/capafy-marketing/IG_BEST_PRACTICES.md exists, read it and follow its measured winning patterns; if absent, use your normal judgment.

STEP3 VIDEO (B3, faceless engine): write YOUR 30-45s voiceover script about THIS listing (hook + what it kills + what it does + "link in bio" CTA; topic = the skill, not generic finance) to a file, then build ONE 9:16 mp4 with:  BROLL_QUERY="<a b-roll query that matches the listing category>" bash ~/.claude/skills/faceless-money-factory/scripts/run-daily.sh <your-script-file> en  . ★Set BROLL_QUERY to topic-appropriate stock footage, NOT the finance default (e.g. YouTube Script Writer -> "video editing laptop creator", Lead Magnet Generator -> "marketing office laptop", a coding skill -> "programmer typing code"). Without BROLL_QUERY the engine falls back to finance "money" b-roll, which mismatches a Capafy skill.★ Gate: only proceed if the mp4 exists and is 1080x1920 9:16.

STEP4 POST (B4, instagrapi — the ONLY poster, proven working reel/Da7VQY8MIOK 2026-07-18):  CDP_PORT=9222 ~/.cache/instagrapi-venv/bin/python ~/anicca/skills/earn/clip/scripts/instagrapi_post.py --video <mp4> --caption-file <caption> --handle '"$IG_HANDLE"' --port 9222 --live  . It pulls the CloakBrowser'"'"'s logged-in sessionid (tier2, session_owner=browser) so no fresh-login challenge, uploads via the private API, and prints JSON with outcome=published + post_url (the reel URL). Only run this when MODE=--live; if MODE=DRY do NOT post (instagrapi has no dry). If it returns ChallengeRequired, the account is poisoned — STOP and report, never retry-login. Capture post_url.

STEP5 BIO: set the profile Website to the all-skills landing URL '"$LANDING_URL"' ONLY when commercial_ok=yes AND MODE=--live. Never use an individual Capafy listing URL for the profile Website. While commercial_ok=no, DO NOT touch the bio (non-commercial phase — we are only measuring reach). Never in DRY.

STEP6 VERIFY + LEDGER + REACH: on --live, confirm the Reel is publicly visible, record its URL in ~/.openclaw/state/capafy-marketing-ig-ledger.jsonl (platform=ig, reel_url=...) + post time in the rotation ledger (platform=ig). Then MEASURE REACH (the real shadowban test): run  python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_metrics.py  to snapshot views/likes/comments, and (a few hours after a post, or on the NEXT day pass) judge: is reach healthy for a fresh account (getting non-zero views/plays, appearing when you search its own hashtags)? If reach looks HEALTHY on the accumulated snapshots, write the marker  touch ~/.openclaw/state/.capafy-ig-reach-healthy  (this flips commercial_ok=yes → next posts add the bio link + soft CTA). If reach looks SHADOWBANNED (near-zero views across multiple posts, not in hashtag/explore), do NOT write the marker — instead report it so a human/next pass decides account-rebuild vs warmup-extend. Never fabricate reach numbers. On DRY, just record the flow reached share cleanly.
After REACH, run python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_reflect.py exactly once to refresh IG_BEST_PRACTICES.md from real ledger + metrics data for the next pass.

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
