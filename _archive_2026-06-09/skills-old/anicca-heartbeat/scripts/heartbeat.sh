#!/usr/bin/env bash
# Single fire of the genesis heartbeat. Idempotent per-instant: writes ONE JSONL line.
# Invoked by `hermes cron` every 30m. Must complete in < 5 s.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${STATE_DIR:-/Users/operator/.hermes/state}"
mkdir -p "$STATE_DIR"
LOG="$STATE_DIR/heartbeat.jsonl"

probe="$("$SKILL_DIR/scripts/lifeline-check.sh")"
provider="$(echo "$probe" | /usr/bin/jq -r '.provider')"
model="$(echo "$probe" | /usr/bin/jq -r '.model')"
sha="$(echo "$probe"   | /usr/bin/jq -r '.constitution_sha')"
ts="$(echo "$probe"    | /usr/bin/jq -r '.ts')"

fuel="$provider"
ok=true
[ -z "$provider" ] && ok=false
[ -z "$sha" ]      && ok=false

line="$(/usr/bin/jq -nc \
  --arg ts "$ts" --argjson ok "$ok" \
  --arg fuel "$fuel" --arg model "$model" --arg constitution_sha "$sha" \
  --argjson probe "$probe" \
  '{ts:$ts, ok:$ok, fuel:$fuel, model:$model, constitution_sha:$constitution_sha, probe:$probe}')"

printf '%s\n' "$line" >> "$LOG"
echo "$line"
