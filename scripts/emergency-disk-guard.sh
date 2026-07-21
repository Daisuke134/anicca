#!/bin/bash
# emergency-disk-guard.sh — deterministic low-disk containment, run every minute.
# Canonical source. Deploy byte-for-byte to /Users/anicca/scripts/emergency-disk-guard.sh.
set -u
export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin:/usr/sbin:/sbin

POLICY_VERSION="p0-containment-v1"
HOME_DIR="${EMERGENCY_GUARD_TEST_HOME:-$HOME}"
STATE_DIR="$HOME_DIR/.openclaw/state"
LOG_DIR="$HOME_DIR/.openclaw/logs"
LOG="$LOG_DIR/emergency-disk-guard.log"
DECISION_LEDGER="$STATE_DIR/emergency-disk-guard-decisions.tsv"
RECLAIM_LEDGER="$STATE_DIR/emergency-disk-guard-reclaim.tsv"
BACKPRESSURE="$STATE_DIR/disk-pressure.block"
LOCK="$STATE_DIR/.emergency-disk-guard.lock"
GIG_LOCK_PID="${EMERGENCY_GUARD_TEST_LOCK_OWNER:-}"
GIG_WORKER_MAX_SECONDS="${GIG_WORKER_MAX_SECONDS:-7200}"
GIG_HEARTBEAT_MAX_SECONDS="${GIG_HEARTBEAT_MAX_SECONDS:-180}"
THRESHOLD_GB="${EMERGENCY_GUARD_THRESHOLD_GB:-6}"
ULTRA_GB="${EMERGENCY_GUARD_ULTRA_GB:-3}"
TEST_MODE=0
[ -n "${EMERGENCY_GUARD_TEST_PROCESS_FIXTURE:-}" ] && TEST_MODE=1
DRY_RUN="${EMERGENCY_GUARD_DRY_RUN:-0}"

mkdir -p "$LOG_DIR" "$STATE_DIR" 2>/dev/null || exit 1
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

if ! mkdir "$LOCK" 2>/dev/null; then
  OLD=$(cat "$LOCK/pid" 2>/dev/null || echo "")
  [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null && exit 0
  rm -rf "$LOCK"
  mkdir "$LOCK" 2>/dev/null || exit 0
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT

free_gb() {
  if [ -n "${EMERGENCY_GUARD_TEST_FREE_GB:-}" ]; then
    printf '%s\n' "$EMERGENCY_GUARD_TEST_FREE_GB"
  else
    df -g / | awk 'NR==2{print $4}'
  fi
}

now_epoch() { printf '%s\n' "${EMERGENCY_GUARD_TEST_NOW_EPOCH:-$(date +%s)}"; }

append_decision() {
  local pid="$1" decision="$2" reason="$3"
  if [ "$TEST_MODE" -eq 1 ]; then
    printf '%s\t%s\t%s\n' "$pid" "$decision" "$reason" >> "$DECISION_LEDGER"
  else
    printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u '+%FT%TZ')" "$pid" "$decision" "$reason" "$POLICY_VERSION" >> "$DECISION_LEDGER"
  fi
}

path_bytes() {
  [ -e "$1" ] || { printf '0\n'; return; }
  du -sk "$1" 2>/dev/null | awk '{print $1 * 1024}'
}

reclaim_path() {
  local path="$1" owner="$2" class="$3" reason="$4" before result after reclaimed
  [ -e "$path" ] || return 0
  before=$(path_bytes "$path")
  if [ "$DRY_RUN" = 1 ]; then
    printf 'candidate\t%s\t%s\t%s\t%s\t%s\t%s\n' "$path" "$owner" "$class" "$before" "$reason" "$POLICY_VERSION"
    return 0
  fi
  result=removed
  rm -rf "$path" 2>/dev/null || result=failed
  after=$(path_bytes "$path")
  reclaimed=$((before - after))
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(date -u '+%FT%TZ')" "$path" "$owner" "$class" "$reclaimed" "$reason" "$POLICY_VERSION" "$result" >> "$RECLAIM_LEDGER"
}

etime_seconds() {
  local value="$1" days=0 hours=0 minutes=0 seconds=0 rest
  value=${value//[[:space:]]/}
  [ -n "$value" ] || return 1
  case "$value" in
    *-*) days=${value%%-*}; rest=${value#*-} ;;
    *) rest=$value ;;
  esac
  case "$rest" in
    *:*:*) hours=${rest%%:*}; rest=${rest#*:}; minutes=${rest%%:*}; seconds=${rest#*:} ;;
    *:*) minutes=${rest%%:*}; seconds=${rest#*:} ;;
    *) return 1 ;;
  esac
  case "$days:$hours:$minutes:$seconds" in *[!0-9:]* ) return 1 ;; esac
  printf '%s\n' "$((10#$days * 86400 + 10#$hours * 3600 + 10#$minutes * 60 + 10#$seconds))"
}

heartbeat_age() {
  local pid="$1" heartbeat mtime
  heartbeat="$STATE_DIR/gig-workers/$pid.heartbeat"
  if [ "$TEST_MODE" -eq 1 ] && [ "${EMERGENCY_GUARD_TEST_HEARTBEAT_PID:-}" = "$pid" ]; then
    printf '0\n'
    return 0
  fi
  [ -f "$heartbeat" ] || return 1
  mtime=$(stat -f %m "$heartbeat" 2>/dev/null) || return 1
  printf '%s\n' "$(($(now_epoch) - mtime))"
}

classify_worker() {
  local pid="$1" elapsed="$2" cmdline="$3" hb_age
  case "$cmdline" in
    *"--name anicca-gig-core"*) printf 'preserve\tgig-core\n'; return ;;
  esac
  if hb_age=$(heartbeat_age "$pid") && [ "$hb_age" -le "$GIG_HEARTBEAT_MAX_SECONDS" ]; then
    printf 'preserve\tfresh-heartbeat\n'; return
  fi
  if [ -z "$elapsed" ]; then
    printf 'preserve\tunknown-age-fail-closed\n'; return
  fi
  if [ "$pid" = "$GIG_LOCK_PID" ] && [ "$elapsed" -le "$GIG_WORKER_MAX_SECONDS" ]; then
    printf 'preserve\tlock-owner\n'; return
  fi
  if [ "$elapsed" -le "$GIG_WORKER_MAX_SECONDS" ]; then
    printf 'preserve\twithin-timeout\n'; return
  fi
  printf 'kill\tstale-runaway\n'
}

stop_runaway() {
  local pid="$1" reason="$2"
  [ "$DRY_RUN" = 1 ] && return
  if [ "$TEST_MODE" -eq 1 ]; then
    printf '%s\t%s\n' "$pid" "$reason" >> "$EMERGENCY_GUARD_TEST_KILL_LEDGER"
    return
  fi
  kill -TERM "$pid" 2>/dev/null || return
  local i=0
  while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 5 ]; do sleep 1; i=$((i + 1)); done
  kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true
}

evaluate_worker() {
  local pid="$1" elapsed="$2" cmdline="$3" verdict decision reason
  verdict=$(classify_worker "$pid" "$elapsed" "$cmdline")
  decision=${verdict%%$'\t'*}
  reason=${verdict#*$'\t'}
  append_decision "$pid" "$decision" "$reason"
  [ "$decision" = kill ] && stop_runaway "$pid" "$reason"
}

evaluate_gig_workers() {
  local pid elapsed cmdline pattern etime seen=" "
  if [ "$TEST_MODE" -eq 1 ]; then
    while IFS=$'\t' read -r pid elapsed cmdline; do
      [ -n "$pid" ] || continue
      evaluate_worker "$pid" "$elapsed" "$cmdline"
    done < "$EMERGENCY_GUARD_TEST_PROCESS_FIXTURE"
    return
  fi
  [ -n "$GIG_LOCK_PID" ] || GIG_LOCK_PID=$(cat /tmp/anicca-gig-pass.lock.d/pid 2>/dev/null || true)
  for pattern in "gig_pass.sh" "Coconala gig"; do
    while IFS= read -r pid; do
      case "$seen" in *" $pid "*) continue ;; esac
      seen="$seen$pid "
      cmdline=$(ps -p "$pid" -o command= 2>/dev/null) || continue
      [ -n "$cmdline" ] || continue
      case "$cmdline" in *"$pattern"*) ;; *) continue ;; esac
      etime=$(ps -p "$pid" -o etime= 2>/dev/null || true)
      elapsed=$(etime_seconds "$etime" 2>/dev/null || true)
      evaluate_worker "$pid" "$elapsed" "$cmdline"
    done < <(pgrep -f "$pattern" 2>/dev/null || true)
  done
}

FREE=$(free_gb)
[ -n "$FREE" ] || exit 1
if [ "$FREE" -ge "$THRESHOLD_GB" ]; then
  rm -f "$BACKPRESSURE"
  exit 0
fi

printf 'free_gb=%s threshold_gb=%s policy=%s observed_at=%s\n' \
  "$FREE" "$THRESHOLD_GB" "$POLICY_VERSION" "$(date -u '+%FT%TZ')" > "$BACKPRESSURE"
log "LOW DISK: ${FREE}GB free (< ${THRESHOLD_GB}GB) — safe containment start"

if [ "$TEST_MODE" -eq 0 ] || [ "${EMERGENCY_GUARD_TEST_ENABLE_RECLAIM:-0}" = 1 ]; then
  # Exact, known-regenerable caches only. No transcript, todo, lock, worktree,
  # deliverable, browser identity, cookies, Login Data, or session database.
  for bundle in "$HOME_DIR/Library/Application Support/Claude/vm_bundles/"*.bundle; do
    [ -e "$bundle" ] && reclaim_path "$bundle" claude-vm ephemeral-cache regenerated-by-claude
  done
  reclaim_path "$HOME_DIR/.cache/whisper" whisper ephemeral-cache model-redownload
  reclaim_path "$HOME_DIR/.cache/torch" torch ephemeral-cache model-redownload
  reclaim_path "$HOME_DIR/.cache/uv" uv ephemeral-cache package-redownload
  reclaim_path "$HOME_DIR/Library/Caches/pip" pip ephemeral-cache package-redownload
  if ! pgrep -f '/Library/Caches/ms-playwright/' >/dev/null 2>&1; then
    reclaim_path "$HOME_DIR/Library/Caches/ms-playwright" playwright ephemeral-cache browser-redownload
  fi
  if ! pgrep -f '[/](cargo|rustc)([[:space:]]|$)' >/dev/null 2>&1; then
    reclaim_path "$HOME_DIR/.cargo/registry" cargo ephemeral-cache crate-redownload
  fi
  for profile in "$HOME_DIR"/.cloak/profiles/*; do
    [ -d "$profile" ] || continue
    if [ "$TEST_MODE" -eq 0 ] && pgrep -f -- "--user-data-dir=$profile([[:space:]]|$)" >/dev/null 2>&1; then
      printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u '+%FT%TZ')" "$profile" preserve active-browser-profile "$POLICY_VERSION" >> "$DECISION_LEDGER"
      continue
    fi
    for cache in \
      "$profile/Default/Cache" "$profile/Default/Code Cache" "$profile/Default/GPUCache" \
      "$profile/ShaderCache" "$profile/GrShaderCache" "$profile/GraphiteDawnCache"; do
      reclaim_path "$cache" cloakbrowser ephemeral-cache browser-cache-regenerated
    done
  done
  if [ -d "$HOME_DIR/.openclaw/workspace/runs" ]; then
    while IFS= read -r intermediate; do
      reclaim_path "$intermediate" reelclaw intermediate-output final-mp4-preserved
    done < <(find "$HOME_DIR/.openclaw/workspace/runs" -mindepth 2 -maxdepth 2 -type f -name reel-text.mp4 -mtime +1 -print 2>/dev/null)
  fi
  if ! pgrep -f 'hammer-and-nail|tent_backend|[/](cargo|rustc)([[:space:]]|$)' >/dev/null 2>&1; then
    reclaim_path "$HOME_DIR/.openclaw/workspace/hammer-and-nail/backend/target" hammer-and-nail build-output cargo-build-regenerated
  fi
  if ! pgrep -f "$HOME_DIR/.openclaw/skills/anicca-earn-bounty/work/" >/dev/null 2>&1; then
    for modules in "$HOME_DIR"/.openclaw/skills/anicca-earn-bounty/work/*/*/node_modules; do
      [ -d "$modules" ] || continue
      project=${modules%/node_modules}
      if [ -f "$project/package-lock.json" ] || [ -f "$project/pnpm-lock.yaml" ] || [ -f "$project/yarn.lock" ]; then
        reclaim_path "$modules" anicca-earn-bounty dependency-output lockfile-reinstall
      fi
    done
  fi
fi

if [ "$FREE" -lt "$ULTRA_GB" ]; then
  evaluate_gig_workers
  log "ULTRA: applied backpressure; preserved core/healthy workers; stopped only stale runaway workers"
fi

NEW=$(free_gb)
log "safe containment done: ${FREE}GB -> ${NEW}GB free"
