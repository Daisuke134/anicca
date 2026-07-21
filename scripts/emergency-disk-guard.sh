#!/bin/bash
# emergency-disk-guard.sh — deterministic low-disk containment, run every minute.
# Canonical source. Deploy byte-for-byte to /Users/anicca/scripts/emergency-disk-guard.sh.
set -u
export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin:/usr/sbin:/sbin

POLICY_VERSION="p0-containment-v2"
HOME_DIR="${EMERGENCY_GUARD_TEST_HOME:-$HOME}"
STATE_DIR="$HOME_DIR/.openclaw/state"
LEASE_DIR="$STATE_DIR/gig-workers"
LOG_DIR="$HOME_DIR/.openclaw/logs"
LOG="$LOG_DIR/emergency-disk-guard.log"
DECISION_LEDGER="$STATE_DIR/emergency-disk-guard-decisions.tsv"
RECLAIM_LEDGER="$STATE_DIR/emergency-disk-guard-reclaim.tsv"
BACKPRESSURE="$STATE_DIR/disk-pressure.block"
LOCK="$STATE_DIR/.emergency-disk-guard.lock"
GIG_LOCK_PID="${EMERGENCY_GUARD_TEST_LOCK_OWNER:-}"
GIG_WORKER_MAX_SECONDS="${GIG_WORKER_MAX_SECONDS:-7200}"
GIG_HEARTBEAT_MAX_SECONDS="${GIG_HEARTBEAT_MAX_SECONDS:-180}"
CANONICAL_GIG_ARGV="${GIG_WORKER_CANONICAL_ARGV:-/bin/bash $HOME_DIR/profitable-claude/skills/gig-work/gig_pass.sh}"
THRESHOLD_GB="${EMERGENCY_GUARD_THRESHOLD_GB:-6}"
ULTRA_GB="${EMERGENCY_GUARD_ULTRA_GB:-3}"
TEST_MODE=0
[ -n "${EMERGENCY_GUARD_TEST_PROCESS_FIXTURE:-}" ] && TEST_MODE=1
DRY_RUN="${EMERGENCY_GUARD_DRY_RUN:-0}"
RECLAIM_SEQ=0
STOP_DECISION=""
STOP_REASON=""

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
  local subject="$1" decision="$2" reason="$3"
  if [ "$TEST_MODE" -eq 1 ]; then
    printf '%s\t%s\t%s\n' "$subject" "$decision" "$reason" >> "$DECISION_LEDGER"
  else
    printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u '+%FT%TZ')" "$subject" "$decision" "$reason" "$POLICY_VERSION" >> "$DECISION_LEDGER"
  fi
}

path_bytes() {
  [ -e "$1" ] || { printf '0\n'; return 0; }
  du -sk "$1" 2>/dev/null | awk 'NF {print $1 * 1024}'
}

append_reclaim() {
  local txid="$1" phase="$2" path="$3" owner="$4" class="$5"
  local before="$6" after="$7" reclaimed="$8" reason="$9" detail="${10}"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(date -u '+%FT%TZ')" "$txid" "$phase" "$path" "$owner" "$class" \
    "$before" "$after" "$reclaimed" "$reason" "$POLICY_VERSION" "$detail" >> "$RECLAIM_LEDGER"
}

reclaim_class_allowed() {
  case "$1" in
    ephemeral-cache|active-ephemeral-cache|build-output|dependency-output) return 0 ;;
    *) return 1 ;;
  esac
}

reclaim_path() {
  local path="$1" owner="$2" class="$3" reason="$4"
  local before after reclaimed txid
  [ -e "$path" ] || return 0
  RECLAIM_SEQ=$((RECLAIM_SEQ + 1))
  txid="$(date -u '+%Y%m%dT%H%M%SZ')-$$-$RECLAIM_SEQ"
  before=$(path_bytes "$path")
  append_reclaim "$txid" planned "$path" "$owner" "$class" "${before:-unknown}" "${before:-unknown}" 0 "$reason" pending

  if ! reclaim_class_allowed "$class"; then
    append_reclaim "$txid" failed "$path" "$owner" "$class" "${before:-unknown}" "${before:-unknown}" 0 "$reason" unknown-class
    append_decision "$path" preserve unknown-reclaim-class
    return 1
  fi
  case "$before" in
    ''|*[!0-9]*)
      append_reclaim "$txid" failed "$path" "$owner" "$class" "${before:-unknown}" "${before:-unknown}" 0 "$reason" unreadable-before-bytes
      append_decision "$path" preserve unreadable-before-bytes
      return 1
      ;;
  esac
  if [ "$before" -le 0 ]; then
    append_reclaim "$txid" failed "$path" "$owner" "$class" "$before" "$before" 0 "$reason" zero-byte-reclaim
    append_decision "$path" preserve zero-byte-reclaim
    return 1
  fi
  if [ "$DRY_RUN" = 1 ]; then
    append_reclaim "$txid" failed "$path" "$owner" "$class" "$before" "$before" 0 "$reason" dry-run-preserved
    printf 'candidate\t%s\t%s\t%s\t%s\t%s\n' "$path" "$owner" "$class" "$before" "$POLICY_VERSION"
    return 0
  fi
  if [ "${EMERGENCY_GUARD_TEST_RM_FAIL_PATH:-}" = "$path" ] || ! rm -rf "$path" 2>/dev/null; then
    after=$(path_bytes "$path")
    append_reclaim "$txid" failed "$path" "$owner" "$class" "$before" "${after:-unknown}" 0 "$reason" remove-command-failed
    append_decision "$path" preserve reclaim-failed
    return 1
  fi
  after=$(path_bytes "$path")
  case "$after" in ''|*[!0-9]*) after=unknown ;; esac
  if [ -e "$path" ] || [ "$after" = unknown ]; then
    append_reclaim "$txid" failed "$path" "$owner" "$class" "$before" "$after" 0 "$reason" path-still-present
    append_decision "$path" preserve reclaim-failed
    return 1
  fi
  reclaimed=$((before - after))
  if [ "$reclaimed" -le 0 ]; then
    append_reclaim "$txid" failed "$path" "$owner" "$class" "$before" "$after" "$reclaimed" "$reason" zero-byte-reclaim
    append_decision "$path" preserve zero-byte-reclaim
    return 1
  fi
  append_reclaim "$txid" removed "$path" "$owner" "$class" "$before" "$after" "$reclaimed" "$reason" removed
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
  case "$days:$hours:$minutes:$seconds" in *[!0-9:]*) return 1 ;; esac
  printf '%s\n' "$((10#$days * 86400 + 10#$hours * 3600 + 10#$minutes * 60 + 10#$seconds))"
}

heartbeat_age() {
  local pid="$1" heartbeat mtime
  heartbeat="$LEASE_DIR/$pid.heartbeat"
  if [ "$TEST_MODE" -eq 1 ] && [ "${EMERGENCY_GUARD_TEST_HEARTBEAT_PID:-}" = "$pid" ]; then
    printf '0\n'
    return 0
  fi
  [ -f "$heartbeat" ] || return 1
  mtime=$(stat -f %m "$heartbeat" 2>/dev/null) || return 1
  printf '%s\n' "$(($(now_epoch) - mtime))"
}

profile_is_active() {
  local profile="$1"
  if [ "$TEST_MODE" -eq 1 ]; then
    [ "${EMERGENCY_GUARD_TEST_ACTIVE_PROFILE:-}" = "$profile" ]
    return
  fi
  pgrep -f -- "--user-data-dir=$profile([[:space:]]|$)" >/dev/null 2>&1
}

# Prints exactly one of: open, confirmed-closed, error.
path_open_state() {
  local path="$1" output rc
  if [ "$TEST_MODE" -eq 1 ]; then
    if [ "${EMERGENCY_GUARD_TEST_OPEN_PATH:-}" = "$path" ]; then
      printf 'open\n'
    elif [ "${EMERGENCY_GUARD_TEST_LSOF_ERROR_PATH:-}" = "$path" ]; then
      printf 'error\n'
    else
      printf 'confirmed-closed\n'
    fi
    return
  fi
  command -v lsof >/dev/null 2>&1 || { printf 'error\n'; return; }
  output=$(lsof +D "$path" 2>&1)
  rc=$?
  if [ "$rc" -eq 0 ]; then
    printf 'open\n'
  elif [ "$rc" -eq 1 ] && [ -z "$output" ]; then
    printf 'confirmed-closed\n'
  else
    printf 'error\n'
  fi
}

reclaim_if_confirmed_closed() {
  local path="$1" owner="$2" class="$3" reason="$4" state
  [ -e "$path" ] || return 0
  state=$(path_open_state "$path")
  case "$state" in
    confirmed-closed) reclaim_path "$path" "$owner" "$class" "$reason" ;;
    open) append_decision "$path" preserve open-path-preserved ;;
    *) append_decision "$path" preserve lsof-error-preserved ;;
  esac
}

lease_value() {
  local lease="$1" key="$2"
  awk -F= -v key="$key" '
    $1 == key { count++; sub(/^[^=]*=/, ""); value=$0 }
    END { if (count != 1) exit 1; print value }
  ' "$lease" 2>/dev/null
}

fixture_field() {
  local pid="$1" column="$2"
  awk -F '\t' -v pid="$pid" -v column="$column" '$1 == pid { print $column; found=1; exit } END { if (!found) exit 1 }' \
    "$EMERGENCY_GUARD_TEST_PROCESS_FIXTURE"
}

observed_start() {
  local pid="$1" stage="$2"
  if [ "$TEST_MODE" -eq 1 ]; then
    if [ "$stage" = initial ]; then fixture_field "$pid" 2; else fixture_field "$pid" 6; fi
  else
    ps -p "$pid" -o lstart= 2>/dev/null | awk '{$1=$1; if (NF) print}'
  fi
}

observed_pgid() {
  local pid="$1" stage="$2"
  if [ "$TEST_MODE" -eq 1 ]; then
    if [ "$stage" = initial ]; then fixture_field "$pid" 3; else fixture_field "$pid" 7; fi
  else
    ps -p "$pid" -o pgid= 2>/dev/null | awk '{$1=$1; if (NF) print}'
  fi
}

observed_argv() {
  local pid="$1" stage="$2"
  if [ "$TEST_MODE" -eq 1 ]; then
    if [ "$stage" = initial ]; then fixture_field "$pid" 5; else fixture_field "$pid" 8; fi
  else
    ps -p "$pid" -o command= 2>/dev/null | awk '{$1=$1; if (NF) print}'
  fi
}

observed_elapsed() {
  local pid="$1" raw
  if [ "$TEST_MODE" -eq 1 ]; then
    fixture_field "$pid" 4
  else
    raw=$(ps -p "$pid" -o etime= 2>/dev/null) || return 1
    etime_seconds "$raw"
  fi
}

group_members() {
  local pgid="$1"
  if [ "$TEST_MODE" -eq 1 ]; then
    [ "$(fixture_field "$pgid" 9 2>/dev/null || true)" = gone ] || printf '%s\n' "$pgid"
  else
    ps -axo pid=,pgid= 2>/dev/null | awk -v pgid="$pgid" '$2 == pgid { print $1 }'
  fi
}

descendants_same_group() {
  local root="$1" pgid="$2" descendant descendant_pgid
  [ "$TEST_MODE" -eq 1 ] && return 0
  while IFS= read -r descendant; do
    [ -n "$descendant" ] || continue
    descendant_pgid=$(ps -p "$descendant" -o pgid= 2>/dev/null | awk '{$1=$1; print}')
    [ "$descendant_pgid" = "$pgid" ] || return 1
  done < <(ps -axo pid=,ppid= 2>/dev/null | awk -v root="$root" '
    { pid[NR]=$1; parent[NR]=$2 }
    END {
      marked[root]=1
      changed=1
      while (changed) {
        changed=0
        for (i=1; i<=NR; i++) if (marked[parent[i]] && !marked[pid[i]]) { marked[pid[i]]=1; changed=1 }
      }
      for (i=1; i<=NR; i++) if (pid[i] != root && marked[pid[i]]) print pid[i]
    }
  ')
}

lease_matches_observation() {
  local lease="$1" pid="$2" expected_start="$3" expected_pgid="$4" expected_argv="$5" stage="$6"
  local lease_pid lease_start lease_pgid lease_argv actual_start actual_pgid actual_argv
  lease_pid=$(lease_value "$lease" pid) || return 1
  lease_start=$(lease_value "$lease" start_token) || return 1
  lease_pgid=$(lease_value "$lease" pgid) || return 1
  lease_argv=$(lease_value "$lease" canonical_argv) || return 1
  [ "$lease_pid" = "$pid" ] && [ "$lease_start" = "$expected_start" ] && \
    [ "$lease_pgid" = "$expected_pgid" ] && [ "$lease_argv" = "$expected_argv" ] || return 1
  actual_start=$(observed_start "$pid" "$stage") || return 1
  actual_pgid=$(observed_pgid "$pid" "$stage") || return 1
  actual_argv=$(observed_argv "$pid" "$stage") || return 1
  [ "$actual_start" = "$expected_start" ] && [ "$actual_pgid" = "$expected_pgid" ] && \
    [ "$actual_argv" = "$expected_argv" ] || return 1
  descendants_same_group "$pid" "$expected_pgid"
}

stop_runaway() {
  local lease="$1" pid="$2" start_token="$3" pgid="$4" argv="$5" reason="$6"
  local i members snapshot member
  STOP_DECISION=preserve
  STOP_REASON=revalidation-failed

  snapshot=$(group_members "$pgid")
  # The lease and all three kernel-observed identity fields are checked again
  # immediately before the first signal. No substring-derived PID enters here.
  lease_matches_observation "$lease" "$pid" "$start_token" "$pgid" "$argv" recheck || return 1
  if [ "$DRY_RUN" = 1 ]; then
    STOP_DECISION=preserve
    STOP_REASON=dry-run-candidate
    return 0
  fi
  if [ "$TEST_MODE" -eq 1 ]; then
    printf '%s\t%s\t%s\n' "$pid" "$reason" "$pgid" >> "$EMERGENCY_GUARD_TEST_KILL_LEDGER"
    if [ "$(fixture_field "$pid" 9 2>/dev/null || true)" = gone ]; then
      STOP_DECISION=stopped
      STOP_REASON="$reason"
      return 0
    fi
    STOP_DECISION=failed
    STOP_REASON=process-group-survived
    return 1
  fi

  /bin/kill -TERM "-$pgid" 2>/dev/null || {
    STOP_DECISION=failed
    STOP_REASON=term-signal-failed
    return 1
  }
  i=0
  while [ -n "$(group_members "$pgid")" ] && [ "$i" -lt 5 ]; do sleep 1; i=$((i + 1)); done
  if [ -n "$(group_members "$pgid")" ]; then
    /bin/kill -KILL "-$pgid" 2>/dev/null || true
    i=0
    while [ -n "$(group_members "$pgid")" ] && [ "$i" -lt 5 ]; do sleep 1; i=$((i + 1)); done
  fi
  members=$(group_members "$pgid")
  if [ -n "$members" ]; then
    STOP_DECISION=failed
    STOP_REASON=process-group-survived
    return 1
  fi
  for member in $snapshot; do
    if ps -p "$member" >/dev/null 2>&1; then
      STOP_DECISION=failed
      STOP_REASON="descendant-survived"
      return 1
    fi
  done
  STOP_DECISION=stopped
  STOP_REASON="$reason"
}

evaluate_lease() {
  local lease="$1" basename pid start_token pgid argv actual_start actual_pgid actual_argv elapsed hb_age
  basename=${lease##*/}
  pid=${basename%.lease}
  case "$pid" in ''|*[!0-9]*) append_decision "$pid" preserve invalid-lease-pid; return ;; esac
  start_token=$(lease_value "$lease" start_token) || { append_decision "$pid" preserve invalid-lease; return; }
  pgid=$(lease_value "$lease" pgid) || { append_decision "$pid" preserve invalid-lease; return; }
  argv=$(lease_value "$lease" canonical_argv) || { append_decision "$pid" preserve invalid-lease; return; }
  [ "$(lease_value "$lease" pid 2>/dev/null || true)" = "$pid" ] || { append_decision "$pid" preserve invalid-lease-pid; return; }
  case "$pgid" in ''|*[!0-9]*) append_decision "$pid" preserve invalid-lease-pgid; return ;; esac
  [ "$pgid" = "$pid" ] || { append_decision "$pid" preserve lease-not-dedicated-pgid; return; }
  [ "$argv" = "$CANONICAL_GIG_ARGV" ] || { append_decision "$pid" preserve lease-argv-not-allowed; return; }

  actual_start=$(observed_start "$pid" initial 2>/dev/null || true)
  [ "$actual_start" = "$start_token" ] || { append_decision "$pid" preserve lease-start-token-mismatch; return; }
  actual_pgid=$(observed_pgid "$pid" initial 2>/dev/null || true)
  [ "$actual_pgid" = "$pgid" ] || { append_decision "$pid" preserve lease-pgid-mismatch; return; }
  actual_argv=$(observed_argv "$pid" initial 2>/dev/null || true)
  [ "$actual_argv" = "$argv" ] || { append_decision "$pid" preserve lease-argv-mismatch; return; }
  descendants_same_group "$pid" "$pgid" || { append_decision "$pid" preserve descendant-outside-dedicated-pgid; return; }
  elapsed=$(observed_elapsed "$pid" 2>/dev/null || true)
  case "$elapsed" in ''|*[!0-9]*) append_decision "$pid" preserve invalid-elapsed; return ;; esac
  if hb_age=$(heartbeat_age "$pid") && [ "$hb_age" -le "$GIG_HEARTBEAT_MAX_SECONDS" ]; then
    append_decision "$pid" preserve fresh-heartbeat
    return
  fi
  if [ "$pid" = "$GIG_LOCK_PID" ] && [ "$elapsed" -le "$GIG_WORKER_MAX_SECONDS" ]; then
    append_decision "$pid" preserve lock-owner
    return
  fi
  if [ "$elapsed" -le "$GIG_WORKER_MAX_SECONDS" ]; then
    append_decision "$pid" preserve within-timeout
    return
  fi
  stop_runaway "$lease" "$pid" "$start_token" "$pgid" "$argv" stale-runaway || true
  append_decision "$pid" "$STOP_DECISION" "$STOP_REASON"
}

evaluate_gig_workers() {
  local lease
  [ -d "$LEASE_DIR" ] || return 0
  for lease in "$LEASE_DIR"/*.lease; do
    [ -f "$lease" ] || continue
    evaluate_lease "$lease"
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
    [ -e "$bundle" ] || continue
    reclaim_if_confirmed_closed "$bundle" claude-vm ephemeral-cache regenerated-by-claude
  done
  reclaim_path "$HOME_DIR/.cache/whisper" whisper ephemeral-cache model-redownload
  reclaim_path "$HOME_DIR/.cache/torch" torch ephemeral-cache model-redownload
  reclaim_path "$HOME_DIR/.cache/uv" uv ephemeral-cache package-redownload
  reclaim_if_confirmed_closed "$HOME_DIR/.cache/codex-runtimes" codex ephemeral-cache runtime-redownload
  reclaim_if_confirmed_closed "$HOME_DIR/.codex/.tmp" codex ephemeral-cache plugin-staging-regenerated
  reclaim_path "$HOME_DIR/Library/Caches/pip" pip ephemeral-cache package-redownload
  if ! pgrep -f '/Library/Caches/ms-playwright/' >/dev/null 2>&1; then
    reclaim_path "$HOME_DIR/Library/Caches/ms-playwright" playwright ephemeral-cache browser-redownload
  fi
  if ! pgrep -f '[/](cargo|rustc)([[:space:]]|$)' >/dev/null 2>&1; then
    reclaim_path "$HOME_DIR/.cargo/registry" cargo ephemeral-cache crate-redownload
  fi
  for profile in "$HOME_DIR"/.cloak/profiles/*; do
    [ -d "$profile" ] || continue
    if profile_is_active "$profile"; then
      append_decision "$profile" preserve active-browser-identity-preserved
      for cache in "$profile/Default/Cache" "$profile/Default/Code Cache" "$profile/Default/GPUCache"; do
        reclaim_path "$cache" cloakbrowser active-ephemeral-cache browser-cache-regenerated
      done
      continue
    fi
    for cache in \
      "$profile/Default/Cache" "$profile/Default/Code Cache" "$profile/Default/GPUCache" \
      "$profile/ShaderCache" "$profile/GrShaderCache" "$profile/GraphiteDawnCache"; do
      reclaim_path "$cache" cloakbrowser ephemeral-cache browser-cache-regenerated
    done
  done
  # runs/*/reel-text.mp4 is intentionally not age-deleted. It remains protected
  # until a producer lease and finalized-output classification exist.
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
  if [ -n "${EMERGENCY_GUARD_TEST_EXTRA_RECLAIM:-}" ]; then
    reclaim_path "$EMERGENCY_GUARD_TEST_EXTRA_RECLAIM" test unknown-class negative-probe
  fi
fi

if [ "$FREE" -lt "$ULTRA_GB" ]; then
  evaluate_gig_workers
  log "ULTRA: applied backpressure; lease-only worker containment complete"
fi

NEW=$(free_gb)
log "safe containment done: ${FREE}GB -> ${NEW}GB free"
