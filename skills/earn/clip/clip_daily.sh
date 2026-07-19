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
MARKETING_ENGINE_DIR="$C/../marketing-engine"
# shellcheck source=../marketing-engine/provision_prompt.sh
. "$MARKETING_ENGINE_DIR/provision_prompt.sh"
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
# usable account is already present. A new account is appended as day1 warming/browser and posts
# nothing this pass. ──
# ── WARM (deterministic: age each status=warming account via warmer.py; day1-2 stay browser-only,
# then day3 establishes the one golden instagrapi session before promotion to ready.) ──
log "WARM: warmer.py"
"$PY" "$MARKETING_ENGINE_DIR/warmer.py" "$CLIP_ACCTS" 2>&1 | while IFS= read -r line; do log "  $line"; done

USABLE_ACCTS=$("$PY" - "$CLIP_ACCTS" <<'PYJSON' 2>/dev/null
import json,sys
try: a=json.load(open(sys.argv[1]))
except Exception: a=[]
def ok(x):
    s=(x.get("status") or "").lower()
    if any(k in s for k in ("poison","frozen","blocked","fail")): return False
    return s.startswith("ready") or s.startswith("warming")
print(sum(1 for x in a if ok(x)))
PYJSON
)
log "PROVISION: usable_accounts=${USABLE_ACCTS:-0}"
if [ "${USABLE_ACCTS:-0}" -eq 0 ]; then
  PROVISION_PROMPT="$(
    IG_PROVISION_ACCOUNT_STATE_FILE="$CLIP_ACCTS" \
    IG_PROVISION_HANDLE_PREFIX="aiclips" \
    IG_PROVISION_INSTANCE="clip" \
    IG_PROVISION_GMAIL_PLUS_TAG_PREFIX="aiclips" \
    IG_PROVISION_BIO_TEXT="one-line AI / money / wealth bio, NO link" \
    IG_PROVISION_BROWSER_INSTRUCTIONS="Run signup inside this pass's already-acquired isolated browser context named '$CLIP_LEASE', not the raw shared :9222 default context. Acquire and inspect that exact lease via ~/anicca/skills/browser/scripts/cdp_context_lease.py; use its target_id/ws and drive only that tab via cdp.py. Never navigate or close a tab this pass did not create, so gig/capafy tabs remain untouched." \
    IG_PROVISION_PROFILE_PREFIX="clip-en" \
    render_ig_provision_prompt
  )"
  step "PROVISION" "$PROVISION_PROMPT" 1500
fi

# ── PRODUCE (deterministic: producer.sh makes a captioned 1080x1920 clip into the queue) ──
log "PRODUCE: producer.sh"
bash "$C/producer.sh" >/dev/null 2>&1 || log "producer rc=$?"

# ── POST (HONEST daily job: run.sh resolves the status==ready account DYNAMICALLY, posts via
# poster.py whose logged-out REALITY GATE confirms the reel is publicly visible before
# claiming success, and telegrams ONLY a verified-published REAL url. NO LLM LEARN/MEASURE/REFLECT
# here = no fabricated metrics or hallucinated reel URLs can ever be reported. This is the whole job.) ──
log "POST: run.sh EARN_MODE=execute"
EARN_MODE=execute bash "$C/run.sh" >/dev/null 2>&1 || log "run.sh rc=$?"

log "clip_daily pass complete"
