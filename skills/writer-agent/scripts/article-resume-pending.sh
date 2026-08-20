#!/usr/bin/env bash
# Durable 300-second exact8 pending worker. It never creates a run or topic. A crash-truncated
# pre-live target set may initialize only its explicitly missing targets in a publication-free tick.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
# Load runtime credentials exactly like article-daily.sh so remote reconciles
# (e.g. publication_remote.devto) never fail closed on a missing API key.
set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a

ARTICLE_ROOT="${ARTICLE_ROOT:-$HOME/profitable-claude/skills/article-writer}"
STATE_DIR="${ARTICLE_STATE_DIR:-$ARTICLE_ROOT/state}"
LOG="${ARTICLE_RESUME_LOG:-$HOME/.openclaw/logs/article-resume.log}"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-$ARTICLE_ROOT/runtime/model-runner.sh}"
MODEL_SUPPORT="${ARTICLE_MODEL_SUPPORT:-$ARTICLE_ROOT/runtime/model-runner-support.py}"
QUALITY_REPAIR_CONTROL="${ARTICLE_QUALITY_REPAIR_CONTROL:-$ARTICLE_ROOT/scripts/quality_repair_control.py}"
QUALITY_FEEDBACK_CONTROL="${ARTICLE_QUALITY_FEEDBACK_CONTROL:-$ARTICLE_ROOT/scripts/quality_feedback_recovery.py}"
PLANNER="$ARTICLE_ROOT/scripts/article_pending.py"
LOCK_DIR="$STATE_DIR/.article-daily.lockdir"
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
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  # A SIGTERM between mkdir and the EXIT trap can leave an empty ownerless
  # directory forever. Recover only that exact shape, and only after proving
  # no *other* publication worker process is alive. Unexpected lock contents
  # remain fail-closed.
  OTHER_OWNER=""
  for OWNER_COMMAND in \
    "$ARTICLE_ROOT/article-daily.sh" \
    "$ARTICLE_ROOT/scripts/article-resume-pending.sh" \
    "$ARTICLE_ROOT/scripts/zenn-deferred-worker.py"; do
    while IFS= read -r OWNER_PID; do
      if [ -n "$OWNER_PID" ] && [ "$OWNER_PID" != "$$" ]; then
        OTHER_OWNER="$OWNER_PID"
        break 2
      fi
    done < <(pgrep -f "$OWNER_COMMAND" 2>/dev/null || true)
  done
  if [ -z "$OTHER_OWNER" ] \
    && [ -z "$(find "$LOCK_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ] \
    && rmdir "$LOCK_DIR" 2>/dev/null \
    && mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "article-resume: recovered ownerless publication lock" >>"$LOG"
  else
    echo "article-resume: shared publication lock is held" >>"$LOG"
    exit 0
  fi
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

# The same 300-second reconciler owns both sides of the publication boundary.
# A safe interrupted generation has no public side effect, so hand the exact
# saved run/prompt back to the daily wrapper; that wrapper revalidates the
# immutable boundary and invokes it once. Never create a run from this worker.
START_CONTROL="${ARTICLE_START_CONTROL:-$ARTICLE_ROOT/scripts/article_daily_start_control.py}"
LOCAL_DATE="${ARTICLE_LOCAL_DATE:-$(TZ=Asia/Tokyo date +%F)}"
PRE_START_DECISION="$(python3 "$START_CONTROL" \
  --state-dir "$STATE_DIR" --local-date "$LOCAL_DATE" 2>>"$LOG" || \
  printf '%s' '{"action":"block-incomplete","reason":"start-control-error"}')"
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
if [ "$(printf '%s' "$QUALITY_FEEDBACK_PLAN" | jq -r '.status // empty')" = "READY" ]; then
  QUALITY_FEEDBACK_REASON="$(printf '%s' "$QUALITY_FEEDBACK_PLAN" | jq -r '.reason // empty')"
  if [ "$QUALITY_FEEDBACK_REASON" = "terminal-quality-feedback" ]; then
    QUALITY_FEEDBACK_READY="$(python3 "$QUALITY_FEEDBACK_CONTROL" begin \
      --run-dir "$GENERATION_RUN_DIR" --ledger "$QUALITY_LEDGER" 2>>"$LOG")" || {
      echo "article-resume: bounded quality feedback begin failed closed" >>"$LOG"
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
if [ "$(printf '%s' "$QUALITY_PLAN" | jq -r '.status // empty')" = "READY" ]; then
  QUALITY_REASON="$(printf '%s' "$QUALITY_PLAN" | jq -r '.reason // empty')"
  if [ "$QUALITY_REASON" = "legacy-stale-quality-block" ] \
    || [ "$QUALITY_REASON" = "tracked-bookmark-source-defect" ]; then
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
if [ "$START_ACTION" = "new-quality-replacement" ]; then
  [ -n "$START_RUN_ID" ] || {
    echo "article-resume: quality replacement run id missing" >>"$LOG"
    exit 1
  }
  echo "article-resume: handing terminal quality slot to replacement run=$START_RUN_ID" >>"$LOG"
  export ARTICLE_EXPECTED_NEW_RUN_ID="$START_RUN_ID"
  trap - EXIT
  rmdir "$LOCK_DIR" 2>/dev/null || exit 1
  exec bash "$ARTICLE_ROOT/article-daily.sh"
fi
if [ "$START_ACTION" = "resume-generation" ]; then
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
  rmdir "$LOCK_DIR" 2>/dev/null || exit 1
  exec bash "$ARTICLE_ROOT/article-daily.sh"
fi

# An unavailable destination is otherwise excluded from pending work forever.
# Re-arm only failure classes whose original blocker can be re-proved as fixed:
# note's locked Python runtime, and Substack's authenticated draft render.
python3 "$ARTICLE_ROOT/scripts/recover-known-unavailable.py" \
  --state-root "$STATE_DIR" --run-id "daily-$LOCAL_DATE" >>"$LOG" 2>&1 || \
  echo "article-resume: known unavailable recovery failed closed" >>"$LOG"

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
  && { [ "$FIRST_INITIALIZATION" = "note/ja" ] || [ "$FIRST_INITIALIZATION" = "devto/en" ]; }; then
  ARTICLE_MODEL_LOG="$LOG" \
    bash "$ARTICLE_ROOT/runtime/judge-broker.sh" "$RUN_DIR" &
  INITIALIZATION_BROKER_PID=$!
  trap 'kill "$INITIALIZATION_BROKER_PID" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null' EXIT
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
    echo "article-resume: exact8 completion notification remains pending" >>"$LOG"
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
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=$FIRST_ELIGIBLE" >>"$LOG"
  exit "$RC"
fi

# X Article publication and same-ID repair are deterministic and fully
# guarded. Do not boot a general-purpose model merely to invoke the fixed
# publisher, especially during EN's narrow platform-clock window.
if [ "$INITIALIZATION_COUNT" -eq 0 ] \
  && [ "$ELIGIBLE_COUNT" -eq 1 ] \
  && { [ "$FIRST_ELIGIBLE" = "x-article/ja" ] || [ "$FIRST_ELIGIBLE" = "x-article/en" ]; }; then
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
    echo "article-resume: exact8 completion notification remains pending" >>"$LOG"
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=$FIRST_ELIGIBLE" >>"$LOG"
  exit "$RC"
fi

# Dev.to already has one authenticated numeric draft ID at this boundary.
# Publishing that exact ID is a fixed guarded API operation, so a general
# model adds latency and another failure surface without making a decision.
if [ "$INITIALIZATION_COUNT" -eq 0 ] \
  && [ "$ELIGIBLE_COUNT" -eq 1 ] \
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
    echo "article-resume: exact8 completion notification remains pending" >>"$LOG"
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=devto/en" >>"$LOG"
  exit "$RC"
fi

# X Post also has a single canonical, fully guarded command. Once the planner
# owns today's durable slot, a general model adds latency but no decision.
if [ "$INITIALIZATION_COUNT" -eq 0 ] \
  && [ "$ELIGIBLE_COUNT" -eq 1 ] \
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
    echo "article-resume: exact8 completion notification remains pending" >>"$LOG"
  echo "article-resume: run=$RUN_ID rc=$RC deterministic=x-post/ja" >>"$LOG"
  exit "$RC"
fi

PROMPT_FILE="$RUN_DIR/gates/pending-resume-$(date -u +%Y%m%dT%H%M%SZ).txt"
printf '%s\n' "RESUME ONLY immutable exact8 publication run $RUN_ID.
Export ARTICLE_RUN_DIR=$RUN_DIR, ARTICLE_PUBLICATION_STATE=$STATE_PATH, ARTICLE_LEDGER=$LEDGER_PATH, and ARTICLE_AUTOPUBLISH=1 for every managed publisher.
Read $STATE_PATH, the original $RUN_DIR/article-daily-prompt.txt publication steps, and saved artifacts in $RUN_DIR.
This worker plan is authoritative: $PLAN
When initialization_pairs is non-empty, this is a crash-truncated target-registration recovery tick. Existing pair targets are immutable: never restage, replace, update, or re-register them. For each initialization pair only, first reconcile whether the failed foreground already left a same-run draft/target whose content matches the immutable state artifact; reuse that exact target when proven. Otherwise run only the original managed STEP 5 staging path for that missing pair and register its returned stable identity through publication-guard.py register-intent. For x-post/ja, register x-post-slot=$RUN_ID without creating a public post. Require publication-guard.py plan to report all eight valid stable intents, then do not publish any pair in this initialization tick. Exit and let the next 300-second tick own publication.
Execute ONLY eligible_pairs, in listed order. Reconcile the persisted stable target remotely before every create/publish action. Already-live pairs, waiting pairs, and pairs absent from eligible_pairs are forbidden.
An eligible x-article/ja listed in recovery_pairs is a bounded same-ID recovery, not create permission: run only x_inplace_repair.py, whose first guard call must convert authenticated not-live evidence back to intent or an exactly identified live media/final-CTA gap to repair-required. Any other ambiguity remains frozen.
An eligible pair whose persisted status is repair-required is NEVER a create. Use only its fixed same-ID command: note/ja = python3 $ARTICLE_ROOT/scripts/note-publish/note_inplace_repair.py; devto/en = python3 $ARTICLE_ROOT/scripts/devto-publish/devto.py repair; substack/ja or substack/en = python3 $ARTICLE_ROOT/scripts/substack-publish/substack_inplace_repair.py --pair PAIR; x-article/ja = python3 $ARTICLE_ROOT/scripts/x-publish/x_inplace_repair.py --pair x-article/ja. For x-post/ja, a strong remote reconcile is sufficient because its media contract is empty. Refuse every repair-required pair not covered by this list.
For x-article/ja or x-article/en, when eligible, update and publish only its persisted saved edit URL with python3 $ARTICLE_ROOT/scripts/x-publish/x_inplace_repair.py --pair PAIR; never open the X new-article composer.
For substack pairs, every public image must be the byte-identical immutable run media (headline-image.png and each body asset uploaded unchanged); never render Mermaid or substitute any alternative figure — a rendered or re-encoded diagram fails the receipt and strands the pair.
Do not select or claim a topic; research, write, revise, regenerate, restage, create a run, replace a target, change an artifact, or send a success receipt unless article-run-complete.py proves exact8.
For x-article/en, the planner already enforced the remote Japanese published_at + six hours and no deadline. For x-post/ja, use only the assigned JST slot, persist the returned status ID, verify timeline visibility and emoji integrity, then record live evidence.
The canonical X Post command is python3 $ARTICLE_ROOT/scripts/x-post/publish.py go; it owns the durable pre-effect timeline fence and must not be replaced with an ad-hoc browser click.
If any identity, hash, safety, remote state, or slot is ambiguous outside the exact recovery_pairs contract above, stop without a public create action.
When reporting to Telegram, write one neutral natural-language Japanese message. Do not add a harness prefix such as Codex::: or Claude:::, and do not expose internal enum labels as the main sentence. State what was attempted, what was externally confirmed, what remains unconfirmed, and the next automatic action. Include a public URL only when a publisher-native readback proves it is live." >"$PROMPT_FILE"

# Judge broker: serve nested judge/vision requests from the sandboxed agent
# through the same model boundary, outside the sandbox.
ARTICLE_MODEL_LOG="$LOG" bash "$ARTICLE_ROOT/runtime/judge-broker.sh" "$RUN_DIR" &
JUDGE_BROKER_PID=$!
trap 'kill "$JUDGE_BROKER_PID" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null' EXIT

ARTICLE_RUN_ID="$RUN_ID" ARTICLE_MODEL_LOG="$LOG" \
  "$MODEL_RUNNER" agent --prompt-file "$PROMPT_FILE"
RC=$?
kill "$JUDGE_BROKER_PID" 2>/dev/null || true
python3 "$ARTICLE_ROOT/scripts/article-completion-notify.py" \
  --state "$STATE_PATH" --ledger "$LEDGER_PATH" \
  --target "${TELEGRAM_TARGET_ID:-8547730585}" >>"$LOG" 2>&1 || \
  echo "article-resume: exact8 completion notification remains pending" >>"$LOG"
echo "article-resume: run=$RUN_ID rc=$RC eligible=$(printf '%s' "$PLAN" | jq -c '.eligible_pairs')" >>"$LOG"
exit "$RC"
