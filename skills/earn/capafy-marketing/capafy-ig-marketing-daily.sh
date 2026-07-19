#!/usr/bin/env bash
# capafy-ig-marketing-daily.sh — B1-B4 IG line — DETERMINISTIC daily trigger for the Capafy
# Instagram marketing loop. Active IG account comes only from clip-accounts-capafy.json.
# launchd -> this script -> headless `claude -p`: provision-or-selector -> copy -> faceless video
# (B3) -> instagrapi post (B4) -> ledger -> report. Copy is agent judgment, NEVER hardcoded here.
# LaunchAgent: ai.anicca.capafy-ig-marketing-daily at 16:00 local; stdout/stderr use LOG below.
#
# ★ Fresh account: day 1-2 warmup ONLY. LIVE starts on day 3. Initial posts stay
#   NON-COMMERCIAL until the reach-health marker exists. ★
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=account_state.sh
. "$SCRIPT_DIR/account_state.sh"
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
LOG="$HOME/.openclaw/logs/capafy-ig-marketing-daily.log"
ROT="$HOME/.openclaw/state/capafy-marketing-rotation.jsonl"
ACCOUNTS_FILE="$(capafy_ig_accounts_file)"
IG_HANDLE="$(resolve_capafy_ig_handle "$ACCOUNTS_FILE")"
IG_PORT="$(resolve_capafy_ig_port "$ACCOUNTS_FILE")"
WARMUP_STATE="$HOME/.cloak/ig-warmup-${IG_HANDLE:-no-active-account}.json"
LANDING_URL="https://capafy-skills-daily.netlify.app"
LANDING_SITE_ID="41c8e52e-b163-442a-84ff-fd866269bf6c"
COOKED_MARKER="$HOME/.openclaw/state/.capafy-ig-account-cooked"
PROVISION_REASON="$(capafy_ig_provision_reason "$IG_HANDLE" "$COOKED_MARKER")"
PROVISION_NEEDED="no"
[ -n "$PROVISION_REASON" ] && PROVISION_NEEDED="yes"
mkdir -p "$(dirname "$LOG")" "$(dirname "$ROT")"
echo "=== capafy-ig-marketing-daily run $(date '+%F %T %Z') ===" >>"$LOG"
echo "account_state=$ACCOUNTS_FILE active_handle=${IG_HANDLE:-none} active_port=${IG_PORT:-none} provision_needed=$PROVISION_NEEDED reason=${PROVISION_REASON:-none}" >>"$LOG"
if [ "${CAPAFY_IG_PROBE_ONLY:-0}" = "1" ]; then
  printf 'active_handle=%s provision_needed=%s reason=%s\n' \
    "${IG_HANDLE:-none}" "$PROVISION_NEEDED" "${PROVISION_REASON:-none}"
  exit 0
fi

# ── IG metrics/attribution run EVERY day (deterministic; IG variants, utm_source=instagram_bio) ──
/opt/homebrew/bin/python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_metrics.py >>"$LOG" 2>&1 || echo "ig_metrics failed (non-fatal)" >>"$LOG"

# ── All-skills bio landing refreshes on EVERY pass, including cadence no-op days. ──
/opt/homebrew/bin/python3 "$HOME/anicca/skills/earn/capafy-marketing/scripts/build_landing.py" >>"$LOG" 2>&1 && netlify deploy --prod --dir "$HOME/anicca/skills/earn/capafy-marketing/site" --site "$LANDING_SITE_ID" >>"$LOG" 2>&1 || echo "landing regenerate/deploy failed (non-fatal)" >>"$LOG"

# ── WARMUP GATE: decide DRY vs LIVE. Day 1-2 DRY; LIVE from day 3. ──
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
if [ "$PROVISION_NEEDED" = "no" ] && [ -f "$ROT" ] && /opt/homebrew/bin/python3 - "$ROT" <<'PY'
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

PROMPT='You are the Anicca Capafy IG-marketing loop (headless; goal = drive Capafy skill subscribers via Instagram Reels; revenue → Dais bank; human NOT in loop). Triggered by launchd (ai.anicca.capafy-ig-marketing-daily). Active account SSOT is '"$ACCOUNTS_FILE"'; resolved handle='"${IG_HANDLE:-none}"', port='"${IG_PORT:-none}"'. NEVER use a Dais-personal account. The bash caller passed MODE='"${MODE_FLAG:-DRY}"'. If MODE=DRY, do not publish. Only MODE=--live may publish.

PROVISION GATE: provision_needed='"$PROVISION_NEEDED"', reason='"${PROVISION_REASON:-none}"'. When provision_needed=yes, run STEP PROVISION below and STOP THIS PASS after its success/failure report. Do not run STEP1-STEP7, do not build content, do not edit bio, and do not publish. A newly provisioned account is day 1 and MUST receive zero posts until warmup reaches day 3.

STEP PROVISION (copied and tweaked from ~/anicca/skills/earn/clip/clip_pass.sh STEP PROVISION; 1-loop-1-account, replace-on-cold, ZERO human): Read ~/.claude/skills/ig-account-create/SKILL.md and follow its proven email-only flow. Create one brand-new Capafy IG account on residential home IP with NO proxy. Use a fresh Gmail plus-address keiodaisuke+capafy<random-tag>@gmail.com. Read the 6-digit OTP with: gog gmail search --account redacted@example.invalid "instagram in:anywhere newer_than:1h" --max 3 --plain. The in:anywhere term is mandatory because OTP can land in spam. Do not use phone flow unless Instagram forces it; if phone or text-CAPTCHA is forced, stop and report provision-blocked:<reason>. BROWSER ISOLATION: drive the existing CloakBrowser daily-driver on CDP :9222 only through cdp_incognito.py in a NEW isolated context and NEW tab. Never navigate, reuse, or close any pre-existing :9222 tab; gig/clip tabs belong to other loops. Fill fields with trusted CDP typing, set DOB with trusted clicks, create a unique handle, and run setup_profile.py with a $0 PIL monogram avatar plus one-line Claude-skills bio containing NO link. Save signup credentials to ~/.cloak/ig-<handle>.json.

DURABLE GOLDEN SESSION — mandatory make-or-break step copied from clip: the browser sessionid is ephemeral and dies when isolated context closes. NEVER call login_by_sessionid and never save browser sessionid as the durable session. Instead use ~/.cache/instagrapi-venv/bin/python and the fresh password from ~/.cloak/ig-<handle>.json: from instagrapi import Client; cl=Client(); cl.login(<username>, <pw>) exactly once as the first fresh-account login; feed=cl.get_timeline_feed(); require real returned data; cl.dump_settings("~/.cloak/instagrapi-<handle>.json"). This is the required Client().login flow. Read the settings file back. Feed verification, not file existence, proves session alive.

STATE WRITE: use '"$ACCOUNTS_FILE"' only. Preserve every existing row. Choose a free dedicated port that is neither 9222 nor 9223 after checking lsof, and a unique profile such as capafy-mkt-<tag>. On confirmed get_timeline_feed success, atomically append {"handle":"<handle>","profile":"<profile>","port":<free-port>,"lang":"en","status":"warming","session_owner":"instagrapi","instance":"capafy","created":"<today YYYY-MM-DD>","started_warming":"<today YYYY-MM-DD>"}. If reason=cooked-marker, first mark prior ready/warming rows poisoned_manual_backup with poisoned_reason and poisoned_at so only the new appended row is active. Parse the full JSON after writing, confirm row count increased by one and the final row matches the new handle, then remove '"$COOKED_MARKER"' and remove ~/.openclaw/state/.capafy-ig-reach-healthy so the replacement account restarts non-commercial reach validation. Send Telegram chat 0000000000 a success message containing handle, port, feed_verified_alive=yes, status_written=warming, and that this pass posted nothing.

FAILURE: if signup, Client().login, get_timeline_feed(), dump_settings, or state verification fails, append a best-effort row with status=provision_failed and the failure reason, ensure '"$COOKED_MARKER"' remains present, and send Telegram chat 0000000000 exactly one provision-blocked:<reason> report. Never label ready/warming and never remove the marker on failure. Touch ~/.openclaw/state/.capafy-ig-marketing-last-pass and stop this pass.

STEP1 SELECT (tool): python3 ~/anicca/skills/earn/capafy-marketing/scripts/select_listing.py  → one online Capafy listing {agent_id,name,desc,url}.

COMMERCIAL GATE: commercial_ok='"$COMMERCIAL_OK"'. While commercial_ok=no, EVERY post is NON-COMMERCIAL: pure-info caption ("here is a Claude skill that does X" — NO "buy/subscribe/link in bio" push), and DO NOT add any Capafy link to the bio yet. This avoids the day-0 commercial-link suspension trigger while we measure reach. Only when commercial_ok=yes do you add the bio link + a soft CTA.

STEP2 COPY (YOUR judgment, no template): from name+desc write (a) a Reel caption (hook + what the skill does; if commercial_ok=yes add a soft "link in bio" CTA, else pure info, NO push, NO link in caption/comment — IG comment links are unclickable) and (b) a one-line on-screen hook for the video. Before writing, if ~/anicca/skills/earn/capafy-marketing/IG_BEST_PRACTICES.md exists, read it and follow its measured winning patterns; if absent, use your normal judgment.

STEP3 VIDEO (B3, faceless engine): write YOUR 30-45s voiceover script about THIS listing (hook + what it kills + what it does + "link in bio" CTA; topic = the skill, not generic finance) to a file, then build ONE 9:16 mp4 with:  BROLL_QUERY="<a b-roll query that matches the listing category>" bash ~/.claude/skills/faceless-money-factory/scripts/run-daily.sh <your-script-file> en  . ★Set BROLL_QUERY to topic-appropriate stock footage, NOT the finance default (e.g. YouTube Script Writer -> "video editing laptop creator", Lead Magnet Generator -> "marketing office laptop", a coding skill -> "programmer typing code"). Without BROLL_QUERY the engine falls back to finance "money" b-roll, which mismatches a Capafy skill.★ Gate: only proceed if the mp4 exists and is 1080x1920 9:16.

STEP4 POST (B4, shared instagrapi poster): CDP_PORT='"$IG_PORT"' ~/.cache/instagrapi-venv/bin/python ~/anicca/skills/earn/clip/scripts/instagrapi_post.py --video <mp4> --caption-file <caption> --handle '"$IG_HANDLE"' --port '"$IG_PORT"' --accounts-path '"$ACCOUNTS_FILE"' --live . The poster must load ~/.cloak/instagrapi-'"$IG_HANDLE"'.json as tier1 and use session_owner=instagrapi from the supplied Capafy state, which forbids browser sessionid fallback. Only run when MODE=--live; if MODE=DRY do not post. If it returns ChallengeRequired, stop and report; never retry-login. Capture post_url.

STEP5 BIO: set the profile Website to the all-skills landing URL '"$LANDING_URL"' ONLY when commercial_ok=yes AND MODE=--live. Never use an individual Capafy listing URL for the profile Website. While commercial_ok=no, DO NOT touch the bio (non-commercial phase — we are only measuring reach). Never in DRY.

STEP6 VERIFY + LEDGER + REACH: on --live, confirm the Reel is publicly visible, record its URL in ~/.openclaw/state/capafy-marketing-ig-ledger.jsonl (platform=ig, reel_url=...) + post time in the rotation ledger (platform=ig). Then MEASURE REACH (the real shadowban test): run  python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_metrics.py  to snapshot views/likes/comments, and (a few hours after a post, or on the NEXT day pass) judge: is reach healthy for a fresh account (getting non-zero views/plays, appearing when you search its own hashtags)? If reach looks HEALTHY on the accumulated snapshots, write the marker  touch ~/.openclaw/state/.capafy-ig-reach-healthy  (this flips commercial_ok=yes → next posts add the bio link + soft CTA). If reach looks SHADOWBANNED (near-zero views across multiple posts, not in hashtag/explore), do NOT write the marker — instead report it so a human/next pass decides account-rebuild vs warmup-extend. Never fabricate reach numbers. On DRY, just record the flow reached share cleanly.
After REACH, run python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_reflect.py exactly once to refresh IG_BEST_PRACTICES.md from real ledger + metrics data for the next pass.

STEP7 REPORT TO DAIS — MANDATORY every pass (Dais wants to SEE the actual output, not a summary). Send to telegram chat 0000000000 via openclaw message send:
  (a) the VIDEO itself as media:  openclaw message send --channel telegram --target 0000000000 --media <the mp4 path> --force-document --message "<caption below>" --json  (--force-document keeps it uncompressed; if the video attach fails, fall back to sending a thumbnail/first-frame png + the message).
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
