#!/usr/bin/env bash
# capafy-ig-marketing-daily.sh — B1-B4 IG line — DETERMINISTIC daily trigger for the Capafy
# Instagram marketing loop. Active IG account comes only from clip-accounts-capafy.json.
# launchd -> this script -> shared agent runner: provision-or-selector -> copy -> faceless video
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
MARKETING_ENGINE_DIR="$SCRIPT_DIR/../marketing-engine"
# shellcheck source=../marketing-engine/provision_prompt.sh
. "$MARKETING_ENGINE_DIR/provision_prompt.sh"
# shellcheck source=../marketing-engine/load_manifest.sh
. "$MARKETING_ENGINE_DIR/load_manifest.sh"
me_load_manifest "${MKT_MANIFEST:-capafy}" || true   # per-loop config — engine stays shared; set MKT_MANIFEST to run another loop on this same engine
INSTANCE="${MKT_INSTANCE:-capafy}"   # state namespace; capafy -> identical paths, other loops -> own
RUN_AGENT="$MARKETING_ENGINE_DIR/run_agent.sh"
LOG="$HOME/.openclaw/logs/${INSTANCE}-ig-marketing-daily.log"
ROT="$HOME/.openclaw/state/${INSTANCE}-marketing-rotation.jsonl"
ACCOUNTS_FILE="$(capafy_ig_accounts_file)"
IG_HANDLE="$(resolve_capafy_ig_handle "$ACCOUNTS_FILE")"
IG_PORT="$(resolve_capafy_ig_port "$ACCOUNTS_FILE")"
IG_STARTED_WARMING="$(resolve_capafy_ig_started_warming "$ACCOUNTS_FILE")"
LANDING_URL="${MKT_BIO_LINK:-https://capafy-skills-daily.netlify.app}"
LANDING_SITE_ID="${MKT_LANDING_SITE_ID:-41c8e52e-b163-442a-84ff-fd866269bf6c}"
COOKED_MARKER="$HOME/.openclaw/state/.${INSTANCE}-ig-account-cooked"
PROVISION_REASON="$(capafy_ig_provision_reason "$IG_HANDLE" "$COOKED_MARKER")"
PROVISION_NEEDED="no"
[ -n "$PROVISION_REASON" ] && PROVISION_NEEDED="yes"
mkdir -p "$(dirname "$LOG")" "$(dirname "$ROT")"
# ── BROWSER ISOLATION (same lease system clip uses): take our own isolated context on :9222 so
#    capafy never churns against clip/gig/Dais tabs on the shared daily-driver (churn = poison). ──
BROWSER_SCRIPTS="$SCRIPT_DIR/../../browser/scripts"
PROVISION_BROWSER="$SCRIPT_DIR/../../browser/ensure_provision_browser.sh"
PROVISION_IDENTITY="${MKT_PROVISION_BROWSER_IDENTITY:-instagram:capafy-provision}"
BROWSER_GUARD="${AI_BROWSER_GUARD:-$HOME/.config/ai/bin/browser-guard.sh}"
ALERT_FILE="$HOME/.openclaw/state/.${INSTANCE}-ig-marketing-ALERT"
CAPAFY_LEASE="capafy-$$"; export CAPAFY_LEASE
PROVISION_LEASED="no"
cleanup() {
  python3 "$BROWSER_SCRIPTS/cdp_context_lease.py" release "$CAPAFY_LEASE" >/dev/null 2>&1
  [ "$PROVISION_LEASED" = "yes" ] && bash "$BROWSER_GUARD" release "$PROVISION_IDENTITY" >/dev/null 2>&1
  return 0
}
trap cleanup EXIT
python3 "$BROWSER_SCRIPTS/cdp_context_lease.py" acquire "$CAPAFY_LEASE" >/dev/null 2>&1 || true
# ── LOUD FAILURE (fixes the 11-day silence 2026-07-19..07-30) ─────────────────────────────────────
# The old script wrote a provision_failed row and exited 0, so launchd, the logs and every dashboard
# reported a clean pass while the loop had in fact posted nothing for 11 days. A pass that could not
# do its job must SAY SO in its exit code, because rc=0 is the only thing an unattended supervisor
# reads. The telemetry row stays (it is useful history); the lie about rc does not.
alert_and_die() {
  local reason="$1"
  printf '%s %s\n' "$(date '+%F %T %Z')" "$reason" >>"$ALERT_FILE"
  echo "ALERT: $reason" >>"$LOG"
  bash "$SCRIPT_DIR/../../_shared/send-telegram.sh" \
    "🚨 ${INSTANCE} IG marketing BLOCKED: ${reason} (pass exited non-zero; see $LOG)" >>"$LOG" 2>&1 || true
  exit 1
}
echo "=== capafy-ig-marketing-daily run $(date '+%F %T %Z') ===" >>"$LOG"
echo "account_state=$ACCOUNTS_FILE active_handle=${IG_HANDLE:-none} active_port=${IG_PORT:-none} provision_needed=$PROVISION_NEEDED reason=${PROVISION_REASON:-none}" >>"$LOG"
if [ "${CAPAFY_IG_PROBE_ONLY:-0}" = "1" ]; then
  printf 'active_handle=%s provision_needed=%s reason=%s\n' \
    "${IG_HANDLE:-none}" "$PROVISION_NEEDED" "${PROVISION_REASON:-none}"
  exit 0
fi

# ── IG metrics/attribution run EVERY day (deterministic; IG variants, utm_source=instagram_bio) ──
/opt/homebrew/bin/python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_metrics.py >>"$LOG" 2>&1 || echo "ig_metrics failed (non-fatal)" >>"$LOG"
/opt/homebrew/bin/python3 ~/anicca/skills/earn/capafy-marketing/scripts/pull_attribution.py >>"$LOG" 2>&1 || echo "pull_attribution failed (non-fatal)" >>"$LOG"

# ── All-skills bio landing refreshes on EVERY pass, including cadence no-op days. ──
# netlify-cli writes ./.netlify relative to cwd; launchd starts at / (no WorkingDirectory) -> mkdir '//.netlify' ENOENT. cd keeps it inside the skill dir.
/opt/homebrew/bin/python3 "$HOME/anicca/skills/earn/capafy-marketing/scripts/build_landing.py" >>"$LOG" 2>&1 && ( cd "$HOME/anicca/skills/earn/capafy-marketing" && netlify deploy --prod --dir "$HOME/anicca/skills/earn/capafy-marketing/site" --site "$LANDING_SITE_ID" ) >>"$LOG" 2>&1 || echo "landing regenerate/deploy failed (non-fatal)" >>"$LOG"

# ── WARMUP GATE: decide DRY vs LIVE. Creation date is day1; day1-2 DRY; LIVE from day3. ──
WARM_DAY="$(capafy_ig_warming_day "$IG_STARTED_WARMING")"
# ★STRATEGY (2026-07-19 Dais, WHOLE marketing engine): warm up for 2 days, post from DAY 3.
# day1-2 = warmup ONLY (no posting) so the fresh account is NOT poisoned/cooled/polluted by
# early posting. instagrapi CAN post (proven) — the failure mode was posting too early, not the
# poster. From day3 the account is warm enough to post daily 100%. First live posts stay
# NON-COMMERCIAL (no bio link, pure-info caption) to measure reach before adding a commercial
# link. COMMERCIAL_OK only after the reach-check step writes the healthy marker.
MODE_FLAG=""   # empty = dry (build video+copy only, publish nothing). --live from day>=3.
COMMERCIAL_MARKER="$HOME/.openclaw/state/.${INSTANCE}-ig-reach-healthy"
LAST_PASS_MARKER="$HOME/.openclaw/state/.${INSTANCE}-ig-marketing-last-pass"
IG_LEDGER="$HOME/.openclaw/state/${INSTANCE}-marketing-ig-ledger.jsonl"
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
  touch "$LAST_PASS_MARKER" 2>/dev/null || true
  exit 0
fi

# ── PROVISIONING BROWSER (dynamic port, actually launched) ────────────────────────────────────────
# A port is not a browser. The previous version passed a hardcoded IG_PROVISION_PORT=9332 that no
# process in any skill ever listened on, so the agent correctly refused at preflight every single day.
# Now the dedicated CloakBrowser is really launched (own clean profile, own launchd owner, port handed
# out by the kernel and read back from DevToolsActivePort) and the port is only known at runtime.
PROVISION_PORT=""
if [ "$PROVISION_NEEDED" = "yes" ]; then
  PROVISION_CDP_URL="$(bash "$PROVISION_BROWSER" "$PROVISION_IDENTITY" 2>>"$LOG")" \
    || alert_and_die "provision browser unavailable for identity $PROVISION_IDENTITY"
  PROVISION_LEASED="yes"
  PROVISION_PORT="${PROVISION_CDP_URL##*:}"
  case "$PROVISION_PORT" in ''|*[!0-9]*) alert_and_die "provision browser returned no usable port ('$PROVISION_CDP_URL')" ;; esac
  echo "provision browser ready identity=$PROVISION_IDENTITY cdp=$PROVISION_CDP_URL port=$PROVISION_PORT" >>"$LOG"
else
  # The SAME staleness trap applies to the account we already have: its session lives in that
  # dedicated profile, and its port is re-assigned by the kernel on every browser restart. A port
  # stored in the account row is therefore a snapshot, never an address. When the row names a browser
  # identity, bring that browser up and take the LIVE port from it; the stored one is only a hint.
  ACCOUNT_BROWSER_IDENTITY="$(_resolve_capafy_ig_account_field "$ACCOUNTS_FILE" browser_identity)"
  if [ -n "$ACCOUNT_BROWSER_IDENTITY" ]; then
    ACCOUNT_CDP_URL="$(bash "$PROVISION_BROWSER" "$ACCOUNT_BROWSER_IDENTITY" 2>>"$LOG")" \
      || alert_and_die "account browser unavailable for identity $ACCOUNT_BROWSER_IDENTITY (handle ${IG_HANDLE:-none})"
    PROVISION_IDENTITY="$ACCOUNT_BROWSER_IDENTITY"   # so the EXIT trap releases the lease we took
    PROVISION_LEASED="yes"
    LIVE_PORT="${ACCOUNT_CDP_URL##*:}"
    case "$LIVE_PORT" in
      ''|*[!0-9]*) alert_and_die "account browser returned no usable port ('$ACCOUNT_CDP_URL')" ;;
      *) [ "$LIVE_PORT" = "${IG_PORT:-}" ] || echo "live port for $ACCOUNT_BROWSER_IDENTITY is $LIVE_PORT (state row says ${IG_PORT:-none}) — using the live one" >>"$LOG"
         IG_PORT="$LIVE_PORT" ;;
    esac
  fi
fi

PROVISION_PROMPT="no provisioning this pass (provision_needed=no)"
if [ "$PROVISION_NEEDED" = "yes" ]; then
PROVISION_PROMPT="$(
  IG_PROVISION_ACCOUNT_STATE_FILE="$ACCOUNTS_FILE" \
  IG_PROVISION_HANDLE_PREFIX="${MKT_HANDLE_PREFIX:-capafy}" \
  IG_PROVISION_INSTANCE="${MKT_INSTANCE:-capafy}" \
  IG_PROVISION_GMAIL_PLUS_TAG_PREFIX="${MKT_GMAIL_PLUS_TAG_PREFIX:-capafy}" \
  IG_PROVISION_BIO_TEXT="${MKT_BIO_TEXT:-one-line Claude-skills bio, NO link}" \
  IG_PROVISION_PORT="$PROVISION_PORT" \
  IG_PROVISION_CONTEXT_ID="$CAPAFY_LEASE" \
  IG_PROVISION_BROWSER_INSTRUCTIONS="The dedicated CloakBrowser for identity '$PROVISION_IDENTITY' is ALREADY RUNNING and leased for you at $PROVISION_CDP_URL (profile ~/.cloak/profiles/capafy-mkt-provision, port assigned dynamically at launch). Do NOT launch a browser yourself and do NOT look for any other port: attach to $PROVISION_CDP_URL and do all signup there. Never use or log in through the shared daily-driver browser (identity interactive:dais) or the gig browser (identity coconala:kosuke)." \
  IG_PROVISION_PROFILE_PREFIX="${MKT_PROFILE_PREFIX:-capafy-mkt}" \
  IG_PROVISION_COOKED_MARKER="$COOKED_MARKER" \
  IG_PROVISION_REASON="${PROVISION_REASON:-none}" \
  IG_PROVISION_REACH_MARKER="$COMMERCIAL_MARKER" \
  IG_PROVISION_LAST_PASS_MARKER="$LAST_PASS_MARKER" \
  IG_PROVISION_TELEGRAM_TARGET="8547730585" \
  render_ig_provision_prompt
)" || alert_and_die "provision prompt render failed (isolation preflight refused port=$PROVISION_PORT context=$CAPAFY_LEASE)"
[ -n "$PROVISION_PROMPT" ] || alert_and_die "provision prompt rendered empty — refusing to run a provisioning pass with no instructions"
fi

PROMPT='You are the Anicca Capafy IG-marketing loop (headless; goal = drive Capafy skill subscribers via Instagram Reels; revenue → Dais bank; human NOT in loop). Triggered by launchd (ai.anicca.capafy-ig-marketing-daily). Active account SSOT is '"$ACCOUNTS_FILE"'; resolved handle='"${IG_HANDLE:-none}"', port='"${IG_PORT:-none}"'. NEVER use a Dais-personal account. The bash caller passed MODE='"${MODE_FLAG:-DRY}"'. If MODE=DRY, do not publish. Only MODE=--live may publish.

PROVISION GATE: provision_needed='"$PROVISION_NEEDED"', reason='"${PROVISION_REASON:-none}"'. When provision_needed=yes, run STEP PROVISION below and STOP THIS PASS after its success/failure report. Do not run STEP1-STEP7, do not build content, do not edit bio, and do not publish. A newly provisioned account is day 1 and MUST receive zero posts until warmup reaches day 3.

'"$PROVISION_PROMPT"'

STEP1 SELECT (tool): python3 ~/anicca/skills/earn/capafy-marketing/scripts/select_listing.py  → one online Capafy listing {agent_id,name,desc,url}.

COMMERCIAL GATE: commercial_ok='"$COMMERCIAL_OK"'. While commercial_ok=no, EVERY post is NON-COMMERCIAL: pure-info caption ("here is a Claude skill that does X" — NO "buy/subscribe/link in bio" push), and DO NOT add any Capafy link to the bio yet. This avoids the day-0 commercial-link suspension trigger while we measure reach. Only when commercial_ok=yes do you add the bio link + a soft CTA.

STEP2 COPY (YOUR judgment, no template): from name+desc write (a) a Reel caption (hook + what the skill does; if commercial_ok=yes add a soft "link in bio" CTA, else pure info, NO push, NO link in caption/comment — IG comment links are unclickable) and (b) a one-line on-screen hook for the video. Before writing, if ~/anicca/skills/earn/capafy-marketing/IG_BEST_PRACTICES.md exists, read it and follow its measured winning patterns; if absent, use your normal judgment.

STEP3 VIDEO (B3, faceless engine): write YOUR 30-45s voiceover script about THIS listing (hook + what it kills + what it does + "link in bio" CTA; topic = the skill, not generic finance) to a file, then build ONE 9:16 mp4 with:  BROLL_QUERY="<a b-roll query that matches the listing category>" bash ~/.claude/skills/faceless-money-factory/scripts/run-daily.sh <your-script-file> en  . ★Set BROLL_QUERY to topic-appropriate stock footage, NOT the finance default (e.g. YouTube Script Writer -> "video editing laptop creator", Lead Magnet Generator -> "marketing office laptop", a coding skill -> "programmer typing code"). Without BROLL_QUERY the engine falls back to finance "money" b-roll, which mismatches a Capafy skill.★ Gate: only proceed if the mp4 exists and is 1080x1920 9:16.

STEP4 POST (B4, shared instagrapi poster): CDP_PORT='"$IG_PORT"' ~/.cache/instagrapi-venv/bin/python ~/anicca/skills/earn/marketing-engine/poster.py --video <mp4> --caption-file <caption> --handle '"$IG_HANDLE"' --port '"$IG_PORT"' --accounts-path '"$ACCOUNTS_FILE"' --live . The poster must load ~/.cloak/instagrapi-'"$IG_HANDLE"'.json as tier1 and use session_owner=instagrapi from the supplied Capafy state, which forbids browser sessionid fallback. Only run when MODE=--live; if MODE=DRY do not post. If it returns ChallengeRequired, stop and report; never retry-login. Capture post_url.

STEP5 BIO (deterministic — do NOT hand-drive the profile UI): set the profile Website to the all-skills landing URL '"$LANDING_URL"' ONLY when commercial_ok=yes AND MODE=--live. Use the PROVEN script (it sets the Website via CDP AND persistence-verifies the value survived save+reload): open the account edit page in THIS pass isolated lease context and run  python3 ~/.agents/skills/ig-account-create/scripts/setup_profile.py --tid <the lease tab TID for '"$IG_HANDLE"'> --website '"$LANDING_URL"' --username '"$IG_HANDLE"'  . It prints website_set=true only if IG kept the FULL link; if website_set=false, IG stripped it — report that and do NOT claim the bio link is installed (never fabricate). Never use an individual Capafy listing URL for the Website (always the all-skills landing). While commercial_ok=no, DO NOT touch the bio (non-commercial reach-measuring phase). Never in DRY.

STEP6 VERIFY + LEDGER + REACH: on --live, confirm the Reel is publicly visible, record its URL in '"$IG_LEDGER"' (platform=ig, reel_url=...) + post time in the rotation ledger (platform=ig). Then MEASURE REACH (the real shadowban test): run  python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_metrics.py  to snapshot views/likes/comments, and (a few hours after a post, or on the NEXT day pass) judge: is reach healthy for a fresh account (getting non-zero views/plays, appearing when you search its own hashtags)? If reach looks HEALTHY on the accumulated snapshots, write the marker  touch '"$COMMERCIAL_MARKER"'  (this flips commercial_ok=yes → next posts add the bio link + soft CTA). If reach looks SHADOWBANNED (near-zero views across multiple posts, not in hashtag/explore), do NOT write the marker — instead report it so a human/next pass decides account-rebuild vs warmup-extend. Never fabricate reach numbers. On DRY, just record the flow reached share cleanly.
After REACH, run python3 ~/anicca/skills/earn/capafy-marketing/scripts/ig_reflect.py exactly once to refresh IG_BEST_PRACTICES.md from real ledger + metrics data for the next pass.

STEP7 REPORT TO DAIS — MANDATORY every pass (Dais wants to SEE the actual output, not a summary). Send to telegram chat 8547730585 via openclaw message send:
  (a) the VIDEO itself as media:  openclaw message send --channel telegram --target 8547730585 --media <the mp4 path> --force-document --message "<caption below>" --json  (--force-document keeps it uncompressed; if the video attach fails, fall back to sending a thumbnail/first-frame png + the message).
  (b) the message body MUST contain: the promoted listing name + agent_id, the mode (DRY or LIVE), the Reel public URL (or "DRY — not posted" on a dry pass), and the FULL caption text verbatim (the exact caption you wrote for the Reel).
  On a DRY pass you STILL send this once (video + full caption + which listing) so Dais can review the creative before go-live — you just do NOT publish to IG. Confirm the send returned a real message id; also AgentMail via loop-report if that path exists.

FINALLY touch '"$LAST_PASS_MARKER"'. A DRY pass, a deferred cadence pass, or a caught error is a clean finish, never a hang.'

EVIDENCE_DIR="$HOME/.openclaw/state/agent-runner-evidence/${INSTANCE}-ig-marketing/$(date +%s)-$$"
printf '%s\n' "$PROMPT" | "$RUN_AGENT" \
  --task-class tool-agent \
  --evidence-dir "$EVIDENCE_DIR" \
  --task-label "${INSTANCE}-ig-marketing-daily" \
  --loop capafy >>"$LOG" 2>&1
RC=$?
echo "=== capafy-ig-marketing-daily done rc=$RC $(date '+%F %T %Z') ===" >>"$LOG"
touch "$LAST_PASS_MARKER" 2>/dev/null || true

# ── OUTCOME GATE ──────────────────────────────────────────────────────────────────────────────────
# The agent can finish with status=ok while having accomplished nothing (measured: 8 consecutive
# "ok" passes whose only action was appending a provision_failed row). So the SHELL, not the agent,
# decides whether this pass succeeded, by re-reading the state the pass was supposed to change.
if [ "$PROVISION_NEEDED" = "yes" ]; then
  NEW_HANDLE="$(resolve_capafy_ig_handle "$ACCOUNTS_FILE")"
  if [ -z "$NEW_HANDLE" ]; then
    alert_and_die "provisioning pass produced no usable ready/warming account (reason=${PROVISION_REASON:-none}, agent rc=$RC) — see $EVIDENCE_DIR"
  fi
  echo "provisioning succeeded: active handle now $NEW_HANDLE" >>"$LOG"
  rm -f "$ALERT_FILE" 2>/dev/null || true
fi
[ "$RC" -eq 0 ] || alert_and_die "agent runner exited rc=$RC — see $EVIDENCE_DIR"
rm -f "$ALERT_FILE" 2>/dev/null || true
exit 0
