#!/usr/bin/env bash
# clip_pass.sh — ONE clip pass as a Reflexion prompt-chain (copied from gig_pass.sh; NeurIPS 2023
# Reflexion: Actor = producer.sh + run.sh, Evaluator = clip-metrics, Self-Reflection = reflection.jsonl).
# Each LLM step is a SEPARATE bounded claude sub-call with a short focused prompt + --no-session-persistence
# (never bricks disk). PRODUCE + POST are deterministic (producer.sh makes a 1080x1920 clip; run.sh posts
# via instagrapi + reports to Telegram, respecting the cadence gate). State passes between steps through
# ~/clips/{reflection.jsonl,playbook.json,clip-metrics.jsonl}.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
C="$HOME/anicca/skills/earn/clip"
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
STATE="$HOME/clips"
mkdir -p "$STATE"
source "$C/_instance_paths.sh"   # resolves CLIP_ACCTS (respects ANICCA_INSTANCE, same as run.sh)
PY="/opt/homebrew/bin/python3"
log(){ echo "$(date '+%F %T') clip_pass: $*" >&2; }

# focused sub-call: run ONE step as its own bounded agent. --no-session-persistence + SKIP_PROMPT_HISTORY
# = write no transcript (the disk-brick source). env -u ANTHROPIC_API_KEY = subscription login.
# Auth: launchd cannot refresh the subscription OAuth token (keychain is only unlocked in an
# interactive session — observed 2026-07-16: every step died rc=1 "OAuth session expired and could
# not be refreshed"). Route sub-calls through the local CLIProxyAPI (:8317) instead, whose creds
# are plain files (~/.cli-proxy-api/) and refresh headlessly. Falls back to subscription auth if
# the key file is missing. Verified in a clean env (env -i ... RC=0) 2026-07-16.
CLIPROXY_KEY="$(cat "$HOME/.cli-proxy-api-key" 2>/dev/null || true)"
STEP_MODEL="sonnet"
if [ -n "$CLIPROXY_KEY" ]; then
  export ANTHROPIC_BASE_URL="http://127.0.0.1:8317"
  export ANTHROPIC_AUTH_TOKEN="$CLIPROXY_KEY"
  STEP_MODEL="claude-sonnet-5"   # proxy needs the explicit model id, not the "sonnet" alias
fi

step(){ # $1=label  $2=prompt
  log "STEP $1 start"
  # stdout is captured per-step (claude CLI prints errors to STDOUT, not stderr — observed
  # 2026-07-16: rc=1 with an empty stderr log) and its tail is surfaced on failure.
  local out="$HOME/.openclaw/logs/clip-step-last.out"
  CLAUDE_CODE_SKIP_PROMPT_HISTORY=1 env -u ANTHROPIC_API_KEY timeout 900 "$CLAUDE" --model "$STEP_MODEL" --dangerously-skip-permissions --no-session-persistence --add-dir "$HOME" \
    -p "You are the Anicca clip earn-core (IG @aiclipsvault, niche = AI / money / wealth). set -a; . ~/.openclaw/.env 2>/dev/null; set +a. Do EXACTLY this ONE step, fully, then stop. $2" >"$out" 2>>"$HOME/.openclaw/logs/clip-steps.err.log"
  local rc=$?
  [ "$rc" -ne 0 ] && log "STEP $1 FAIL stdout-tail: $(tail -c 800 "$out" 2>/dev/null | tr '\n' ' ')"
  log "STEP $1 done (rc=$rc)"
}

# ── deterministic prelude: single-instance lock (mkdir = atomic on macOS) + disk guard ──
LOCKD=/tmp/anicca-clip-pass.lock.d
[ -d "$LOCKD" ] && [ $(( $(date +%s) - $(stat -f %m "$LOCKD" 2>/dev/null||echo 0) )) -gt 1800 ] && rmdir "$LOCKD" 2>/dev/null
mkdir "$LOCKD" 2>/dev/null || { log "another clip pass holds the lock — exit"; exit 0; }
trap 'rmdir "$LOCKD" 2>/dev/null' EXIT
FREE=$(df -g / | tail -1 | awk '{print $4}')
[ "${FREE:-99}" -lt 5 ] && { log "disk <5GB free — abort to protect the session"; exit 0; }

# ── LEARN (Reflexion: read prior reflection + scout winners → playbook) ──
step "LEARN" "STEP LEARN (cold-start bible = docs/loop-engineering/47-cold-start-self-improvement-bible.md; IMITATE-FIRST,守破離). Read the LAST line of $STATE/reflection.jsonl to know the current PHASE and what to adjust. In the cold-start phase (own posts still noise, no self-outlier yet) you learn from WINNERS, not your own metrics: (1) scout the TOP 3-5 AI/money/wealth accounts on Instagram; (2) find each account's OUTLIER reels = posts ~3-10x above THAT account's own average views; (3) study those outliers for the levers IN THIS PRIORITY ORDER: #1 the first-3-second HOOK (this decides ~40-50%% of virality — most important by far), #2 pattern-interrupt / visual jolt, #3 thumbnail+title packaging, #4 mid retention move (~7s), #5 script structure+length, #6 posting-time/hashtags (lowest); transcribe the hook + structure. (4) MERGE the generalized winning patterns into $STATE/playbook.json {phase, general:[...], components:{hook,pattern_interrupt,thumbnail,retention_move,script,posting_time,hashtags}} (a lever seen in 3+ winner outliers => tier:core). Copy with HIGH fidelity (Shu phase). Do not invent numbers; cite the actual outlier reels you saw."

# ── AFF-FIND (MON-5: find the affiliate/product to promote → offer.json → caption link) ──
# Only runs when there is no fresh offer yet (finding an offer is not needed every pass).
if [ ! -s "$STATE/offer.json" ]; then
  step "AFF-FIND" "STEP AFF-FIND (MON-5): pick the affiliate/product this @aiclipsvault (niche AI/money/wealth) will promote, so we can monetize. Prefer, in order: (1) our OWN products (100%% margin, no signup) — the Anicca app or life manager, if a public link exists; (2) an INSTANT-signup high-commission affiliate: Digistore24 (2-min signup, no interview) or ClickBank, browse the marketplace, pick ONE offer that (a) matches AI/money/wealth, (b) has high commission (recurring SaaS 20-40%%/mo or 50-75%% RevShare digital), (c) is globally available. Use the AI's own email keiodaisuke+aiclips1@gmail.com for any signup (auto-read OTP via 'gog gmail'). Get the real affiliate LINK. Write ~/clips/offer.json = {network, offer_name, affiliate_link, commission, niche, joined:<true|false>, note}. If signup is blocked (captcha/verification you cannot pass this pass), still record the chosen offer + what is needed with joined:false. Be honest; do not invent a link."
fi

# ── WARM (deterministic bookkeeping, not an LLM step: fresh accounts (status=="warming" in
# clip-accounts.json) need passive warmup before they may post. Runs ig-account-warmer's
# warm.py once per warming account (skips + WARNs if that account's browser is down) and
# promotes warming->ready once the account clears Dais's 3-day/3-run floor. See
# warm_step.py for the full policy citation.) ──
log "WARM: warm_step.py"
"$PY" "$C/warm_step.py" "$CLIP_ACCTS" 2>&1 | while IFS= read -r line; do log "  $line"; done

# ── PROVISION (1-loop-1-acc, replace-on-cold, NO HUMAN). v38 root-cause fix: the live loop had
# NO account-creation step, so once its only account went cold (poisoned) it just gave up every
# pass ("ready_account=none" → exit) and posted nothing for days. Here the loop CREATES a fresh
# account on the home residential IP (0-phone / 0-captcha, proven with @aiclipsvault /
# @useclaudeskills) whenever no usable account exists. Skipped entirely (no LLM cost) when a
# usable account is already present. run.sh below resolves status==ready dynamically, so a newly
# provisioned ready account is picked up on THIS same pass. ──
USABLE_ACCTS=$("$PY" - "$CLIP_ACCTS" <<'PYJSON' 2>/dev/null
import json,sys
try: a=json.load(open(sys.argv[1]))
except Exception: a=[]
def ok(x):
    s=(x.get("status") or "").lower()
    if s not in ("ready","warming"): return False
    if "poison" in s or "frozen" in s or "blocked" in s: return False
    return True
print(sum(1 for x in a if ok(x)))
PYJSON
)
log "PROVISION: usable_accounts=${USABLE_ACCTS:-0}"
if [ "${USABLE_ACCTS:-0}" -eq 0 ]; then
  step "PROVISION" "STEP PROVISION (1-loop-1-acc, replace-on-cold, ZERO human): clip-accounts.json (~/.cloak/clip-accounts.json) has NO usable account (none with status ready/warming that is not poisoned/frozen/blocked), so CREATE one brand-new IG account NOW and register it as the sole active clip account. Follow the ig-account-create skill at ~/.claude/skills/ig-account-create/SKILL.md EXACTLY as proven for @aiclipsvault and @useclaudeskills. HARD RULES: (a) drive the RUNNING CloakBrowser daily-driver on CDP :9222 via cdp_incognito.py — an isolated context in a NEW tab; NEVER touch or close any existing tab. (b) residential home IP, NO proxy (a fresh/cold proxy IP triggers a phone wall — do not use one). (c) email = a fresh Gmail plus-address keiodaisuke+aiclips<random-tag>@gmail.com; read the 6-digit OTP via 'gog gmail search --account redacted@example.invalid \\\"instagram in:anywhere newer_than:1h\\\" --max 3 --plain' (OTP often lands in SPAM, so in:anywhere is required). (d) IG email-signup on this home IP needs NO phone and NO captcha — do NOT do the phone flow; if IG unexpectedly forces a phone number or a text-CAPTCHA, STOP and report provision-blocked:<reason> (do NOT buy an SMS number, do NOT switch to a proxy). (e) fill every field with TRUSTED typing (cdp.py insert), DOB via clickxy with scrollIntoView. Then: setup_profile.py --tid <TID> --icon <a $0 PIL monogram png> --bio \\\"one-line AI / money / wealth bio, NO link\\\" --username <handle> (DAY-0: NO commercial link in bio — a day-0 link = suspension). Then establish a DURABLE golden session — THE make-or-break step. A prior provision saved an EPHEMERAL browser-sessionid that died the instant the incognito context closed, which bricked the account (tier1 dead + tier2 forbidden + a saved-but-dead file blocks the fresh-account password exemption). Do NOT repeat that. Instead do a real instagrapi PASSWORD login-once (this is the legitimate FIRST login for a brand-new account, NOT a relogin, so it is safe and browser-independent): using the instagrapi venv python ~/.cache/instagrapi-venv/bin/python, run Client().login(<username>, <the pw you set at signup — read it from ~/.cloak/ig-<handle>.json>), then IMMEDIATELY call get_timeline_feed() and confirm it returns real data — this VERIFIES the session is actually ALIVE, not merely that a file was written — then dump_settings to ~/.cloak/instagrapi-<handle>.json. NEVER use login_by_sessionid (the browser sessionid) — it dies when the context closes. If login or get_timeline_feed() raises ChallengeRequired/bloks or otherwise fails, the account is NOT usable: report provision-blocked:<reason> and register it with status \\\"provision_failed\\\" (NOT ready). ONLY when get_timeline_feed() has CONFIRMED a live session, append ONE entry to ~/.cloak/clip-accounts.json: {\\\"handle\\\":\\\"<handle>\\\",\\\"profile\\\":\\\"clip-en<n>\\\",\\\"port\\\":<a FREE port that is NEITHER 9222 NOR 9223 — check with 'lsof -i -P' first>,\\\"lang\\\":\\\"en\\\",\\\"status\\\":\\\"ready\\\",\\\"session_owner\\\":\\\"instagrapi\\\",\\\"created\\\":\\\"<today YYYY-MM-DD>\\\"}. CRITICAL: write status \\\"ready\\\" ONLY IF get_timeline_feed() verified the session alive (otherwise \\\"provision_failed\\\"); the port field MUST be present and MUST NOT be 9222 or 9223 (run.sh silently defaults a missing port to 9222 = Dais's personal daily-driver — a wrong-account post hazard). Read the file back and verify it parses. Report: handle + port + feed_verified_alive(yes/no) + status_written, or provision-blocked:<reason>."
fi

# ── PRODUCE (deterministic: producer.sh makes a captioned 1080x1920 clip into the queue) ──
log "PRODUCE: producer.sh"
bash "$C/producer.sh" >/dev/null 2>&1 || log "producer rc=$?"

# ── POST (deterministic: run.sh posts the next queued clip via instagrapi + Telegram; cadence-gated) ──
log "POST: run.sh EARN_MODE=execute"
EARN_MODE=execute bash "$C/run.sh" >/dev/null 2>&1 || log "run.sh rc=$?"

# ── BIO (deterministic: IG only makes the profile "website" field clickable — the sole money
# entry point for this loop. Points aiclipsvault's external_url at offer.json's affiliate_link
# (?sid1=aiclipsvault for per-account attribution). TIER-1 ONLY: never triggers a login, silently
# no-ops when the saved instagrapi session is missing/invalid — self-heals once run.sh's POST
# step (login_resilient) refreshes that session, no code change needed. See bio_step.py.) ──
INSTA_PY="$HOME/.cache/instagrapi-venv/bin/python"
if [ -x "$INSTA_PY" ]; then
  log "BIO: bio_step.py aiclipsvault"
  "$INSTA_PY" "$C/scripts/bio_step.py" --handle aiclipsvault 2>>"$HOME/.openclaw/logs/clip-steps.err.log" | while IFS= read -r line; do log "  $line"; done
else
  log "BIO: skip — instagrapi venv not present at $INSTA_PY"
fi

# ── MEASURE (Evaluator: read real view counts of recent reels) ──
step "MEASURE" "STEP MEASURE: resolve @aiclipsvault's CloakBrowser CDP port from $HOME/.cloak/clip-accounts.json, open instagram.com/aiclipsvault/ in it, and read the view + like counts of the 3 most recent reels. Append ONE compact json line per reel to $STATE/clip-metrics.jsonl: {ts:<integer epoch>, reel_url, views:<int>, likes:<int>}. Ground ONLY on the real numbers shown on the page; if logged out, restore the session first; never guess."

# ── REFLECT (Self-Reflection: verbal reinforcement for the next pass) ──
step "REFLECT" "STEP REFLECT (Reflexion + PHASE gate, bible = 47-cold-start-self-improvement-bible.md): read tail -10 $STATE/clip-metrics.jsonl and the last line of $STATE/reflection.jsonl. Decide the PHASE: 'imitate' while own posts are still noise (no self-outlier yet) — keep copying winners, don't over-trust your own tiny numbers; flip to 'optimize' ONLY once one of YOUR OWN reels hits ~3x your own average views (a self-outlier), then that reel becomes the new imitation source. Append ONE compact json line to $STATE/reflection.jsonl: {ts:<int epoch>, phase:<imitate|optimize>, tried:<what changed this pass, lever-named e.g. hook/pattern-interrupt/thumbnail>, metrics_moved:<views delta vs prior, or flat>, self_outlier:<true if a own-post hit 3x own avg, else false>, next:<the single most promising lever next pass — in imitate phase this is 'copy a fresh winner outlier's HOOK', prioritise the hook>}. Be concrete and honest; if flat, pick a DIFFERENT lever than last time (hook first)."

log "pass complete"
