#!/usr/bin/env bash
# Scan Claude Code transcripts for Skill tool invocations.
# Output: JSONL {ts, skill, system: "claude-code", session}
set -euo pipefail

PROJECT_DIR="${1:-/Users/anicca/.claude/projects/-Users-anicca-anicca-project}"
OUT="${2:-/tmp/usage_cc.jsonl}"

: > "$OUT"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "ERR: $PROJECT_DIR not found" >&2
  exit 1
fi

# Iterate every .jsonl transcript; pull Skill tool calls
find "$PROJECT_DIR" -name "*.jsonl" -type f | while read -r f; do
  session=$(basename "$f" .jsonl)
  # Each line is one event. Filter for Skill tool_use.
  grep -h '"name":"Skill"' "$f" 2>/dev/null | \
    jq -c --arg session "$session" '
      {
        ts: .timestamp,
        skill: (.message.content[]? | select(.type=="tool_use" and .name=="Skill") | .input.skill // .input.name // "unknown"),
        system: "claude-code",
        session: $session,
        cwd: .cwd,
        branch: .gitBranch
      } | select(.skill != null and .skill != "")
    ' 2>/dev/null >> "$OUT" || true
done

echo "Wrote $(wc -l < "$OUT") events to $OUT"
