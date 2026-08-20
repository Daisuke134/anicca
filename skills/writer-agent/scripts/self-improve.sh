#!/usr/bin/env bash
# Daily 22:30 evidence-bound article learning entrypoint.
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -a
. "$HOME/.openclaw/.env" 2>/dev/null || true
set +a

SKILL_DIR="${ARTICLE_SKILL_DIR:-$HOME/profitable-claude/skills/article-writer}"
STATE_DIR="$SKILL_DIR/state"
LOG_DIR="$HOME/.openclaw/logs"
mkdir -p "$STATE_DIR" "$LOG_DIR"

# Score the day's title ledger against real high-performing titles before the
# controller reads quality. Nothing in the tree called beat_rate.py, so the
# ledgers the daily run writes were being produced and never scored (measured
# 2026-07-27) -- a loop that looks like it is learning and is not. A failure
# here is a missing data point, never a reason to skip the controller below.
bash "$SKILL_DIR/scripts/score-latest-run.sh" >> "$LOG_DIR/writer-beat-rate.log" 2>&1 || true

# Count what is left to write. The outlet has been instrumented for months and
# the inlet never was; on 2026-07-27 the queue held one card fifteen minutes
# before a publish. Running it here rather than in the morning buys a full day
# of warning, which is the difference between refilling calmly and skipping.
bash "$SKILL_DIR/scripts/topic-supply.sh" >> "$LOG_DIR/writer-topic-supply.log" 2>&1 || true

# The Python controller owns one lock across measurement, proposal/review,
# pre-application journaling, the exact playbook diff, keep/revert, commit,
# push, and the durable receipt. Provider failure exits retryable while the
# last-known-good playbook and the daily publisher remain untouched.
set +e
RESULT="$(python3 "$SKILL_DIR/scripts/self_improve_control.py" run \
  --skill-dir "$SKILL_DIR")"
RC=$?
set -e
printf '%s\n' "$RESULT"
if [[ "$RC" -ne 0 ]]; then
  exit "$RC"
fi

RECEIPT_DATE="$(printf '%s' "$RESULT" | jq -er '.observed_at[0:10]')"
RECEIPT="$STATE_DIR/learning/receipts/$RECEIPT_DATE.json"
VERIFY_RESULT="$(python3 "$SKILL_DIR/scripts/self_improve_control.py" verify \
  --skill-dir "$SKILL_DIR")"
printf '%s\n' "$VERIFY_RESULT"
python3 "$SKILL_DIR/scripts/self-improve-notify.py" \
  --skill-dir "$SKILL_DIR" \
  --receipt "$RECEIPT"
