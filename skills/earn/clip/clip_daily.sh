#!/usr/bin/env bash
# clip_daily.sh — CLEAN HONEST daily clip poster (v44). No LLM LEARN/MEASURE/REFLECT (fabrication source removed).
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
log(){ echo "$(date '+%F %T') clip_daily: $*" >&2; }

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
  local timeout_seconds="${3:-900}"
  log "STEP $1 start"
  # stdout is captured per-step (claude CLI prints errors to STDOUT, not stderr — observed
  # 2026-07-16: rc=1 with an empty stderr log) and its tail is surfaced on failure.
  local out="$HOME/.openclaw/logs/clip-step-last.out"
  CLAUDE_CODE_SKIP_PROMPT_HISTORY=1 CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 env -u ANTHROPIC_API_KEY timeout "$timeout_seconds" "$CLAUDE" --model "$STEP_MODEL" --dangerously-skip-permissions --no-session-persistence --add-dir "$HOME" \
    -p "You are the Anicca clip earn-core (IG @aiclipsvault, niche = AI / money / wealth). set -a; . ~/.openclaw/.env 2>/dev/null; set +a. Do EXACTLY this ONE step, fully, then stop. $2" >"$out" 2>>"$HOME/.openclaw/logs/clip-steps.err.log"
  local rc=$?
  [ "$rc" -ne 0 ] && log "STEP $1 FAIL stdout-tail: $(tail -c 800 "$out" 2>/dev/null | tr '\n' ' ')"
  log "STEP $1 done (rc=$rc)"
}

# ── deterministic prelude: single-instance lock (mkdir = atomic on macOS) + disk guard ──
LOCKD=/tmp/anicca-clip-daily.lock.d
CLIP_LEASE="clip-$$"; export CLIP_LEASE
[ -d "$LOCKD" ] && [ $(( $(date +%s) - $(stat -f %m "$LOCKD" 2>/dev/null||echo 0) )) -gt 1800 ] && rmdir "$LOCKD" 2>/dev/null
mkdir "$LOCKD" 2>/dev/null || { log "another clip pass holds the lock — exit"; exit 0; }
trap 'rmdir "$LOCKD" 2>/dev/null; python3 "$C/../../browser/scripts/cdp_context_lease.py" release "$CLIP_LEASE" >/dev/null 2>&1' EXIT
FREE=$(df -g / | tail -1 | awk '{print $4}')
[ "${FREE:-99}" -lt 5 ] && { log "disk <5GB free — abort to protect the session"; exit 0; }
python3 "$C/../../browser/scripts/cdp_context_lease.py" acquire "$CLIP_LEASE" --no-seed >/dev/null 2>&1 || true

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
  step "PROVISION" "STEP PROVISION (1-loop-1-acc, replace-on-cold, ZERO human): clip-accounts.json (~/.cloak/clip-accounts.json) has NO usable account (none with status ready/warming that is not poisoned/frozen/blocked), so CREATE one brand-new IG account NOW and register it as the sole active clip account. BROWSER ISOLATION OVERRIDE: the account-creation signup MUST run INSIDE this pass's already-acquired isolated browser context named '$CLIP_LEASE', NOT the raw shared :9222 default context. Acquire/inspect that exact lease via ~/anicca/skills/browser/scripts/cdp_context_lease.py; the lease already created an isolated context on :9222 with its own cookie jar and tab. Get the lease's target_id/ws and drive THAT tab via cdp.py. NEVER navigate or close any tab you did not create, so gig/capafy tabs remain untouched. This overrides any later cdp_incognito.py/raw :9222 wording in this prompt. Follow the ig-account-create skill at ~/.claude/skills/ig-account-create/SKILL.md EXACTLY as proven for @aiclipsvault and @useclaudeskills. HARD RULES: (a) drive the RUNNING CloakBrowser daily-driver on CDP :9222 via cdp_incognito.py — an isolated context in a NEW tab; NEVER touch or close any existing tab. (b) residential home IP, NO proxy (a fresh/cold proxy IP triggers a phone wall — do not use one). (c) email = a fresh Gmail plus-address keiodaisuke+aiclips<random-tag>@gmail.com; read the 6-digit OTP via 'gog gmail search --account keiodaisuke@gmail.com \\\"instagram in:anywhere newer_than:1h\\\" --max 3 --plain' (OTP often lands in SPAM, so in:anywhere is required). (d) IG email-signup on this home IP needs NO phone and NO captcha — do NOT do the phone flow; if IG unexpectedly forces a phone number or a text-CAPTCHA, STOP and report provision-blocked:<reason> (do NOT buy an SMS number, do NOT switch to a proxy). (e) fill every field with TRUSTED typing (cdp.py insert), DOB via clickxy with scrollIntoView. Then: setup_profile.py --tid <TID> --icon <a $0 PIL monogram png> --bio \\\"one-line AI / money / wealth bio, NO link\\\" --username <handle> (DAY-0: NO commercial link in bio — a day-0 link = suspension). Then establish a DURABLE golden session — THE make-or-break step. A prior provision saved an EPHEMERAL browser-sessionid that died the instant the incognito context closed, which bricked the account (tier1 dead + tier2 forbidden + a saved-but-dead file blocks the fresh-account password exemption). Do NOT repeat that. Instead do a real instagrapi PASSWORD login-once (this is the legitimate FIRST login for a brand-new account, NOT a relogin, so it is safe and browser-independent): using the instagrapi venv python ~/.cache/instagrapi-venv/bin/python, run Client().login(<username>, <the pw you set at signup — read it from ~/.cloak/ig-<handle>.json>), then IMMEDIATELY call get_timeline_feed() and confirm it returns real data — this VERIFIES the session is actually ALIVE, not merely that a file was written — then dump_settings to ~/.cloak/instagrapi-<handle>.json. NEVER use login_by_sessionid (the browser sessionid) — it dies when the context closes. If login or get_timeline_feed() raises ChallengeRequired/bloks or otherwise fails, the account is NOT usable: report provision-blocked:<reason> and register it with status \\\"provision_failed\\\" (NOT ready). ONLY when get_timeline_feed() has CONFIRMED a live session, append ONE entry to ~/.cloak/clip-accounts.json: {\\\"handle\\\":\\\"<handle>\\\",\\\"profile\\\":\\\"clip-en<n>\\\",\\\"port\\\":<a FREE port that is NEITHER 9222 NOR 9223 — check with 'lsof -i -P' first>,\\\"lang\\\":\\\"en\\\",\\\"status\\\":\\\"ready\\\",\\\"session_owner\\\":\\\"instagrapi\\\",\\\"created\\\":\\\"<today YYYY-MM-DD>\\\"}. CRITICAL: write status \\\"ready\\\" ONLY IF get_timeline_feed() verified the session alive (otherwise \\\"provision_failed\\\"); the port field MUST be present and MUST NOT be 9222 or 9223 (run.sh silently defaults a missing port to 9222 = Dais's personal daily-driver — a wrong-account post hazard). Read the file back and verify it parses. Report: handle + port + feed_verified_alive(yes/no) + status_written, or provision-blocked:<reason>." 1500
fi

# ── PRODUCE (deterministic: producer.sh makes a captioned 1080x1920 clip into the queue) ──
log "PRODUCE: producer.sh"
bash "$C/producer.sh" >/dev/null 2>&1 || log "producer rc=$?"

# ── POST (HONEST daily job: run.sh resolves the status==ready account DYNAMICALLY, posts via
# instagrapi_post.py whose logged-out REALITY GATE confirms the reel is publicly visible before
# claiming success, and telegrams ONLY a verified-published REAL url. NO LLM LEARN/MEASURE/REFLECT
# here = no fabricated metrics or hallucinated reel URLs can ever be reported. This is the whole job.) ──
log "POST: run.sh EARN_MODE=execute"
EARN_MODE=execute bash "$C/run.sh" >/dev/null 2>&1 || log "run.sh rc=$?"

log "clip_daily pass complete"
