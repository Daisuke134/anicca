#!/usr/bin/env bash
# One model process boundary for AI Entity Article Writer.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPPORT="$SCRIPT_DIR/model-runner-support.py"
MODE="${1:-}"
[ "$#" -gt 0 ] && shift

PROMPT_FILE=""
IMAGE_FILE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --prompt-file)
      [ "$#" -ge 2 ] || { echo "model-runner: --prompt-file requires a value" >&2; exit 64; }
      PROMPT_FILE="$2"
      shift 2
      ;;
    --image)
      [ "$#" -ge 2 ] || { echo "model-runner: --image requires a value" >&2; exit 64; }
      IMAGE_FILE="$2"
      shift 2
      ;;
    *)
      echo "model-runner: unknown argument: $1" >&2
      exit 64
      ;;
  esac
done

case "$MODE" in
  agent|judge|vision) ;;
  *) echo "model-runner: mode must be agent, judge, or vision" >&2; exit 64 ;;
esac
PROMPT_STDIN_FILE=""
if [ "$PROMPT_FILE" = "-" ]; then
  PROMPT_STDIN_FILE="$(mktemp "${TMPDIR:-/tmp}/article-model-prompt.XXXXXX")"
  chmod 600 "$PROMPT_STDIN_FILE"
  cat >"$PROMPT_STDIN_FILE"
  PROMPT_FILE="$PROMPT_STDIN_FILE"
  trap 'rm -f -- "$PROMPT_STDIN_FILE"' EXIT
fi
[ -f "$PROMPT_FILE" ] || { echo "model-runner: prompt file is missing" >&2; exit 64; }
if [ "$MODE" = "vision" ] && [ ! -f "$IMAGE_FILE" ]; then
  echo "model-runner: vision mode requires an existing --image" >&2
  exit 64
fi

# Judge broker client: a nested judge/vision call inside the bounded agent
# sandbox cannot start another provider process (codex app-server init is
# denied). It hands the prompt to the unsandboxed wrapper broker through the
# run-scoped state tree and waits for the response; timeout is a retryable
# provider failure, never a fabricated verdict.
# Routing triggers on EITHER the env marker OR a live broker heartbeat: an
# agent clearing ARTICLE_NESTED_SANDBOX (observed 2026-07-25) cannot bypass
# the broker while one is serving this run. The broker's own server-side
# invocation sets ARTICLE_JUDGE_BROKER_SERVER=1 and is never re-routed.
BROKER_HEARTBEAT_LIVE=0
DISCOVERED_BROKER_DIR=""
BROKER_FROM_REGISTRY=0
if [ "${ARTICLE_JUDGE_BROKER_SERVER:-}" != "1" ]; then
  REGISTRY_STATE_ROOT="${ARTICLE_MODEL_STATE_ROOT:-$HOME/profitable-claude/skills/article-writer/state}"
  if [ -n "${ARTICLE_RUN_DIR:-}" ]; then
    DISCOVERED_BROKER_DIR="${ARTICLE_RUN_DIR}/gates/judge-broker"
  else
    # Env-independent fallback: the broker registers itself at a fixed
    # state-root path, so routing survives agent subshells that drop env.
    if [ -f "$REGISTRY_STATE_ROOT/.judge-broker-active" ]; then
      DISCOVERED_BROKER_DIR="$(cat "$REGISTRY_STATE_ROOT/.judge-broker-active" 2>/dev/null)"
      BROKER_FROM_REGISTRY=1
    fi
  fi
  # A registry is runtime state owned by this exact state root. Ignore a
  # pointer outside state/runs (including a pytest temp broker): otherwise a
  # fresh external heartbeat can route production judges into a broker that
  # no production process serves, causing a 900-second blind wait.
  if [ "$BROKER_FROM_REGISTRY" = "1" ] && [ -n "$DISCOVERED_BROKER_DIR" ]; then
    BROKER_REGISTRY_VALID="$(python3 -c '
from pathlib import Path
import sys
root = (Path(sys.argv[1]) / "runs").resolve()
candidate = Path(sys.argv[2]).resolve()
valid = (
    candidate.name == "judge-broker"
    and candidate.parent.name == "gates"
    and candidate.is_relative_to(root)
)
print("1" if valid else "0")
' "$REGISTRY_STATE_ROOT" "$DISCOVERED_BROKER_DIR" 2>/dev/null || echo 0)"
    [ "$BROKER_REGISTRY_VALID" = "1" ] || DISCOVERED_BROKER_DIR=""
  fi
  if [ -n "$DISCOVERED_BROKER_DIR" ] && [ -f "$DISCOVERED_BROKER_DIR/heartbeat" ]; then
    HEARTBEAT_AGE=$(( $(date +%s) - $(stat -f %m "$DISCOVERED_BROKER_DIR/heartbeat" 2>/dev/null || echo 0) ))
    [ "$HEARTBEAT_AGE" -lt 180 ] && BROKER_HEARTBEAT_LIVE=1
  fi
  # A gate may intentionally isolate its attempt receipts under a child
  # ARTICLE_RUN_DIR. If that child has no serving broker, reuse the live
  # run-scoped broker registered by the parent instead of writing a request
  # into an unserved directory and waiting until timeout.
  if [ "$BROKER_HEARTBEAT_LIVE" != "1" ] \
    && [ -f "$REGISTRY_STATE_ROOT/.judge-broker-active" ]; then
    REGISTRY_BROKER_DIR="$(cat "$REGISTRY_STATE_ROOT/.judge-broker-active" 2>/dev/null)"
    REGISTRY_BROKER_VALID="$(python3 -c '
from pathlib import Path
import sys
root = (Path(sys.argv[1]) / "runs").resolve()
candidate = Path(sys.argv[2]).resolve()
valid = (
    candidate.name == "judge-broker"
    and candidate.parent.name == "gates"
    and candidate.is_relative_to(root)
)
print("1" if valid else "0")
' "$REGISTRY_STATE_ROOT" "$REGISTRY_BROKER_DIR" 2>/dev/null || echo 0)"
    if [ "$REGISTRY_BROKER_VALID" = "1" ] \
      && [ -f "$REGISTRY_BROKER_DIR/heartbeat" ]; then
      REGISTRY_HEARTBEAT_AGE=$(( $(date +%s) - $(stat -f %m "$REGISTRY_BROKER_DIR/heartbeat" 2>/dev/null || echo 0) ))
      if [ "$REGISTRY_HEARTBEAT_AGE" -lt 180 ]; then
        DISCOVERED_BROKER_DIR="$REGISTRY_BROKER_DIR"
        BROKER_FROM_REGISTRY=1
        BROKER_HEARTBEAT_LIVE=1
      fi
    fi
  fi
fi
if [ "$MODE" != "agent" ] && [ "${ARTICLE_JUDGE_BROKER_SERVER:-}" != "1" ] \
  && { [ "${ARTICLE_NESTED_SANDBOX:-}" = "1" ] || [ "$BROKER_HEARTBEAT_LIVE" = "1" ]; }; then
  if [ -z "$DISCOVERED_BROKER_DIR" ]; then
    echo "model-runner: nested sandbox judge found no broker (no ARTICLE_RUN_DIR and no active registry)" >&2
    exit 64
  fi
  BROKER_DIR="$DISCOVERED_BROKER_DIR"
  mkdir -p "$BROKER_DIR/requests" "$BROKER_DIR/responses"
  REQUEST_ID="$(date +%s%N).$$"
  cp "$PROMPT_FILE" "$BROKER_DIR/requests/$REQUEST_ID.prompt"
  REQUEST_TMP="$BROKER_DIR/requests/.tmp-$REQUEST_ID"
  printf '{"id":"%s","mode":"%s","image":"%s"}\n' \
    "$REQUEST_ID" "$MODE" "${IMAGE_FILE:-}" >"$REQUEST_TMP"
  mv "$REQUEST_TMP" "$BROKER_DIR/requests/$REQUEST_ID.json"
  BROKER_DEADLINE=$(( $(date +%s) + ${ARTICLE_JUDGE_BROKER_TIMEOUT:-900} ))
  while [ ! -f "$BROKER_DIR/responses/$REQUEST_ID.json" ]; do
    if [ "$(date +%s)" -ge "$BROKER_DEADLINE" ]; then
      echo "model-runner: judge broker timed out" >&2
      exit 75
    fi
    sleep 1
  done
  BROKER_RC="$(python3 -c 'import json,sys; print(int(json.load(open(sys.argv[1])).get("rc", 75)))' \
    "$BROKER_DIR/responses/$REQUEST_ID.json" 2>/dev/null || echo 75)"
  cat "$BROKER_DIR/responses/$REQUEST_ID.out" 2>/dev/null
  exit "$BROKER_RC"
fi

PROVIDER="${ARTICLE_PROVIDER:-auto}"
case "$PROVIDER" in
  auto|codex|claude) ;;
  *) echo "model-runner: ARTICLE_PROVIDER must be auto, codex, or claude" >&2; exit 64 ;;
esac

MODEL_ROOT="${ARTICLE_MODEL_ROOT:-$HOME/profitable-claude}"
MODEL_STATE_ROOT="${ARTICLE_MODEL_STATE_ROOT:-$MODEL_ROOT/skills/article-writer/state}"
RUN_ID="${ARTICLE_RUN_ID:-unknown}"
HEALTH_FILE="${ARTICLE_PROVIDER_HEALTH:-$MODEL_ROOT/skills/article-writer/state/provider-health.json}"
MODEL_LOG="${ARTICLE_MODEL_LOG:-$MODEL_ROOT/skills/article-writer/state/model-runner.log}"
COOLDOWN_SECONDS="${ARTICLE_PROVIDER_COOLDOWN_SECONDS:-21600}"
CODEX_BIN="${ARTICLE_CODEX_BIN:-$(command -v codex 2>/dev/null || true)}"
CLAUDE_BIN="${ARTICLE_CLAUDE_BIN:-$(command -v claude 2>/dev/null || true)}"
TEMP_FAILURE=75

mkdir -p "$(dirname "$MODEL_LOG")" "$(dirname "$HEALTH_FILE")" "$MODEL_STATE_ROOT"

log_event() {
  printf '%s run_id=%s provider=%s mode=%s status=%s%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$RUN_ID" "$1" "$MODE" "$2" "${3:+ $3}" \
    >>"$MODEL_LOG"
}

record_health() {
  python3 "$SUPPORT" record \
    --file "$HEALTH_FILE" \
    --provider "$1" \
    --mode "$MODE" \
    --status "$2" \
    --error-class "${3:-}" \
    --cooldown "$COOLDOWN_SECONDS" \
    --run-id "$RUN_ID"
}

is_eligible() {
  python3 "$SUPPORT" eligible \
    --file "$HEALTH_FILE" --provider "$1" --mode "$MODE" >/dev/null 2>&1
}

provider_binary() {
  if [ "$1" = "codex" ]; then
    printf '%s' "$CODEX_BIN"
  else
    printf '%s' "$CLAUDE_BIN"
  fi
}

invoke_provider() {
  local provider="$1"
  local binary prompt sandbox raw_out raw_err safe_out safe_err rc
  binary="$(provider_binary "$provider")"
  prompt="$(<"$PROMPT_FILE")"
  raw_out="$(mktemp "${TMPDIR:-/tmp}/article-model-out.XXXXXX")"
  raw_err="$(mktemp "${TMPDIR:-/tmp}/article-model-err.XXXXXX")"
  safe_out="$(mktemp "${TMPDIR:-/tmp}/article-model-safe-out.XXXXXX")"
  safe_err="$(mktemp "${TMPDIR:-/tmp}/article-model-safe-err.XXXXXX")"

  local -a command
  if [ "$provider" = "codex" ]; then
    # Dais 2026-07-25: the agent runs WITHOUT a sandbox on this local Mac.
    # The workspace-write cage caused every judge/publish failure class today
    # (nested app-server EPERM, blocked DNS, Telegram identity EPERM) and the
    # local machine is the trust boundary. Source discipline stays enforced
    # by the prompt's hard boundaries and the identity/conscience gates.
    sandbox="read-only"
    local working_root="$MODEL_ROOT"
    if [ "$MODE" = "agent" ]; then
      sandbox="danger-full-access"
      working_root="$MODEL_ROOT"
    fi
    command=(
      "$binary" exec --ephemeral
      --model gpt-5.6-luna
      -c "model_reasoning_effort=\"${ARTICLE_MODEL_REASONING_EFFORT:-xhigh}\""
      --sandbox "$sandbox"
      -C "$working_root"
    )
    if [ "$MODE" = "agent" ]; then
      command+=(--add-dir "$HOME")
    else
      command+=(--ignore-user-config --ignore-rules)
    fi
    [ "$MODE" = "vision" ] && command+=(--image "$IMAGE_FILE")
    command+=(-)
  elif [ "$MODE" = "agent" ]; then
    command=(
      "$binary" --model sonnet
      --dangerously-skip-permissions
      --add-dir "$HOME"
      --no-session-persistence
      -p "$prompt"
    )
  elif [ "$MODE" = "judge" ]; then
    command=(
      "$binary" --model sonnet
      --no-session-persistence
      --allowedTools ""
      -p "$prompt"
    )
  else
    prompt="${prompt}

Read and judge this existing image file: $IMAGE_FILE"
    command=(
      "$binary" --model sonnet
      --no-session-persistence
      --allowedTools "Read"
      --add-dir "$(dirname "$IMAGE_FILE")"
      -p "$prompt"
    )
  fi

  set +e
  if [ "$provider" = "codex" ]; then
    if [ "$MODE" = "agent" ]; then
      # Mark every process inside the bounded sandbox so nested judge/vision
      # calls route through the wrapper-side judge broker instead of trying
      # to start a provider process the sandbox will deny.
      ARTICLE_NESTED_SANDBOX=1 "${command[@]}" <"$PROMPT_FILE" >"$raw_out" 2>"$raw_err"
    else
      "${command[@]}" <"$PROMPT_FILE" >"$raw_out" 2>"$raw_err"
    fi
  else
    "${command[@]}" >"$raw_out" 2>"$raw_err"
  fi
  rc=$?
  set -e

  python3 "$SUPPORT" redact <"$raw_out" >"$safe_out"
  python3 "$SUPPORT" redact <"$raw_err" >"$safe_err"
  if [ -s "$safe_err" ]; then
    tee -a "$MODEL_LOG" <"$safe_err" >&2
  fi
  if [ -s "$safe_out" ]; then
    tee -a "$MODEL_LOG" <"$safe_out"
  fi

  INVOCATION_STDOUT="$raw_out"
  INVOCATION_STDERR="$raw_err"
  INVOCATION_SAFE_STDOUT="$safe_out"
  INVOCATION_SAFE_STDERR="$safe_err"
  INVOCATION_RC="$rc"
}

cleanup_invocation() {
  local path
  for path in \
    "${INVOCATION_STDOUT:-}" "${INVOCATION_STDERR:-}" \
    "${INVOCATION_SAFE_STDOUT:-}" "${INVOCATION_SAFE_STDERR:-}"; do
    [ -n "$path" ] && [ -f "$path" ] && rm -f -- "$path"
  done
  INVOCATION_STDOUT=""
  INVOCATION_STDERR=""
  INVOCATION_SAFE_STDOUT=""
  INVOCATION_SAFE_STDERR=""
}

if [ "$PROVIDER" = "auto" ]; then
  CANDIDATES=(codex claude)
else
  CANDIDATES=("$PROVIDER")
fi

for candidate in "${CANDIDATES[@]}"; do
  binary="$(provider_binary "$candidate")"
  if [ -z "$binary" ] || [ ! -x "$binary" ]; then
    log_event "$candidate" "unavailable" "reason=missing_cli"
    if [ "$PROVIDER" != "auto" ]; then
      echo "model-runner: provider=$candidate missing_cli" >&2
      exit 69
    fi
    continue
  fi

  if ! is_eligible "$candidate"; then
    log_event "$candidate" "skipped" "reason=cooldown"
    if [ "$PROVIDER" != "auto" ]; then
      echo "model-runner: provider=$candidate mode=$MODE is in cooldown" >&2
      exit "$TEMP_FAILURE"
    fi
    continue
  fi

  invoke_provider "$candidate"
  rc="$INVOCATION_RC"
  if [ "$rc" -eq 0 ]; then
    record_health "$candidate" success
    log_event "$candidate" success
    cleanup_invocation
    exit 0
  fi

  error_class="$(python3 "$SUPPORT" classify \
    --return-code "$rc" --stdout "$INVOCATION_STDOUT" --stderr "$INVOCATION_STDERR")"
  if [ "$error_class" = "fatal" ]; then
    record_health "$candidate" fatal "$error_class"
    log_event "$candidate" fatal "error_class=$error_class rc=$rc"
    cleanup_invocation
    exit "${rc:-1}"
  fi

  record_health "$candidate" retryable "$error_class"
  log_event "$candidate" retryable "error_class=$error_class rc=$rc"
  cleanup_invocation

  # A full foreground agent may already have created public side effects.
  # Never replay that complete prompt on another provider after it starts.
  if [ "$MODE" = "agent" ]; then
    exit "$TEMP_FAILURE"
  fi
  if [ "$PROVIDER" != "auto" ]; then
    exit "$TEMP_FAILURE"
  fi
done

echo "model-runner: no healthy provider for mode=$MODE" >&2
exit "$TEMP_FAILURE"
