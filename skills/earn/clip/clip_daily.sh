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
LEASE_SCRIPT="$C/../../browser/scripts/cdp_context_lease.py"
CLIP_LEASE_WS=""
CLIP_LEASE_TOKEN=""
CLIP_LEASE_GENERATION=""
LEASE_HEARTBEAT_PID=""
LEASE_HEARTBEAT_SECONDS="${LEASE_HEARTBEAT_SECONDS:-300}"
MAIN_PARENT_PID="$$"
MAIN_PARENT_PGID="$(ps -o pgid= -p "$MAIN_PARENT_PID" | tr -d '[:space:]')"
ACTIVE_STEP_PID=""
ACTIVE_STEP_PGID=""
LEASE_SIGNAL_HANDLING=0

active_step_group_is_safe(){
  local pgid="${1:-}"
  case "$pgid" in
    ''|0|*[!0-9]*) return 1 ;;
  esac
  [ -n "${MAIN_PARENT_PGID:-}" ] && [ "$pgid" != "$MAIN_PARENT_PGID" ]
}

active_step_group_alive(){
  local pgid="${1:-}"
  active_step_group_is_safe "$pgid" && kill -0 -- "-$pgid" 2>/dev/null
}

clear_active_step(){
  ACTIVE_STEP_PID=""
  ACTIVE_STEP_PGID=""
}

start_active_step(){ # every agent step gets a private session/process group on macOS
  if [ -n "${ACTIVE_STEP_PGID:-}" ]; then
    if ! active_step_group_is_safe "$ACTIVE_STEP_PGID"; then
      log "refusing to replace an unsafe active step process group"
      return 1
    fi
    if active_step_group_alive "$ACTIVE_STEP_PGID"; then
      log "refusing to replace a still-live active step process group"
      return 1
    fi
    clear_active_step
  fi
  python3 -c 'import os
import sys
os.setsid()
os.execvp(sys.argv[1], sys.argv[1:])' "$@" &
  ACTIVE_STEP_PID=$!
  ACTIVE_STEP_PGID=$ACTIVE_STEP_PID
}

wait_for_active_step(){
  local pid="${ACTIVE_STEP_PID:-}"
  local rc=0
  [ -n "$pid" ] || return 0
  wait "$pid" || rc=$?
  ACTIVE_STEP_PID=""
  if ! active_step_group_is_safe "$ACTIVE_STEP_PGID"; then
    log "active step process group is unsafe; retaining fenced lease"
    [ "$rc" -eq 0 ] && rc=1
    return "$rc"
  elif active_step_group_alive "$ACTIVE_STEP_PGID"; then
    terminate_active_step || {
      [ "$rc" -eq 0 ] && rc=1
      return "$rc"
    }
  else
    clear_active_step
  fi
  return "$rc"
}

run_active_step_with_stdin(){
  local input="$1"
  shift
  start_active_step bash -c '
input=$1
shift
printf "%s\\n" "$input" | "$@"
' bash "$input" "$@"
  [ -n "${ACTIVE_STEP_PID:-}" ] || return 1
  wait_for_active_step
}

terminate_active_step(){
  local pid="${ACTIVE_STEP_PID:-}"
  local pgid="${ACTIVE_STEP_PGID:-}"
  local attempts=20
  [ -n "$pgid" ] || { clear_active_step; return 0; }
  if ! active_step_group_is_safe "$pgid"; then
    log "refusing to signal an unsafe active step process group"
    return 1
  fi
  kill -TERM -- "-$pgid" 2>/dev/null || true
  while [ "$attempts" -gt 0 ] && active_step_group_alive "$pgid"; do
    command sleep 0.05
    attempts=$((attempts - 1))
  done
  if active_step_group_alive "$pgid"; then
    kill -KILL -- "-$pgid" 2>/dev/null || true
  fi
  attempts=20
  while [ "$attempts" -gt 0 ] && active_step_group_alive "$pgid"; do
    command sleep 0.05
    attempts=$((attempts - 1))
  done
  [ -z "$pid" ] || wait "$pid" 2>/dev/null || true
  if active_step_group_alive "$pgid"; then
    log "active step process group survived termination; retaining fenced lease"
    return 1
  fi
  clear_active_step
}

handle_lease_signal(){
  local received_signal="$1"
  [ "${LEASE_SIGNAL_HANDLING:-0}" = "1" ] && return
  LEASE_SIGNAL_HANDLING=1
  log "received $received_signal; terminating active step before fenced lease release"
  terminate_active_step
  [ "$received_signal" = "INT" ] && exit 130
  exit 143
}

install_lease_signal_handlers(){
  trap 'handle_lease_signal TERM' TERM
  trap 'handle_lease_signal INT' INT
}

parse_lease(){ # $1=acquire JSON; reject partial or malformed lease identities
  local parse_status ws_valid
  {
    IFS= read -r parse_status
    IFS= read -r CLIP_LEASE_TOKEN
    IFS= read -r CLIP_LEASE_GENERATION
    IFS= read -r ws_valid
    IFS= read -r CLIP_LEASE_WS || true
  } < <(printf '%s' "$1" | python3 -c '
import json
import sys

try:
    lease = json.load(sys.stdin)
    token = lease.get("token")
    generation = lease.get("generation")
    if (
        not lease.get("ok")
        or not isinstance(token, str)
        or not token
        or any(char.isspace() or char == "\x1f" for char in token)
        or isinstance(generation, bool)
        or not isinstance(generation, int)
        or generation < 1
    ):
        raise ValueError("invalid fenced lease acquire response")
except (ValueError, TypeError, json.JSONDecodeError):
    print("0")
    raise SystemExit(0)

ws = lease.get("ws")
ws_valid = isinstance(ws, str) and bool(ws) and not any(char.isspace() for char in ws)
print("1")
print(token)
print(generation)
print(int(ws_valid))
if ws_valid:
    print(ws)
')
  [ "$parse_status" = "1" ] && [ -n "$CLIP_LEASE_TOKEN" ] && [ -n "$CLIP_LEASE_GENERATION" ] && [ "$ws_valid" = "1" ] && [ -n "$CLIP_LEASE_WS" ]
}

heartbeat_lease(){
  python3 "$LEASE_SCRIPT" heartbeat "$CLIP_LEASE" --token "$CLIP_LEASE_TOKEN" --generation "$CLIP_LEASE_GENERATION" >/dev/null 2>&1
}

release_lease(){
  [ -n "${CLIP_LEASE_TOKEN:-}" ] && [ -n "${CLIP_LEASE_GENERATION:-}" ] || return 0
  python3 "$LEASE_SCRIPT" release "$CLIP_LEASE" --token "$CLIP_LEASE_TOKEN" --generation "$CLIP_LEASE_GENERATION" >/dev/null 2>&1
}

lease_heartbeat_loop(){
  while command sleep "$LEASE_HEARTBEAT_SECONDS"; do
    heartbeat_lease || {
      log "lease heartbeat failed; terminating pass before stale browser work"
      kill -TERM "$MAIN_PARENT_PID" 2>/dev/null || true
      return 1
    }
  done
}

start_lease_heartbeat(){
  ( lease_heartbeat_loop ) &
  LEASE_HEARTBEAT_PID=$!
}

stop_lease_heartbeat(){
  [ -n "${LEASE_HEARTBEAT_PID:-}" ] || return 0
  kill "$LEASE_HEARTBEAT_PID" 2>/dev/null || true
  wait "$LEASE_HEARTBEAT_PID" 2>/dev/null || true
  LEASE_HEARTBEAT_PID=""
}

cleanup(){
  local rc=$?
  trap - TERM INT
  stop_lease_heartbeat
  if terminate_active_step; then
    release_lease || log "fenced lease release failed; gc will retry the durable pending row"
  else
    log "active step process group remains; retaining fenced lease for recovery"
    [ "$rc" -eq 0 ] && rc=1
  fi
  rmdir "$LOCKD" 2>/dev/null || true
  trap - EXIT
  exit "$rc"
}

step(){ # $1=label  $2=prompt
  heartbeat_lease || { log "lease heartbeat failed before STEP $1"; exit 1; }
  log "STEP $1 start"
  local out="$HOME/.openclaw/logs/clip-step-last.out"
  local evidence="$HOME/.openclaw/state/agent-runner-evidence/clip-daily/$(date +%s)-$$-$1"
  run_active_step_with_stdin "You are the Anicca clip earn-core (IG @aiclipsvault, niche = AI / money / wealth). set -a; . ~/.openclaw/.env 2>/dev/null; set +a. The launcher already acquired fenced CDP context '$CLIP_LEASE' at ws '$CLIP_LEASE_WS'; it retains the exact token/generation and alone owns heartbeats and release. Drive ONLY that ws, never invoke cdp_context_lease.py acquire/release, and never read the lease ledger. Do EXACTLY this ONE step, fully, then stop. $2" \
    "$RUN_AGENT" --task-class tool-agent --evidence-dir "$evidence" --task-label "clip-daily-$1" --loop clip \
    >"$out" 2>>"$HOME/.openclaw/logs/clip-steps.err.log"
  local rc=$?
  heartbeat_lease || { log "lease heartbeat failed after STEP $1"; exit 1; }
  [ "$rc" -ne 0 ] && log "STEP $1 FAIL stdout-tail: $(tail -c 800 "$out" 2>/dev/null | tr '\n' ' ')"
  log "STEP $1 done (rc=$rc)"
}

# ── deterministic prelude: single-instance lock (mkdir = atomic on macOS) + disk guard ──
LOCKD=/tmp/anicca-clip-daily.lock.d
CLIP_LEASE="clip-$$"; export CLIP_LEASE
[ -d "$LOCKD" ] && [ $(( $(date +%s) - $(stat -f %m "$LOCKD" 2>/dev/null||echo 0) )) -gt 1800 ] && rmdir "$LOCKD" 2>/dev/null
mkdir "$LOCKD" 2>/dev/null || { log "another clip pass holds the lock — exit"; exit 0; }
trap cleanup EXIT
install_lease_signal_handlers
FREE=$(df -g / | tail -1 | awk '{print $4}')
[ "${FREE:-99}" -lt 5 ] && { log "disk <5GB free — abort to protect the session"; exit 0; }
LEASE_JSON=$(python3 "$LEASE_SCRIPT" acquire "$CLIP_LEASE" --no-seed) || { log "fenced lease acquire failed; aborting pass"; exit 1; }
parse_lease "$LEASE_JSON" || { log "fenced lease response malformed; aborting pass"; exit 1; }
export CLIP_LEASE CLIP_LEASE_WS
heartbeat_lease || { log "fenced lease heartbeat rejected after acquire; aborting pass"; exit 1; }
start_lease_heartbeat

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
