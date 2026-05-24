#!/usr/bin/env bash
# Scan Anicca's cron jobs.json + skills/ directory.
# Output: JSONL of skill usage events derived from cron last-run timestamps.
set -euo pipefail

JOBS_JSON="${1:-/Users/anicca/.openclaw/cron/jobs.json}"
SKILLS_DIR="${2:-/Users/anicca/.openclaw/skills}"
OUT="${3:-/tmp/usage_anicca.jsonl}"

: > "$OUT"

if [ ! -f "$JOBS_JSON" ]; then
  echo "ERR: $JOBS_JSON not found" >&2
  exit 1
fi

# Each cron job's payload.message often references a skill name.
# Parse: extract skill name from payload.message via regex on "Execute X skill" or "skills/X/SKILL.md"
jq -c '.jobs[] | select(.enabled == true)' "$JOBS_JSON" | while read -r job; do
  job_id=$(echo "$job" | jq -r '.id')
  last_run_ms=$(echo "$job" | jq -r '.state.lastRunAtMs // 0')
  last_status=$(echo "$job" | jq -r '.state.lastStatus // "unknown"')
  message=$(echo "$job" | jq -r '.payload.message // ""')

  # Skip if never run
  [ "$last_run_ms" = "0" ] && continue

  # Convert ms → ISO ts
  ts=$(date -u -r $((last_run_ms / 1000)) +"%Y-%m-%dT%H:%M:%S.000Z" 2>/dev/null || echo "")

  # Extract skill name: match either "skills/<name>/" or "Execute <name> skill"
  skill=$(echo "$message" | grep -oE 'skills/[a-z0-9_-]+' | head -1 | sed 's|skills/||' || echo "")
  if [ -z "$skill" ]; then
    skill=$(echo "$message" | grep -oE 'Execute [a-z0-9_-]+ skill' | head -1 | sed 's/Execute //; s/ skill//' || echo "")
  fi
  # Fallback: use job_id as skill name
  [ -z "$skill" ] && skill="$job_id"

  jq -n -c --arg ts "$ts" --arg skill "$skill" --arg job "$job_id" --arg status "$last_status" '
    {
      ts: $ts,
      skill: $skill,
      system: "anicca",
      cron_job: $job,
      status: $status
    }
  ' >> "$OUT"
done

echo "Wrote $(wc -l < "$OUT") events to $OUT"

# Also dump the full skills/ listing as a separate "inventory" file.
# Use SKILL.md mtime (more stable than dir mtime which changes when any file inside touches).
INV="${OUT%.jsonl}_inventory.jsonl"
: > "$INV"
find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d | while read -r d; do
  name=$(basename "$d")
  # Skip hidden / backup folders
  case "$name" in
    .*|_*) continue ;;
  esac
  has_skill_md="false"
  added_ts=""
  if [ -f "$d/SKILL.md" ]; then
    has_skill_md="true"
    added_ts=$(date -u -r "$d/SKILL.md" +"%Y-%m-%dT%H:%M:%S.000Z" 2>/dev/null || echo "")
  fi
  jq -n -c --arg name "$name" --arg ts "$added_ts" --argjson has "$has_skill_md" '
    { skill: $name, added_at: $ts, has_skill_md: $has }
  ' >> "$INV"
done
echo "Wrote inventory $(wc -l < "$INV") skills to $INV"
