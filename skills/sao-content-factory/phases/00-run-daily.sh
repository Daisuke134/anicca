#!/usr/bin/env bash
# 00-run-daily.sh — SAO Content Factory orchestrator
#
# Picks today's entity by JST day-of-week, runs all phases, emits ONE summary line.
# Idempotent: state/<entity>-<date>.done prevents re-runs.
#
# Manual override: ENTITY=<slug> bash 00-run-daily.sh
#
# Exit codes:
#   0 = success or already-done-today (idempotent)
#   non-zero = phase failure

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/sao-content-factory"
cd "$SKILL_DIR"

# Load env
if [ -f "$HOME/.openclaw/.env" ]; then
  set -a; source "$HOME/.openclaw/.env"; set +a
fi

# Source libs
for lib in lib/*.sh; do source "$lib"; done

# Pick entity by JST day-of-week (Mon=1 .. Sun=7)
JST_DAY=$(TZ=Asia/Tokyo date +%u)
JST_DATE=$(TZ=Asia/Tokyo date +%Y-%m-%d)

case "${ENTITY:-}" in
  "")
    case "$JST_DAY" in
      1) ENTITY="andon-stockholm-cafe" ;;
      2) ENTITY="kelly" ;;
      3) ENTITY="light-anchor" ;;
      4) ENTITY="polsia" ;;
      5) ENTITY="truth-terminal" ;;
      6) ENTITY="anicca-self" ;;
      7) ENTITY="weekly-roundup" ;;
    esac
    ;;
esac

ENTITY_JSON="$SKILL_DIR/entities/$ENTITY.json"
[ -f "$ENTITY_JSON" ] || { echo "❌ FAILED at orchestrator: entity $ENTITY not found ($ENTITY_JSON)"; exit 2; }

OUT_DIR="$SKILL_DIR/output/$ENTITY/$JST_DATE"
STATE_FILE="$SKILL_DIR/state/$ENTITY-$JST_DATE.done"
LOG_DIR="$OUT_DIR/logs"
ERR_LOG="$LOG_DIR/run.err.log"

# Idempotent: skip if today's run is already done
if [ -f "$STATE_FILE" ]; then
  STATE=$(cat "$STATE_FILE")
  echo "✅ Already done today: $ENTITY @ $JST_DATE — $STATE"
  exit 0
fi

# Find next version dir
N=1
while [ -d "$OUT_DIR/v$N" ]; do N=$((N+1)); done
VERSION_DIR="$OUT_DIR/v$N"
mkdir -p "$VERSION_DIR/img" "$VERSION_DIR/broll" "$VERSION_DIR/vo" "$VERSION_DIR/bgm" "$VERSION_DIR/output" "$VERSION_DIR/docs" "$LOG_DIR"

export ENTITY ENTITY_JSON VERSION_DIR JST_DATE SKILL_DIR

# Run phases sequentially
PHASES=(
  "01-source.sh"
  "02-script.sh"
  "03-assets.sh"
  "04-render.sh"
  "05-thread.sh"
  "06-publish.sh"
  "07-report.sh"
)

LAST_OUTPUT=""
for phase in "${PHASES[@]}"; do
  echo "  ▶ phase: $phase" >&2
  PHASE_LOG="$LOG_DIR/${phase%.sh}.log"
  if ! out=$(bash "$SKILL_DIR/phases/$phase" 2>"$PHASE_LOG"); then
    {
      echo "❌ FAILED at phase $phase: see $PHASE_LOG"
      tail -10 "$PHASE_LOG" || true
    } > "$ERR_LOG"
    cat "$ERR_LOG"
    exit 4
  fi
  LAST_OUTPUT="$out"
done

# Mark done
echo "$LAST_OUTPUT" > "$STATE_FILE"

# Emit final summary line (this becomes the Slack message)
echo "$LAST_OUTPUT"
