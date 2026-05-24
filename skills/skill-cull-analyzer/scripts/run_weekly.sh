#!/usr/bin/env bash
# Weekly orchestrator. Called by cron Friday 17:00 JST.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$SKILL_DIR/state"
DATE=$(date +"%Y-%m-%d")
WEEK_FILE="$STATE_DIR/weekly_${DATE}.json"

mkdir -p "$STATE_DIR"

echo ">>> Step 1: Scan Claude Code transcripts"
bash "$SKILL_DIR/scripts/scan_claude_code.sh" \
  /Users/anicca/.claude/projects/-Users-anicca-anicca-project \
  /tmp/usage_cc.jsonl

echo ">>> Step 2: Scan Anicca cron + skills"
bash "$SKILL_DIR/scripts/scan_anicca.sh" \
  /Users/anicca/.openclaw/cron/jobs.json \
  /Users/anicca/.openclaw/skills \
  /tmp/usage_anicca.jsonl

echo ">>> Step 3: Analyze"
bash "$SKILL_DIR/scripts/analyze.sh" \
  /tmp/usage_cc.jsonl \
  /tmp/usage_anicca.jsonl \
  /tmp/usage_anicca_inventory.jsonl \
  "$WEEK_FILE"

echo ">>> Step 4: Report to Slack"
bash "$SKILL_DIR/scripts/report_to_slack.sh" "$WEEK_FILE"

echo ">>> Done. Snapshot: $WEEK_FILE"
