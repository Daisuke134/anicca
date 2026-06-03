#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# _shared/heartbeat-memu.sh — memU fragment called by heartbeat-beat.sh.
#
# Modes:
#   retrieve   builds 3 orient queries from current cron context + recent beat
#              summary, asks memU for top relevant items, prints JSON to stdout.
#   memorize   reads HEARTBEAT_DIARY (env or stdin) and persists summaries
#              into data/items.jsonl for the next beat to replay.
#
# Honours MEMU_DRY_RUN=1 for dry-run (prints stdin payload, skips python).
# Pure bash — no external deps beyond python3.13 venv at $MEMU_VENV.

set -euo pipefail

MODE="${1:-retrieve}"
MEMU_VENV="${MEMU_VENV:-$HOME/.anicca-genesis/memU-test/.venv}"
REPO_DIR="${MEMU_REPO_DIR:-$HOME/anicca-oss}"
WRAPPER="$REPO_DIR/runtime/memu/wrappers/heartbeat.py"
USER_JSON='{"user_id":"anicca-001"}'

# Fall back to worktree if repo runtime is not yet merged
if [[ ! -f "$WRAPPER" ]]; then
  for cand in \
    "$HOME/anicca-oss/.worktrees/memu/runtime/memu/wrappers/heartbeat.py" \
    "$HOME/.openclaw/runtime/memu/wrappers/heartbeat.py"; do
    if [[ -f "$cand" ]]; then WRAPPER="$cand"; break; fi
  done
fi

if [[ ! -f "$WRAPPER" ]]; then
  echo "heartbeat-memu: wrapper not found at $WRAPPER — skipping (non-fatal)" >&2
  exit 0
fi

if [[ ! -x "$MEMU_VENV/bin/python" ]]; then
  echo "heartbeat-memu: venv missing at $MEMU_VENV — skipping (non-fatal)" >&2
  exit 0
fi

# Load env: DEEPSEEK_API_KEY required, OLLAMA_API_KEY placeholder if missing
if [[ -f "$HOME/.openclaw/.env" ]]; then
  set -a; . "$HOME/.openclaw/.env"; set +a
fi
export OLLAMA_API_KEY="${OLLAMA_API_KEY:-ollama}"

if [[ "${MEMU_DRY_RUN:-0}" == "1" ]]; then
  echo "{\"dry_run\": true, \"mode\": \"$MODE\", \"wrapper\": \"$WRAPPER\", \"user\": $USER_JSON}"
  exit 0
fi

case "$MODE" in
  retrieve)
    # Build the orient queries from heartbeat context
    QUERIES=$(cat <<JSON
{
  "queries": [
    {"query": "What gigs / customers are waiting for Anicca right now?"},
    {"query": "What did we learn or commit to in the last 24h?"},
    {"query": "Which channels and credentials are proven and ready?"}
  ]
}
JSON
)
    echo "$QUERIES" | "$MEMU_VENV/bin/python" "$WRAPPER" retrieve --user "$USER_JSON"
    ;;
  memorize)
    # Read stdin (= heartbeat diary). If empty, use HEARTBEAT_DIARY env var.
    if [[ -t 0 ]]; then
      DIARY="${HEARTBEAT_DIARY:-}"
      if [[ -z "$DIARY" ]]; then
        echo "heartbeat-memu: no stdin and HEARTBEAT_DIARY unset — skipping" >&2
        exit 0
      fi
      printf '%s' "$DIARY" | "$MEMU_VENV/bin/python" "$WRAPPER" memorize --user "$USER_JSON"
    else
      "$MEMU_VENV/bin/python" "$WRAPPER" memorize --user "$USER_JSON"
    fi
    ;;
  *)
    echo "heartbeat-memu: unknown mode '$MODE' (expected retrieve|memorize)" >&2
    exit 2
    ;;
esac
