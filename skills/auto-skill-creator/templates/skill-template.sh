#!/usr/bin/env bash
# CANONICAL SKILL TEMPLATE — copy when scaffolding a new OpenClaw skill.
# This template bakes in the conventions every skill MUST follow:
#   1. Resolve Slack --target from canonical state, never hardcode the channel ID.
#   2. Source ~/.openclaw/.env so secrets never live in the script.
#   3. Honor a per-skill DRY env flag (NEW_SKILL_DRY_RUN=true).
#   4. Defer first-time setup to skill-onboarder.
set -euo pipefail

SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
SKILL_NAME="$(basename "$SKILL")"
MODE="${MODE:-default}"

# .env load (idempotent).
ENV_FILE="${OPENCLAW_ENV:-$HOME/.openclaw/.env}"
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

# Canonical Slack target — NEVER hardcode the channel ID.
SLACK_TARGET="$(jq -r '.slack.metrics_channel // empty' \
  "$HOME/.openclaw/state/anicca.json" 2>/dev/null)"
SLACK_TARGET="${SLACK_TARGET:-${SLACK_CHANNEL_ID:-}}"
if [[ -z "$SLACK_TARGET" ]]; then
  echo "[err] no Slack target — populate ~/.openclaw/state/anicca.json::slack.metrics_channel" >&2
  exit 2
fi

# DRY guard.
DRY="${NEW_SKILL_DRY_RUN:-true}"

# First-time-setup defer to skill-onboarder if no per-skill state exists.
STATE_FILE="$HOME/.openclaw/state/${SKILL_NAME}.json"
if [[ ! -f "$STATE_FILE" ]]; then
  echo "[skill-onboarder] no state for $SKILL_NAME yet — run:"
  echo "  SKILL=$SKILL_NAME bash $HOME/.openclaw/skills/skill-onboarder/scripts/run.sh"
  echo "[continuing in DRY mode with empty state]"
  STATE='{}'
else
  STATE="$(cat "$STATE_FILE")"
fi

# Mode dispatch — replace `default` with your real mode block.
case "$MODE" in
  default)
    SUMMARY="${SKILL_NAME} ran in mode=default dry=${DRY}"
    ;;
  *)
    echo "[err] unknown MODE=$MODE" >&2; exit 2 ;;
esac

# Slack send (LIVE only). Resolved target — see note above.
if [[ "$DRY" == "false" ]]; then
  openclaw message send --channel slack \
    --target "$SLACK_TARGET" \
    --message "$SUMMARY"
else
  printf '[DRY %s] target=%s message=%s\n' "$SKILL_NAME" "$SLACK_TARGET" "$SUMMARY"
fi
