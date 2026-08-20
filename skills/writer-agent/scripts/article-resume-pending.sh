#!/usr/bin/env bash
# Durable 300-second publication-contract pending worker. It never creates a run or topic. A crash-truncated
# pre-live target set may initialize only its explicitly missing targets in a publication-free tick.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
# Load runtime credentials exactly like article-daily.sh so remote reconciles
# (e.g. publication_remote.devto) never fail closed on a missing API key.
set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a

ARTICLE_ROOT="${ARTICLE_ROOT:-$HOME/profitable-claude/skills/writer-agent}"
STATE_DIR="${ARTICLE_STATE_DIR:-$ARTICLE_ROOT/state}"
LOG="${ARTICLE_RESUME_LOG:-$HOME/.openclaw/logs/article-resume.log}"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-$ARTICLE_ROOT/runtime/model-runner.sh}"
MODEL_SUPPORT="${ARTICLE_MODEL_SUPPORT:-$ARTICLE_ROOT/runtime/model-runner-support.py}"
QUALITY_REPAIR_CONTROL="${ARTICLE_QUALITY_REPAIR_CONTROL:-$ARTICLE_ROOT/scripts/quality_repair_control.py}"
QUALITY_FEEDBACK_CONTROL="${ARTICLE_QUALITY_FEEDBACK_CONTROL:-$ARTICLE_ROOT/scripts/quality_feedback_recovery.py}"
PLANNER="$ARTICLE_ROOT/scripts/article_pending.py"
LOCK_DIR="$STATE_DIR/.article-daily.lockdir"
LOCK_OWNER_FILE="$LOCK_DIR/owner.pid"
# Keep nested publisher and gate processes on the same immutable release root.
# Without this export a launchd worker can fall back to an empty compatibility
# directory when the model invokes scripts/run.sh.
ARTICLE_SKILL_DIR="$ARTICLE_ROOT"
export ARTICLE_ROOT ARTICLE_STATE_DIR STATE_DIR ARTICLE_SKILL_DIR
mkdir -p "$(dirname "$LOG")"

[ -d "$STATE_DIR/runs" ] || exit 0

# A durable local pause is the emergency brake for an external-publication
# worker.  It is checked before lock acquisition, reconciliation, or any
# publisher invocation so a launchd tick cannot create a second side effect
# while a prior failure is being verified.
PUBLICATION_PAUSE_FILE="${ARTICLE_PUBLICATION_PAUSE_FILE:-$STATE_DIR/.publication-paused}"
if [ -f "$PUBLICATION_PAUSE_FILE" ]; then
  echo "article-resume: publication paused file=$PUBLICATION_PAUSE_FILE" >>"$LOG"
  exit 0
fi
if [ "${ARTICLE_OWNER_FENCE_ACTIVE:-0}" != "1" ]; then
  OWNER_FENCE_DIR="${ARTICLE_OWNER_FENCE_DIR:-$HOME/.local/state/life-manager/writer/owner-fence}"
  export ARTICLE_OWNER_FENCE_DIR
  exec python3 "$ARTICLE_ROOT/scripts/writer_owner_fence.py" run \
    --fence-dir "$OWNER_FENCE_DIR" --owner article-resume \
    --root "$ARTICLE_ROOT" --state "$STATE_DIR" \
    --run-id "${ARTICLE_EXPECTED_RUN_ID:-daily-$(TZ=Asia/Tokyo date +%F)}" \
    -- "$0" "$@"
fi

# A publisher must not create an irreversible external effect when its durable
# receipt, circuit, or outbox cannot be persisted. Resume has no cleanup rights;
# it fails closed until the host has the same 5 GiB safety floor as the creator.
DISK_MIN_FREE_BYTES="${ARTICLE_RESUME_MIN_FREE_BYTES:-$((5 * 1024 * 1024 * 1024))}"
disk_free_bytes() {
  local free_kb
  free_kb="$(df -Pk / 2>/dev/null | awk 'NR==2{print $4}')"
  echo $(( ${free_kb:-0} * 1024 ))
}
DISK_FREE_BYTES="$(disk_free_bytes)"
if [ "${DISK_FREE_BYTES:-0}" -lt "$DISK_MIN_FREE_BYTES" ]; then
  echo "article-resume: disk floor blocked publication free=${DISK_FREE_BYTES}bytes required=${DISK_MIN_FREE_BYTES}bytes" >>"$LOG"
  exit 0
fi

process_owns_this_publication_lock() {
  local owner_pid="$1" owner_command owner_cwd token token_dir token_base resolved
  owner_command="$(ps -p "$owner_pid" -o command= 2>/dev/null || true)"
  [ -n "$owner_command" ] || return 1
  for token in $owner_command; do
    case "$token" in
      "$ARTICLE_ROOT/article-daily.sh"|\
      "$ARTICLE_ROOT/scripts/article-resume-pending.sh"|\
      "$ARTICLE_ROOT/scripts/zenn-deferred-worker.py"|\
      "$ARTICLE_ROOT/scripts/current_run_media_upgrade.py") return 0 ;;
    esac
  done
  owner_cwd="$(/usr/sbin/lsof -a -p "$owner_pid" -d cwd -Fn 2>/dev/null \
    | sed -n 's/^n//p' | head -1)"
  [ -n "$owner_cwd" ] || return 1
  for token in $owner_command; do
    case "$token" in
      *article-daily.sh|*article-resume-pending.sh|\
      *zenn-deferred-worker.py|*current_run_media_upgrade.py)
        case "$token" in /*) resolved="$token" ;; *)
          token_dir="$(dirname "$token")"
          token_base="$(basename "$token")"
          resolved="$(cd "$owner_cwd/$token_dir" 2>/dev/null \
            && printf '%s/%s' "$PWD" "$token_base")"
          ;;
        esac
        case "$resolved" in
          "$ARTICLE_ROOT/article-daily.sh"|\
          "$ARTICLE_ROOT/scripts/article-resume-pending.sh"|\
          "$ARTICLE_ROOT/scripts/zenn-deferred-worker.py"|\
          "$ARTICLE_ROOT/scripts/current_run_media_upgrade.py") return 0 ;;
        esac
        ;;
    esac
  done
  return 1
}

release_publication_lock() {
  local recorded_owner=""
  recorded_owner="$(cat "$LOCK_OWNER_FILE" 2>/dev/null || true)"
  if [ "$recorded_owner" = "$$" ]; then
    rm -f -- "$LOCK_OWNER_FILE"
    rmdir "$LOCK_DIR" 2>/dev/null
  else
    return 1
  fi
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  # A SIGTERM between mkdir and the EXIT trap can leave an empty ownerless
  # directory forever. Recover only that exact shape, and only after proving
  # no *other* publication worker process is alive. Unexpected lock contents
  # remain fail-closed.
  OTHER_OWNER=""
  RECORDED_OWNER="$(cat "$LOCK_OWNER_FILE" 2>/dev/null || true)"
  case "$RECORDED_OWNER" in
    '') ;;
    *[!0-9]*) OTHER_OWNER="invalid-owner-record" ;;
    *)
      if [ "$RECORDED_OWNER" != "$$" ] \
        && kill -0 "$RECORDED_OWNER" 2>/dev/null \
        && process_owns_this_publication_lock "$RECORDED_OWNER"; then
        OTHER_OWNER="$RECORDED_OWNER"
      fi
      ;;
  esac
  # Match process basenames, not only absolute command strings. A manual
  # kickstart such as `bash skills/writer-agent/scripts/article-resume-pending.sh`
  # is the same owner as launchd's absolute invocation; the old absolute
  # pgrep missed it and let launchd steal the empty directory lock.
  for OWNER_COMMAND in \
    'article-daily\.sh' \
    'article-resume-pending\.sh' \
    'zenn-deferred-worker\.py' \
    'current_run_media_upgrade\.py'; do
    while IFS= read -r OWNER_PID; do
      if [ -n "$OWNER_PID" ] && [ "$OWNER_PID" != "$$" ] \
        && process_owns_this_publication_lock "$OWNER_PID"; then
        OTHER_OWNER="$OWNER_PID"
        break 2
      fi
    done < <(pgrep -f "$OWNER_COMMAND" 2>/dev/null || true)
  done
  # article-daily records both PID and process-start time. Treat those two
  # files as lock metadata; older recovery code whitelisted owner.pid only and
  # left every stale lock permanently wedged after a normal exit.
  LOCK_EXTRA="$(find "$LOCK_DIR" -mindepth 1 -maxdepth 1 \
    ! -name owner.pid ! -name owner.start -print -quit 2>/dev/null)"
  if [ -z "$OTHER_OWNER" ] \
    && { [ -z "$RECORDED_OWNER" ] \
      || { [ -f "$LOCK_OWNER_FILE" ] && [ -f "$LOCK_DIR/owner.start" ] \
        && [ -z "$LOCK_EXTRA" ] \
        && rm -f -- "$LOCK_OWNER_FILE" "$LOCK_DIR/owner.start"; }; } \
    && [ -z "$(find "$LOCK_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ] \
    && rmdir "$LOCK_DIR" 2>/dev/null \
    && mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "article-resume: recovered ownerless publication lock" >>"$LOG"
  else
    echo "article-resume: shared publication lock is held" >>"$LOG"
    exit 0
  fi
fi
printf '%s\n' "$$" >"$LOCK_OWNER_FILE" || {
  rmdir "$LOCK_DIR" 2>/dev/null || true
  exit 1
}
trap 'release_publication_lock' EXIT

# The same 300-second reconciler owns both sides of the publication boundary.
# A safe interrupted generation has no public side effect, so hand the exact
# saved run/prompt back to the daily wrapper; that wrapper revalidates the
# immutable boundary and invokes it once. Never create a run from this worker.
START_CONTROL="${ARTICLE_START_CONTROL:-$ARTICLE_ROOT/scripts/article_daily_start_control.py}"
LOCAL_DATE="${ARTICLE_LOCAL_DATE:-$(TZ=Asia/Tokyo date +%F)}"
PRE_START_DECISION="$(python3 "$START_CONTROL" \
  --state-dir "$STATE_DIR" --local-date "$LOCAL_DATE" 2>>"$LOG" || \
  printf '%s' '{"action":"block-incomplete","reason":"start-control-error"}')"
PRE_START_ACTION="$(printf '%s' "$PRE_START_DECISION" | jq -r '.action // empty')"
# A persisted publication backlog is the foreground availability contract.
# Inspect it before today's schedule decision so midnight and quality work
# cannot starve an older immutable active-four run.
PRIORITY_PUBLICATION_PLAN='{"status":"SKIPPED","reason":"start-control-blocked"}'
PRIORITY_PUBLICATION_READY=0
if [ "$PRE_START_ACTION" != "block-incomplete" ]; then
  PRIORITY_PLAN_ARGS=(--state-root "$STATE_DIR")
  [ -n "${ARTICLE_NOW:-}" ] && PRIORITY_PLAN_ARGS+=(--now "$ARTICLE_NOW")
  PRIORITY_PUBLICATION_PLAN="$(python3 "$PLANNER" "${PRIORITY_PLAN_ARGS[@]}" 2>>"$LOG" || true)"
  if [ "$(printf '%s' "$PRIORITY_PUBLICATION_PLAN" | jq -r '.status // empty')" = "READY" ] \
    && [ "$(printf '%s' "$PRIORITY_PUBLICATION_PLAN" | jq '((.initialization_pairs // []) + (.eligible_pairs // []) + (.recovery_pairs // [])) | length')" -gt 0 ]; then
    PRIORITY_PUBLICATION_READY=1
  fi
fi
# The 06:00 calendar job remains the normal creator. If the host was asleep,
# launchd was unloaded, or that event was otherwise missed, the five-minute
# reconciler must start today's one run as soon as the scheduled hour has
# passed. Before 06:00 it does nothing; a catch-up never creates tomorrow's
# article early.
LOCAL_HOUR="${ARTICLE_LOCAL_HOUR:-$(TZ=Asia/Tokyo date +%H)}"
DAILY_SCHEDULE_HOUR="${ARTICLE_DAILY_SCHEDULE_HOUR:-6}"
case "$LOCAL_HOUR" in
  0[0-9]|1[0-9]|2[0-3]) ;;
  *) echo "article-resume: invalid local hour; catch-up blocked" >>"$LOG"; exit 1 ;;
esac
case "$DAILY_SCHEDULE_HOUR" in
  [0-9]|1[0-9]|2[0-3]) ;;
  *) echo "article-resume: invalid daily schedule hour; catch-up blocked" >>"$LOG"; exit 1 ;;
esac
LOCAL_HOUR_VALUE="${LOCAL_HOUR#0}"
[ -n "$LOCAL_HOUR_VALUE" ] || LOCAL_HOUR_VALUE=0
if [ "$PRE_START_ACTION" = "new" ] \
  && [ "$PRIORITY_PUBLICATION_READY" -ne 1 ]; then
  if [ "$LOCAL_HOUR_VALUE" -lt "$DAILY_SCHEDULE_HOUR" ]; then
    echo "article-resume: daily schedule not due date=$LOCAL_DATE hour=$LOCAL_HOUR" >>"$LOG"
    exit 0
  fi
  echo "article-resume: missed daily schedule catch-up date=$LOCAL_DATE hour=$LOCAL_HOUR" >>"$LOG"
  export ARTICLE_EXPECTED_NEW_DAILY_DATE="$LOCAL_DATE"
  trap - EXIT
  release_publication_lock || exit 1
  exec bash "$ARTICLE_ROOT/article-daily.sh"
fi

GENERATION_RUN_ID="$(printf '%s' "$PRE_START_DECISION" | jq -r '.run_id // empty')"
case "$GENERATION_RUN_ID" in
  daily-????-??-??|????????-??????) ;;
  *) GENERATION_RUN_ID="daily-$LOCAL_DATE" ;;
esac
GENERATION_RUN_DIR="$STATE_DIR/runs/$GENERATION_RUN_ID"
GENERATION_STATE_PATH="$GENERATION_RUN_DIR/gates/generation-state.json"

# A replacement that consumed its one normal reroute may receive one research-first
# recovery on the same run. It runs before legacy/source-defect repair because its
# terminal receipts are current and its missing evidence is the actual input.
QUALITY_LEDGER="$STATE_DIR/articles.jsonl"
QUALITY_FEEDBACK_PLAN="$(python3 "$QUALITY_FEEDBACK_CONTROL" plan \
  --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" 2>>"$LOG" || true)"
if [ "$PRIORITY_PUBLICATION_READY" -ne 1 ] \
  && [ "$(printf '%s' "$QUALITY_FEEDBACK_PLAN" | jq -r '.status // empty')" = "READY" ]; then
  QUALITY_FEEDBACK_REASON="$(printf '%s' "$QUALITY_FEEDBACK_PLAN" | jq -r '.reason // empty')"
  if [ "$QUALITY_FEEDBACK_REASON" = "terminal-quality-feedback" ]; then
    QUALITY_FEEDBACK_READY="$(python3 "$QUALITY_FEEDBACK_CONTROL" begin \
      --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" 2>>"$LOG")" || {
      echo "article-resume: bounded quality feedback begin failed closed" >>"$LOG"
      exit 1
    }
  elif [ "$QUALITY_FEEDBACK_REASON" = "terminal-quality-publication-handoff" ]; then
    QUALITY_FEEDBACK_READY="$(python3 "$QUALITY_FEEDBACK_CONTROL" handoff \
      --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" 2>>"$LOG")" || {
      echo "article-resume: quality publication handoff failed closed" >>"$LOG"
      exit 1
    }
  else
    QUALITY_FEEDBACK_READY="$QUALITY_FEEDBACK_PLAN"
  fi
  QUALITY_FEEDBACK_RUN_ID="$(printf '%s' "$QUALITY_FEEDBACK_READY" | jq -r '.run_id // empty')"
  [ -n "$QUALITY_FEEDBACK_RUN_ID" ] || QUALITY_FEEDBACK_RUN_ID="$(basename "$GENERATION_RUN_DIR")"
  QUALITY_FEEDBACK_PROMPT="$(printf '%s' "$QUALITY_FEEDBACK_READY" | jq -r '.prompt_path // empty')"
  if [ ! -f "$QUALITY_FEEDBACK_PROMPT" ]; then
    echo "article-resume: bounded quality feedback prompt missing" >>"$LOG"
    exit 1
  fi
  PROVIDER="${ARTICLE_PROVIDER:-auto}"
  HEALTH_FILE="${ARTICLE_PROVIDER_HEALTH:-$STATE_DIR/provider-health.json}"
  PROVIDER_READY=0
  for CANDIDATE in $([ "$PROVIDER" = "auto" ] && printf 'codex claude' || printf '%s' "$PROVIDER"); do
    if python3 "$MODEL_SUPPORT" eligible --file "$HEALTH_FILE" \
      --provider "$CANDIDATE" --mode agent >/dev/null 2>&1; then
      PROVIDER_READY=1
      break
    fi
  done
  if [ "$PROVIDER_READY" -ne 1 ]; then
    echo "article-resume: bounded quality feedback remains in provider cooldown run=$QUALITY_FEEDBACK_RUN_ID" >>"$LOG"
    exit 0
  fi
  QUALITY_FEEDBACK_INVOKING="$(python3 "$QUALITY_FEEDBACK_CONTROL" invoke \
    --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" \
    --owner-pid "$$" 2>>"$LOG")" || {
    echo "article-resume: bounded quality feedback invoke failed closed run=$QUALITY_FEEDBACK_RUN_ID" >>"$LOG"
    exit 1
  }
  printf '%s\n' "$QUALITY_FEEDBACK_INVOKING" >>"$LOG"
  INVOKING_FEEDBACK_PROMPT="$(printf '%s' "$QUALITY_FEEDBACK_INVOKING" | jq -r '.prompt_path // empty')"
  [ -n "$INVOKING_FEEDBACK_PROMPT" ] && QUALITY_FEEDBACK_PROMPT="$INVOKING_FEEDBACK_PROMPT"
  export ARTICLE_RUN_DIR="$GENERATION_RUN_DIR"
  export ARTICLE_QUALITY_FEEDBACK_ACTIVE=1
  export ARTICLE_QUALITY_FEEDBACK_OWNER_PID="$$"
  ARTICLE_MODEL_LOG="$LOG" bash "$ARTICLE_ROOT/runtime/judge-broker.sh" "$GENERATION_RUN_DIR" &
  JUDGE_BROKER_PID=$!
  ARTICLE_RUN_ID="$QUALITY_FEEDBACK_RUN_ID" ARTICLE_MODEL_LOG="$LOG" \
    "$MODEL_RUNNER" agent --prompt-file "$QUALITY_FEEDBACK_PROMPT"
  RC=$?
  kill "$JUDGE_BROKER_PID" 2>/dev/null || true
  wait "$JUDGE_BROKER_PID" 2>/dev/null || true
  python3 "$QUALITY_FEEDBACK_CONTROL" result \
    --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" \
    --return-code "$RC" --owner-pid "$$" >>"$LOG" 2>&1 || {
    echo "article-resume: bounded quality feedback result failed closed run=$QUALITY_FEEDBACK_RUN_ID rc=$RC" >>"$LOG"
    exit 1
  }
  echo "article-resume: bounded quality feedback recovery run=$QUALITY_FEEDBACK_RUN_ID rc=$RC" >>"$LOG"
  exit 0
fi

# Reopen only an exact unpublished legacy block or a hash-bound tracked source
# defect whose fixed gate now passes. The start controller selects the newest
# same-day run, including timestamp replacement IDs. This runs before the
# generic publication planner so older backlog cannot starve today's article.
QUALITY_PLAN="$(python3 "$QUALITY_REPAIR_CONTROL" plan \
  --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" 2>>"$LOG" || true)"
if [ "$PRIORITY_PUBLICATION_READY" -ne 1 ] \
  && [ "$(printf '%s' "$QUALITY_PLAN" | jq -r '.status // empty')" = "READY" ]; then
  QUALITY_REASON="$(printf '%s' "$QUALITY_PLAN" | jq -r '.reason // empty')"
  if [ "$QUALITY_REASON" = "structurally-exhausted-quality-evaluations" ]; then
    python3 "$QUALITY_REPAIR_CONTROL" terminalize \
      --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" >>"$LOG" 2>&1 || {
      echo "article-resume: deterministic quality terminalization failed closed" >>"$LOG"
      exit 1
    }
    echo "article-resume: deterministic quality terminalization run=$GENERATION_RUN_ID" >>"$LOG"
    exit 0
  elif [ "$QUALITY_REASON" = "legacy-stale-quality-block" ] \
    || [ "$QUALITY_REASON" = "tracked-bookmark-source-defect" ] \
    || [ "$QUALITY_REASON" = "tracked-reader-terminal-source-defect" ] \
    || [ "$QUALITY_REASON" = "tracked-editorial-hash-scope-source-defect" ] \
    || [ "$QUALITY_REASON" = "tracked-topic-router-reroute-source-defect" ]; then
    QUALITY_READY="$(python3 "$QUALITY_REPAIR_CONTROL" begin \
      --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" 2>>"$LOG")" || {
      echo "article-resume: bounded quality repair begin failed closed" >>"$LOG"
      exit 1
    }
  else
    QUALITY_READY="$QUALITY_PLAN"
  fi
  QUALITY_RUN_ID="$(printf '%s' "$QUALITY_READY" | jq -r '.run_id // empty')"
  [ -n "$QUALITY_RUN_ID" ] || QUALITY_RUN_ID="$(basename "$GENERATION_RUN_DIR")"
  QUALITY_PROMPT="$(printf '%s' "$QUALITY_READY" | jq -r '.prompt_path // empty')"
  if [ ! -f "$QUALITY_PROMPT" ]; then
    echo "article-resume: bounded quality repair prompt missing" >>"$LOG"
    exit 1
  fi
  PROVIDER="${ARTICLE_PROVIDER:-auto}"
  HEALTH_FILE="${ARTICLE_PROVIDER_HEALTH:-$STATE_DIR/provider-health.json}"
  PROVIDER_READY=0
  for CANDIDATE in $([ "$PROVIDER" = "auto" ] && printf 'codex claude' || printf '%s' "$PROVIDER"); do
    if python3 "$MODEL_SUPPORT" eligible --file "$HEALTH_FILE" \
      --provider "$CANDIDATE" --mode agent >/dev/null 2>&1; then
      PROVIDER_READY=1
      break
    fi
  done
  if [ "$PROVIDER_READY" -ne 1 ]; then
    echo "article-resume: bounded quality repair remains in provider cooldown run=$QUALITY_RUN_ID" >>"$LOG"
    exit 0
  fi
  QUALITY_INVOKING="$(python3 "$QUALITY_REPAIR_CONTROL" invoke \
    --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" \
    --owner-pid "$$" 2>>"$LOG")" || {
    echo "article-resume: bounded quality repair invoke failed closed run=$QUALITY_RUN_ID" >>"$LOG"
    exit 1
  }
  printf '%s\n' "$QUALITY_INVOKING" >>"$LOG"
  INVOKING_PROMPT="$(printf '%s' "$QUALITY_INVOKING" | jq -r '.prompt_path // empty')"
  [ -n "$INVOKING_PROMPT" ] && QUALITY_PROMPT="$INVOKING_PROMPT"
  export ARTICLE_RUN_DIR="$GENERATION_RUN_DIR"
  export ARTICLE_QUALITY_REPAIR_ACTIVE=1
  export ARTICLE_QUALITY_REPAIR_OWNER_PID="$$"
  ARTICLE_MODEL_LOG="$LOG" bash "$ARTICLE_ROOT/runtime/judge-broker.sh" "$GENERATION_RUN_DIR" &
  JUDGE_BROKER_PID=$!
  ARTICLE_RUN_ID="$QUALITY_RUN_ID" ARTICLE_MODEL_LOG="$LOG" \
    "$MODEL_RUNNER" agent --prompt-file "$QUALITY_PROMPT"
  RC=$?
  kill "$JUDGE_BROKER_PID" 2>/dev/null || true
  wait "$JUDGE_BROKER_PID" 2>/dev/null || true
  python3 "$QUALITY_REPAIR_CONTROL" result \
    --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" \
    --return-code "$RC" >>"$LOG" 2>&1 || {
    echo "article-resume: bounded quality repair result failed closed run=$QUALITY_RUN_ID rc=$RC" >>"$LOG"
    exit 1
  }
  echo "article-resume: bounded quality repair run=$QUALITY_RUN_ID rc=$RC" >>"$LOG"
  exit 0
fi

if [ -f "$GENERATION_STATE_PATH" ] \
  && [ ! -f "$GENERATION_RUN_DIR/gates/publication-state.json" ] \
  && [ "$(jq -r '.status // empty' "$GENERATION_STATE_PATH")" = "invoking" ]; then
  python3 "$ARTICLE_ROOT/scripts/article_generation_state.py" \
    --run-dir "$GENERATION_RUN_DIR" \
    --run-id "$GENERATION_RUN_ID" \
    --prompt-file "$GENERATION_RUN_DIR/article-daily-prompt.txt" \
    --ledger "$STATE_DIR/articles.jsonl" \
    recover-orphan --minimum-age-seconds \
    "${ARTICLE_GENERATION_ORPHAN_AGE_SECONDS:-60}" >>"$LOG" 2>&1 || true
fi
START_DECISION="$(python3 "$START_CONTROL" \
  --state-dir "$STATE_DIR" --local-date "$LOCAL_DATE" 2>>"$LOG" || \
  printf '%s' '{"action":"block-incomplete","reason":"start-control-error"}')"
START_ACTION="$(printf '%s' "$START_DECISION" | jq -r '.action // empty')"
START_RUN_ID="$(printf '%s' "$START_DECISION" | jq -r '.run_id // empty')"
if [ "$PRIORITY_PUBLICATION_READY" -ne 1 ] \
  && [ "$START_ACTION" = "new-quality-replacement" ]; then
  [ -n "$START_RUN_ID" ] || {
    echo "article-resume: quality replacement run id missing" >>"$LOG"
    exit 1
  }
  echo "article-resume: handing terminal quality slot to replacement run=$START_RUN_ID" >>"$LOG"
  export ARTICLE_EXPECTED_NEW_RUN_ID="$START_RUN_ID"
  trap - EXIT
  release_publication_lock || exit 1
  exec bash "$ARTICLE_ROOT/article-daily.sh"
fi
if [ "$PRIORITY_PUBLICATION_READY" -ne 1 ] \
  && [ "$START_ACTION" = "resume-generation" ]; then
  GENERATION_RUN_ID="$START_RUN_ID"
  PROVIDER="${ARTICLE_PROVIDER:-auto}"
  HEALTH_FILE="${ARTICLE_PROVIDER_HEALTH:-$STATE_DIR/provider-health.json}"
  PROVIDER_READY=0
  for CANDIDATE in $([ "$PROVIDER" = "auto" ] && printf 'codex claude' || printf '%s' "$PROVIDER"); do
    if python3 "$MODEL_SUPPORT" eligible --file "$HEALTH_FILE" \
      --provider "$CANDIDATE" --mode agent >/dev/null 2>&1; then
      PROVIDER_READY=1
      break
    fi
  done
  if [ "$PROVIDER_READY" -ne 1 ]; then
    echo "article-resume: prepublication generation remains in provider cooldown run=$GENERATION_RUN_ID" >>"$LOG"
    exit 0
  fi
  echo "article-resume: prepublication generation recovery run=$GENERATION_RUN_ID" >>"$LOG"
  export ARTICLE_EXPECTED_RUN_ID="$GENERATION_RUN_ID"
  trap - EXIT
  release_publication_lock || exit 1
  exec bash "$ARTICLE_ROOT/article-daily.sh"
fi

# An unavailable destination is otherwise excluded from pending work forever.
# Re-arm only failure classes whose original blocker can be re-proved as fixed:
# note's locked Python runtime, and Substack's authenticated draft render.
python3 "$ARTICLE_ROOT/scripts/recover-known-unavailable.py" \
  --state-root "$STATE_DIR" >>"$LOG" 2>&1 || \
  echo "article-resume: known unavailable recovery failed closed" >>"$LOG"

# Unknown publisher failures are observations for the Agent repair loop, not a
# terminal exclusion from pending work. The bridge is read-only over run
# receipts and durably deduplicates destination incidents before planning.
python3 "$ARTICLE_ROOT/scripts/writer_unavailable_incident_bridge.py" \
  --state-root "$STATE_DIR" --observed-at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  >>"$LOG" 2>&1 || \
  echo "article-resume: unavailable incident bridge failed closed" >>"$LOG"

# SSOT Order 4. Claim at most one durable incident per tick and route it: a
# known failure class to its deterministic runbook decision, an unknown one to
# a Terra investigation. Blocking revenue-set work outranks non-blocking
# distribution work, the claim carries a lease so two ticks cannot work the
# same incident, and no runbook command or publisher effect runs here.
#
# This runs inside the held publication lock, so it must never buy lock time
# with a model call: PRIORITY_PUBLICATION_READY is this worker's own backlog
# signal, and while it is 1 the dispatcher completes the deterministic route
# and its receipts but defers Terra to a tick that owes no publication work.
# Order 4 repairs nothing this tick, so deferring the model costs no recovery.
# Fail closed: repair routing must never delay or break the publication work
# below.
python3 "$ARTICLE_ROOT/scripts/writer_repair_dispatch.py" \
  --state-root "$STATE_DIR" \
  --scripts "$ARTICLE_ROOT/scripts" \
  --registry "$ARTICLE_ROOT/config/repair-runbooks.json" \
  --model-runner "$MODEL_RUNNER" \
  --publication-backlog "$PRIORITY_PUBLICATION_READY" \
  --observed-at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  >>"$LOG" 2>&1 || \
  echo "article-resume: repair routing failed closed" >>"$LOG"

PLAN_ARGS=(--state-root "$STATE_DIR")
[ -n "${ARTICLE_NOW:-}" ] && PLAN_ARGS+=(--now "$ARTICLE_NOW")
PLAN="$(python3 "$PLANNER" "${PLAN_ARGS[@]}" 2>>"$LOG")" || {
  echo "article-resume: planner failed closed" >>"$LOG"
  exit 1
}
[ "$(printf '%s' "$PLAN" | jq -r '.status')" = "READY" ] || {
  echo "article-resume: $(printf '%s' "$PLAN" | jq -c '.')" >>"$LOG"
  exit 0
}
INITIALIZATION_COUNT="$(printf '%s' "$PLAN" | jq '.initialization_pairs | length')"
ELIGIBLE_COUNT="$(printf '%s' "$PLAN" | jq '.eligible_pairs | length')"
FIRST_INITIALIZATION="$(printf '%s' "$PLAN" | jq -r '.initialization_pairs[0] // empty')"
if [ "$INITIALIZATION_COUNT" -gt 0 ] && [ "$ELIGIBLE_COUNT" -gt 0 ]; then
  echo "article-resume: planner mixed initialization and publication work" >>"$LOG"
  exit 1
fi

RUN_ID="$(printf '%s' "$PLAN" | jq -r '.run_id')"
RUN_DIR="$(printf '%s' "$PLAN" | jq -r '.run_dir')"
STATE_PATH="$(printf '%s' "$PLAN" | jq -r '.state_path')"
LEDGER_PATH="$(printf '%s' "$PLAN" | jq -r '.ledger_path')"
case "$RUN_ID" in daily-????-??-??|????????-??????) ;; *) echo "article-resume: invalid run id" >>"$LOG"; exit 1 ;; esac
[ -d "$RUN_DIR" ] && [ -f "$STATE_PATH" ] || exit 1

notify_pending() {
  python3 "$ARTICLE_ROOT/scripts/article-completion-notify.py" \
    --state "$STATE_PATH" --ledger "$LEDGER_PATH" \
    --target "${TELEGRAM_TARGET_ID:-8547730585}" \
    --pending --reason "$1" >>"$LOG" 2>&1 || \
    echo "article-resume: pending Telegram report remains queued reason=$1" >>"$LOG"
}

PUBLICATION_CONTRACT="$(python3 "$ARTICLE_ROOT/scripts/publication_contract_resolver.py" \
  --state "$STATE_PATH" --ledger "$LEDGER_PATH" --run-id "$RUN_ID" 2>>"$LOG")" || {
  echo "article-resume: publication contract resolution failed closed run=$RUN_ID" >>"$LOG"
  exit 1
}
case "$PUBLICATION_CONTRACT" in
  legacy-exact8)
    DORMANT_ROUTING_INSTRUCTION="This is legacy exact8; legacy dormant destinations remain eligible and must route their persisted targets through the deterministic publisher."
    DORMANT_ELIGIBILITY_INSTRUCTION="Legacy dormant destinations remain eligible; do not synthesize active-six skip receipts."
    REQUIRED_INTENTS_INSTRUCTION="Require publication-guard.py plan to report all eight valid stable intents."
    INITIALIZATION_CONTRACT_INSTRUCTION="Legacy exact8 initialization must register x-article/en and x-post/ja; x-post/ja target-kind x-post-slot must use the planner's legacy x-post/ja slot owner and publication-guard.py registration/plan guards."
    DORMANT_RECEIPT_INSTRUCTION="Legacy exact8 has no dormant skip receipts; x-post/ja remains real pending publication work."
    COMPLETION_CONTRACT_INSTRUCTION="Do not select or claim a topic; research, write, revise, regenerate, restage, create a run, replace a target, change an artifact, or send a success receipt unless article-run-complete.py proves the persisted legacy-exact8 contract."
    RECOVERY_SCOPE_INSTRUCTION="If any identity, hash, safety, remote state, or slot is ambiguous outside the legacy-exact8 recovery_pairs contract above, stop without a public create action."
    REPAIR_SCOPE_INSTRUCTION="An eligible pair whose persisted status is repair-required is NEVER a create. Use only its fixed same-ID command: note/ja = python3 $ARTICLE_ROOT/scripts/note-publish/note_inplace_repair.py; devto/en = python3 $ARTICLE_ROOT/scripts/devto-publish/devto.py repair; substack/ja or substack/en = python3 $ARTICLE_ROOT/scripts/substack-publish/substack_inplace_repair.py --pair PAIR; x-article/ja = python3 $ARTICLE_ROOT/scripts/x-publish/x_inplace_repair.py --pair x-article/ja. For x-post/ja, a strong remote reconcile is sufficient because its media contract is empty. Refuse every repair-required pair not covered by this list."
    X_POST_COMMAND_INSTRUCTION="The canonical X Post command is python3 $ARTICLE_ROOT/scripts/x-post/publish.py go; it owns the durable pre-effect timeline fence and must not be replaced with an ad-hoc browser click."
    ;;
  active-four)
    DORMANT_ROUTING_INSTRUCTION="Current active-four: zenn-article/ja, devto/en, x-article/en, and x-post/ja receive explicit durable dormant-destination skip receipts and never receive publication intents."
    DORMANT_ELIGIBILITY_INSTRUCTION="Dormant zenn-article/ja, devto/en, x-article/en, x-post/ja are never eligible. Never publish, repair, or stage zenn-article/ja or devto/en."
    REQUIRED_INTENTS_INSTRUCTION="Require publication-guard.py plan to report all four active valid stable intents plus four durable dormant skip receipts."
    INITIALIZATION_CONTRACT_INSTRUCTION="Active-four initialization must register every missing_dormant_skip_pairs entry through publication-guard.py register-dormant-skip before or alongside the four active target registrations; register only note/ja, substack/ja, substack/en, and x-article/ja, and do not publish any pair in this initialization tick."
    DORMANT_RECEIPT_INSTRUCTION="The four dormant skip receipts have slo=not-applicable, never breach an SLO, and never enter pending, recovery, or publication work."
    COMPLETION_CONTRACT_INSTRUCTION="Do not select or claim a topic; research, write, revise, regenerate, restage, create a run, replace a target, change an artifact, or send a success receipt unless article-run-complete.py proves the persisted active-four contract."
    RECOVERY_SCOPE_INSTRUCTION="If any identity, hash, safety, remote state, or slot is ambiguous outside the active-four recovery_pairs contract above, stop without a public create action."
    REPAIR_SCOPE_INSTRUCTION="An eligible pair whose persisted status is repair-required is NEVER a create. Use only its fixed same-ID command: note/ja = python3 $ARTICLE_ROOT/scripts/note-publish/note_inplace_repair.py; substack/ja or substack/en = python3 $ARTICLE_ROOT/scripts/substack-publish/substack_inplace_repair.py --pair PAIR; x-article/ja = python3 $ARTICLE_ROOT/scripts/x-publish/x_inplace_repair.py --pair x-article/ja. Refuse every repair-required zenn-article/ja or devto/en and every pair not covered by this list."
    X_POST_COMMAND_INSTRUCTION="Never publish, repair, or stage dormant x-post/ja; its explicit skip receipt is not an eligible command."
    ;;
  *)
    echo "article-resume: unsupported publication contract=$PUBLICATION_CONTRACT" >>"$LOG"
    exit 1
    ;;
esac

# A current active-four run must persist every missing dormant skip receipt before
# any active target initialization. This is a publication-free state transition.
MISSING_DORMANT_SKIP_PAIRS="$(printf '%s' "$PLAN" | jq -r '.missing_dormant_skip_pairs[]?')"
if [ "$PUBLICATION_CONTRACT" = "active-four" ] && [ -n "$MISSING_DORMANT_SKIP_PAIRS" ]; then
  export ARTICLE_RUN_DIR="$RUN_DIR"
  export ARTICLE_PUBLICATION_STATE="$STATE_PATH"
  export ARTICLE_LEDGER="$LEDGER_PATH"
  export ARTICLE_AUTOPUBLISH=1
  while IFS= read -r DORMANT_PAIR; do
    [ -n "$DORMANT_PAIR" ] || continue
    python3 "$ARTICLE_ROOT/scripts/publication-guard.py" \
      register-dormant-skip --pair "$DORMANT_PAIR" \
      --reason "dormant-destination" >>"$LOG" 2>&1 || {
        echo "article-resume: dormant skip registration failed pair=$DORMANT_PAIR" >>"$LOG"
        exit 1
      }
  done <<< "$MISSING_DORMANT_SKIP_PAIRS"
fi

# The self-owned paid publication is an adjunct to active-four. Delivery/readback
# runs under its own same-run lock in the background: a dirty landing checkout,
# deploy propagation, or one failed readback must never delay the four active pairs.
if [ -n "${ARTICLE_SELF_OWNED_LANDING_ROOT:-}" ] \
  && [ -n "${ARTICLE_SELF_OWNED_REMOTE:-}" ] \
  && [ -n "${ARTICLE_SELF_OWNED_BRANCH:-}" ]; then
  (
    SELF_OWNED_LOCK="$RUN_DIR/gates/self-owned-worker.lock"
    if ! mkdir "$SELF_OWNED_LOCK" 2>/dev/null; then
      exit 0
    fi
    trap 'rmdir "$SELF_OWNED_LOCK" 2>/dev/null || true' EXIT
    python3 "$ARTICLE_ROOT/scripts/self_owned_article.py" resume \
      --publication-state "$STATE_PATH" \
      --ledger "$LEDGER_PATH" \
      --landing-root "$ARTICLE_SELF_OWNED_LANDING_ROOT" \
      --remote "$ARTICLE_SELF_OWNED_REMOTE" \
      --branch "$ARTICLE_SELF_OWNED_BRANCH" \
      --base-url "${ARTICLE_SELF_OWNED_BASE_URL:-https://aniccaai.com}"
  ) >>"$LOG" 2>&1 </dev/null &
fi

# A recognized note ambiguity is a deterministic state transition, not a
# writing decision. Prove its authenticated same-key live-media shape and
# convert it to repair-required in one publication-free tick. The next tick
# runs only the protected in-place repair.
if [ "$(printf '%s' "$PLAN" | jq -r '.recovery_pairs[0] // empty')" = "note/ja" ] \
  && [ "$(jq -r '.pairs["note/ja"].status // empty' "$STATE_PATH")" = "ambiguous" ]; then
  export ARTICLE_RUN_DIR="$RUN_DIR"
  export ARTICLE_PUBLICATION_STATE="$STATE_PATH"
  export ARTICLE_LEDGER="$LEDGER_PATH"
  export ARTICLE_AUTOPUBLISH=1
  export ARTICLE_PUBLISH_PAIR="note/ja"
  python3 "$ARTICLE_ROOT/scripts/publication-guard.py" \
    recover-ambiguous --pair "note/ja" >>"$LOG" 2>&1
  RC=$?
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=recover-note/ja" >>"$LOG"
  exit "$RC"
fi

# A missing managed target has no editorial decision left: STEP 5 already
# persisted its exact argv/env in the preflighted dispatch manifest. Execute
# supported deterministic rows once and require a durable target before
# exiting the publication-free initialization tick.
if [ "$INITIALIZATION_COUNT" -eq 1 ] \
  && [ "$ELIGIBLE_COUNT" -eq 0 ] \
  && { [ "$FIRST_INITIALIZATION" = "note/ja" ] \
    || { [ "$PUBLICATION_CONTRACT" = "legacy-exact8" ] \
      && [ "$FIRST_INITIALIZATION" = "devto/en" ]; }; }; then
  ARTICLE_MODEL_LOG="$LOG" \
    bash "$ARTICLE_ROOT/runtime/judge-broker.sh" "$RUN_DIR" &
  INITIALIZATION_BROKER_PID=$!
  trap 'kill "$INITIALIZATION_BROKER_PID" 2>/dev/null; release_publication_lock' EXIT
  python3 "$ARTICLE_ROOT/scripts/execute-initialization-pair.py" \
    --pair "$FIRST_INITIALIZATION" --run-dir "$RUN_DIR" --state "$STATE_PATH" \
    --ledger "$LEDGER_PATH" >>"$LOG" 2>&1
  RC=$?
  kill "$INITIALIZATION_BROKER_PID" 2>/dev/null || true
  wait "$INITIALIZATION_BROKER_PID" 2>/dev/null || true
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=initialize-$FIRST_INITIALIZATION" >>"$LOG"
  exit "$RC"
fi

# The first money-bearing note intent is a fully specified operation: immutable
# eyecatch, executable ¥500 policy, guarded publish, public API readback, and
# receipt reconciliation. Run that narrow contract directly instead of giving
# a general model the frozen run prompt (which may predate the current money
# policy) plus several unrelated eligible destinations.
if [ "$INITIALIZATION_COUNT" -eq 0 ] \
  && [ "$ELIGIBLE_COUNT" -gt 0 ] \
  && [ "$(printf '%s' "$PLAN" | jq -r '.eligible_pairs[0]')" = "note/ja" ]; then
  export ARTICLE_RUN_DIR="$RUN_DIR"
  export ARTICLE_PUBLICATION_STATE="$STATE_PATH"
  export ARTICLE_LEDGER="$LEDGER_PATH"
  export ARTICLE_AUTOPUBLISH=1
  export ARTICLE_PUBLISH_PAIR="note/ja"
  NOTE_STATUS="$(jq -r '.pairs["note/ja"].status // empty' "$STATE_PATH")"
  NOTE_CODE_ARGS=()
  if [ "$NOTE_STATUS" = "repair-required" ]; then
    NOTE_MCP_DIR="${NOTE_MCP_DIR:-$HOME/.openclaw/external/note-mcp}"
    bash "$ARTICLE_ROOT/scripts/ensure-note-mcp-runtime.sh" \
      "$NOTE_MCP_DIR" >>"$LOG" 2>&1 || {
      echo "article-resume: note-mcp runtime restore failed closed" >>"$LOG"
      exit 1
    }
    export NOTE_MCP_DIR
    export NOTE_MCP_SRC="$NOTE_MCP_DIR/src"
    NOTE_COMMAND=(
      "$NOTE_MCP_DIR/.venv/bin/python"
      "$ARTICLE_ROOT/scripts/note-publish/note_inplace_repair.py"
    )
    NOTE_CODE_ARGS=(
      --code-file "$ARTICLE_ROOT/scripts/note-publish/note_inplace_repair.py"
      --code-file "$ARTICLE_ROOT/scripts/ensure-note-mcp-runtime.sh"
    )
  elif [ "$NOTE_STATUS" = "intent" ]; then
    NOTE_COMMAND=(python3 "$ARTICLE_ROOT/scripts/publish-note-managed.py")
    NOTE_CODE_ARGS=(
      --code-file "$ARTICLE_ROOT/scripts/publish-note-managed.py"
      --code-file "$ARTICLE_ROOT/scripts/note-publish/set-eyecatch-draft.py"
      --code-file "$ARTICLE_ROOT/scripts/note-publish/set-eyecatch-api.py"
      --code-file "$ARTICLE_ROOT/scripts/note-publish/publish-paid.py"
      --code-file "$ARTICLE_ROOT/scripts/ensure-note-mcp-runtime.sh"
    )
  else
    echo "article-resume: note deterministic dispatch refused status=$NOTE_STATUS" >>"$LOG"
    exit 1
  fi
  python3 "$ARTICLE_ROOT/scripts/resume_failure_circuit.py" run \
    --circuit "$RUN_DIR/gates/resume-failure-circuit.json" \
    --state "$STATE_PATH" \
    "${NOTE_CODE_ARGS[@]}" \
    --pair "note/ja" \
    --threshold "${ARTICLE_RESUME_FAILURE_THRESHOLD:-2}" \
    --log "$LOG" \
    -- "${NOTE_COMMAND[@]}" >>"$LOG" 2>&1
  RC=$?
  python3 "$ARTICLE_ROOT/scripts/article-completion-notify.py" \
    --state "$STATE_PATH" --ledger "$LEDGER_PATH" \
    --target "${TELEGRAM_TARGET_ID:-8547730585}" >>"$LOG" 2>&1 || \
    echo "article-resume: $PUBLICATION_CONTRACT completion notification remains pending" >>"$LOG"
  notify_pending "Noteの公開と読み戻しが未完了です"
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=note/ja" >>"$LOG"
  exit "$RC"
fi

FIRST_ELIGIBLE="$(printf '%s' "$PLAN" | jq -r '.eligible_pairs[0] // empty')"
if [ "$INITIALIZATION_COUNT" -eq 0 ] \
  && [ "$ELIGIBLE_COUNT" -gt 0 ] \
  && { [ "$FIRST_ELIGIBLE" = "substack/ja" ] || [ "$FIRST_ELIGIBLE" = "substack/en" ]; }; then
  export ARTICLE_RUN_DIR="$RUN_DIR" ARTICLE_PUBLICATION_STATE="$STATE_PATH"
  export ARTICLE_LEDGER="$LEDGER_PATH" ARTICLE_AUTOPUBLISH=1
  export ARTICLE_PUBLISH_PAIR="$FIRST_ELIGIBLE"
  SUBSTACK_CODE_ARGS=(
    --code-file "$ARTICLE_ROOT/scripts/publish-substack-managed.py"
    --code-file "$ARTICLE_ROOT/scripts/substack-publish/substack_refresh_intent.py"
    --code-file "$ARTICLE_ROOT/scripts/substack-publish/substack_paid_payload.py"
    --code-file "$ARTICLE_ROOT/scripts/substack-publish/substack_inplace_repair.py"
    --code-file "$ARTICLE_ROOT/scripts/_shared/publish-substack-mermaid.sh"
    --code-file "$ARTICLE_ROOT/scripts/publication-guard.py"
    --code-file "$ARTICLE_ROOT/scripts/publication_remote.py"
    --code-file "$ARTICLE_ROOT/scripts/publication_resume.py"
    --code-file "$ARTICLE_ROOT/scripts/pii-gate.py"
    --code-file "$ARTICLE_ROOT/scripts/substack-publish/verify-preview.py"
  )
  SUBSTACK_COMMAND=(python3 "$ARTICLE_ROOT/scripts/publish-substack-managed.py")
  python3 "$ARTICLE_ROOT/scripts/resume_failure_circuit.py" run \
    --circuit "$RUN_DIR/gates/resume-failure-circuit.json" \
    --state "$STATE_PATH" \
    "${SUBSTACK_CODE_ARGS[@]}" \
    --pair "$FIRST_ELIGIBLE" \
    --threshold "${ARTICLE_RESUME_FAILURE_THRESHOLD:-2}" \
    --log "$LOG" \
    -- "${SUBSTACK_COMMAND[@]}" >>"$LOG" 2>&1
  RC=$?
  python3 "$ARTICLE_ROOT/scripts/article-completion-notify.py" \
    --state "$STATE_PATH" --ledger "$LEDGER_PATH" \
    --target "${TELEGRAM_TARGET_ID:-8547730585}" >>"$LOG" 2>&1 || \
    echo "article-resume: $PUBLICATION_CONTRACT completion notification remains pending" >>"$LOG"
  notify_pending "Substackの公開と読み戻しが未完了です"
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=$FIRST_ELIGIBLE" >>"$LOG"
  exit "$RC"
fi

# X Article publication and same-ID repair are deterministic and fully
# guarded. Do not boot a general-purpose model merely to invoke the fixed
# publisher, especially during EN's narrow platform-clock window.
if [ "$INITIALIZATION_COUNT" -eq 0 ] \
  && [ "$ELIGIBLE_COUNT" -gt 0 ] \
  && { [ "$FIRST_ELIGIBLE" = "x-article/ja" ] \
    || { [ "$PUBLICATION_CONTRACT" = "legacy-exact8" ] \
      && [ "$FIRST_ELIGIBLE" = "x-article/en" ]; }; }; then
  export ARTICLE_RUN_DIR="$RUN_DIR"
  export ARTICLE_PUBLICATION_STATE="$STATE_PATH"
  export ARTICLE_LEDGER="$LEDGER_PATH"
  export ARTICLE_AUTOPUBLISH=1
  export ARTICLE_PUBLISH_PAIR="$FIRST_ELIGIBLE"
  python3 "$ARTICLE_ROOT/scripts/x-publish/x_inplace_repair.py" \
    --pair "$FIRST_ELIGIBLE" >>"$LOG" 2>&1
  RC=$?
  python3 "$ARTICLE_ROOT/scripts/article-completion-notify.py" \
    --state "$STATE_PATH" --ledger "$LEDGER_PATH" \
    --target "${TELEGRAM_TARGET_ID:-8547730585}" >>"$LOG" 2>&1 || \
    echo "article-resume: $PUBLICATION_CONTRACT completion notification remains pending" >>"$LOG"
  notify_pending "X記事の公開と読み戻しが未完了です"
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=$FIRST_ELIGIBLE" >>"$LOG"
  exit "$RC"
fi

# Dev.to already has one authenticated numeric draft ID at this boundary.
# Publishing that exact ID is a fixed guarded API operation, so a general
# model adds latency and another failure surface without making a decision.
if [ "$INITIALIZATION_COUNT" -eq 0 ] \
  && [ "$ELIGIBLE_COUNT" -eq 1 ] \
  && [ "$PUBLICATION_CONTRACT" = "legacy-exact8" ] \
  && [ "$FIRST_ELIGIBLE" = "devto/en" ]; then
  export ARTICLE_RUN_DIR="$RUN_DIR"
  export ARTICLE_PUBLICATION_STATE="$STATE_PATH"
  export ARTICLE_LEDGER="$LEDGER_PATH"
  export ARTICLE_AUTOPUBLISH=1
  export ARTICLE_PUBLISH_PAIR="devto/en"
  DEVTO_TARGET="$(jq -r '.pairs["devto/en"].target // empty' "$STATE_PATH")"
  case "$DEVTO_TARGET" in
    ''|*[!0-9]*) echo "article-resume: invalid Dev.to target" >>"$LOG"; exit 1 ;;
  esac
  python3 "$ARTICLE_ROOT/scripts/devto-publish/devto.py" go "$DEVTO_TARGET" >>"$LOG" 2>&1
  RC=$?
  python3 "$ARTICLE_ROOT/scripts/article-completion-notify.py" \
    --state "$STATE_PATH" --ledger "$LEDGER_PATH" \
    --target "${TELEGRAM_TARGET_ID:-8547730585}" >>"$LOG" 2>&1 || \
    echo "article-resume: $PUBLICATION_CONTRACT completion notification remains pending" >>"$LOG"
  notify_pending "Dev.toの公開と読み戻しが未完了です"
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=devto/en" >>"$LOG"
  exit "$RC"
fi

# X Post also has a single canonical, fully guarded command. Once the planner
# owns today's durable slot, a general model adds latency but no decision.
if [ "$INITIALIZATION_COUNT" -eq 0 ] \
  && [ "$ELIGIBLE_COUNT" -eq 1 ] \
  && [ "$PUBLICATION_CONTRACT" = "legacy-exact8" ] \
  && [ "$(printf '%s' "$PLAN" | jq -r '.eligible_pairs[0]')" = "x-post/ja" ]; then
  export ARTICLE_RUN_DIR="$RUN_DIR"
  export ARTICLE_PUBLICATION_STATE="$STATE_PATH"
  export ARTICLE_LEDGER="$LEDGER_PATH"
  export ARTICLE_AUTOPUBLISH=1
  export ARTICLE_PUBLISH_PAIR="x-post/ja"
  python3 "$ARTICLE_ROOT/scripts/x-post/publish.py" go >>"$LOG" 2>&1
  RC=$?
  python3 "$ARTICLE_ROOT/scripts/article-completion-notify.py" \
    --state "$STATE_PATH" --ledger "$LEDGER_PATH" \
    --target "${TELEGRAM_TARGET_ID:-8547730585}" >>"$LOG" 2>&1 || \
    echo "article-resume: $PUBLICATION_CONTRACT completion notification remains pending" >>"$LOG"
  notify_pending "X短文の公開と読み戻しが未完了です"
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=x-post/ja" >>"$LOG"
  exit "$RC"
fi

PROMPT_FILE="$RUN_DIR/gates/pending-resume-$(date -u +%Y%m%dT%H%M%SZ).txt"
printf '%s\n' "RESUME ONLY immutable $PUBLICATION_CONTRACT publication run $RUN_ID.
Export ARTICLE_RUN_DIR=$RUN_DIR, ARTICLE_PUBLICATION_STATE=$STATE_PATH, ARTICLE_LEDGER=$LEDGER_PATH, and ARTICLE_AUTOPUBLISH=1 for every managed publisher.
Read $STATE_PATH, the original $RUN_DIR/article-daily-prompt.txt publication steps, and saved artifacts in $RUN_DIR.
This worker plan is authoritative: $PLAN
When initialization_pairs is non-empty, this is a crash-truncated target-registration recovery tick. Existing pair targets are immutable: never restage, replace, update, or re-register them. For each initialization pair only, first reconcile whether the failed foreground already left a same-run draft/target whose content matches the immutable state artifact; reuse that exact target when proven. Otherwise run only the original managed STEP 5 staging path for that missing pair and register its returned stable identity through publication-guard.py register-intent. $DORMANT_ROUTING_INSTRUCTION $INITIALIZATION_CONTRACT_INSTRUCTION $REQUIRED_INTENTS_INSTRUCTION; do not publish any pair in this initialization tick. Exit and let the next 300-second tick own publication.
Execute ONLY eligible_pairs, in listed order. Reconcile the persisted stable target remotely before every create/publish action. Already-live pairs, waiting pairs, and pairs absent from eligible_pairs are forbidden.
An eligible x-article/ja listed in recovery_pairs is a bounded same-ID recovery, not create permission: run only x_inplace_repair.py, whose first guard call must convert authenticated not-live evidence back to intent or an exactly identified live media/final-CTA gap to repair-required. Any other ambiguity remains frozen.
${REPAIR_SCOPE_INSTRUCTION}
For x-article/ja, when eligible, update and publish only its persisted saved edit URL with python3 $ARTICLE_ROOT/scripts/x-publish/x_inplace_repair.py --pair x-article/ja; never open the X new-article composer. $DORMANT_ELIGIBILITY_INSTRUCTION
For substack pairs, every public image must be the byte-identical immutable run media (headline-image.png and each body asset uploaded unchanged); never render Mermaid or substitute any alternative figure — a rendered or re-encoded diagram fails the receipt and strands the pair.
$COMPLETION_CONTRACT_INSTRUCTION $DORMANT_RECEIPT_INSTRUCTION
$X_POST_COMMAND_INSTRUCTION
$RECOVERY_SCOPE_INSTRUCTION
Do not send Telegram messages from the model. The deterministic wrapper sends the only progress or completion report after it reads the persisted state. State what was attempted and what remains unconfirmed in the run log; never add a harness prefix or claim a public URL without publisher-native readback." >"$PROMPT_FILE"

# Judge broker: serve nested judge/vision requests from the sandboxed agent
# through the same model boundary, outside the sandbox.
ARTICLE_MODEL_LOG="$LOG" bash "$ARTICLE_ROOT/runtime/judge-broker.sh" "$RUN_DIR" &
JUDGE_BROKER_PID=$!
trap 'kill "$JUDGE_BROKER_PID" 2>/dev/null; release_publication_lock' EXIT

ARTICLE_RUN_ID="$RUN_ID" ARTICLE_MODEL_LOG="$LOG" \
  "$MODEL_RUNNER" agent --prompt-file "$PROMPT_FILE"
RC=$?
kill "$JUDGE_BROKER_PID" 2>/dev/null || true
python3 "$ARTICLE_ROOT/scripts/article-completion-notify.py" \
  --state "$STATE_PATH" --ledger "$LEDGER_PATH" \
  --target "${TELEGRAM_TARGET_ID:-8547730585}" >>"$LOG" 2>&1 || \
  echo "article-resume: $PUBLICATION_CONTRACT completion notification remains pending" >>"$LOG"
notify_pending "公開処理が未完了です"
echo "article-resume: run=$RUN_ID rc=$RC eligible=$(printf '%s' "$PLAN" | jq -c '.eligible_pairs')" >>"$LOG"
exit "$RC"
