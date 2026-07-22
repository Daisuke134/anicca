#!/usr/bin/env bash
# clip_daily.sh — CLEAN HONEST daily clip poster (v44). No LLM LEARN/MEASURE/REFLECT (fabrication source removed).
# Reflexion: Actor = producer.sh + run.sh, Evaluator = clip-metrics, Self-Reflection = reflection.jsonl).
# Each judgment step is a separate bounded shared-runner call with a short focused prompt
# (never bricks disk). PRODUCE + POST are deterministic (producer.sh makes a 1080x1920 clip; run.sh posts
# via instagrapi + reports to Telegram, respecting the cadence gate). State passes between steps through
# ~/clips/{reflection.jsonl,playbook.json,clip-metrics.jsonl}.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
C="$HOME/anicca/skills/earn/clip"
MARKETING_ENGINE_DIR="$C/../marketing-engine"
# shellcheck source=../marketing-engine/provision_prompt.sh
. "$MARKETING_ENGINE_DIR/provision_prompt.sh"
# shellcheck source=../marketing-engine/account_state.sh
. "$MARKETING_ENGINE_DIR/account_state.sh"
RUN_AGENT="$MARKETING_ENGINE_DIR/run_agent.sh"
STATE="$HOME/clips"
mkdir -p "$STATE"
source "$C/_instance_paths.sh"   # resolves CLIP_ACCTS (respects ANICCA_INSTANCE, same as run.sh)
PY="/opt/homebrew/bin/python3"
log(){ echo "$(date '+%F %T') clip_daily: $*" >&2; }

step(){ # $1=label  $2=prompt
  log "STEP $1 start"
  local out="$HOME/.openclaw/logs/clip-step-last.out"
  local evidence="$HOME/.openclaw/state/agent-runner-evidence/clip-daily/$(date +%s)-$$-$1"
  printf '%s\n' "You are the Anicca clip earn-core (IG @aiclipsvault, niche = AI / money / wealth). set -a; . ~/.openclaw/.env 2>/dev/null; set +a. Do EXACTLY this ONE step, fully, then stop. $2" | \
    "$RUN_AGENT" --task-class tool-agent --evidence-dir "$evidence" --task-label "clip-daily-$1" \
      >"$out" 2>>"$HOME/.openclaw/logs/clip-steps.err.log"
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

USABLE_ACCTS=$(count_ig_usable_accounts "$CLIP_ACCTS")
log "PROVISION: usable_accounts=${USABLE_ACCTS:-0}"
if [ "${USABLE_ACCTS:-0}" -eq 0 ]; then
  PROVISION_PROMPT="$(
    IG_PROVISION_ACCOUNT_STATE_FILE="$CLIP_ACCTS" \
    IG_PROVISION_HANDLE_PREFIX="aiclips" \
    IG_PROVISION_INSTANCE="clip" \
    IG_PROVISION_GMAIL_PLUS_TAG_PREFIX="aiclips" \
    IG_PROVISION_BIO_TEXT="one-line AI / money / wealth bio, NO link" \
    IG_PROVISION_PORT="9331" \
    IG_PROVISION_CONTEXT_ID="$CLIP_LEASE" \
    IG_PROVISION_BROWSER_INSTRUCTIONS="Launch and use the dedicated CloakBrowser profile on :9331 for context '$CLIP_LEASE'. Never use or log in through the raw shared :9222 browser." \
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
