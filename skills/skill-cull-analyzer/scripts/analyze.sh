#!/usr/bin/env bash
# Analyze usage events, output report JSON.
set -euo pipefail

CC="${1:-/tmp/usage_cc.jsonl}"
ANICCA="${2:-/tmp/usage_anicca.jsonl}"
INV="${3:-/tmp/usage_anicca_inventory.jsonl}"
OUT="${4:-/tmp/skill_cull_report.json}"

NOW_TS=$(date -u +%s)
DAY_30=$((NOW_TS - 30 * 86400))
DAY_21=$((NOW_TS - 21 * 86400))
DAY_7=$((NOW_TS - 7 * 86400))

# Helper: emit "skill\tepoch_ts" pairs
emit_pairs() {
  local file="$1"
  [ ! -s "$file" ] && return 0
  jq -r 'select(.ts != null and .ts != "") | "\(.skill)\t\(.ts)"' "$file" | \
    while IFS=$'\t' read -r skill ts; do
      epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "${ts%.*}" +%s 2>/dev/null || echo "0")
      [ "$epoch" != "0" ] && echo -e "${skill}\t${epoch}"
    done
}

# Aggregate per system
aggregate() {
  local system="$1"
  local file="$2"
  emit_pairs "$file" | awk -v now="$NOW_TS" -v d30="$DAY_30" -v d21="$DAY_21" -v d7="$DAY_7" '
    {
      skill = $1; epoch = $2;
      total[skill]++;
      if (epoch >= d30) cnt30[skill]++;
      if (epoch >= d7)  cnt7[skill]++;
      if (epoch > last[skill]) last[skill] = epoch;
    }
    END {
      for (s in total) {
        days_since = int((now - last[s]) / 86400);
        printf "%s\t%d\t%d\t%d\t%d\n", s, cnt30[s]+0, cnt7[s]+0, days_since, last[s];
      }
    }' | sort -t$'\t' -k2 -nr
}

# Filter out UUID-shaped skill names (one-shot anicca crons) before aggregating
filter_uuids() {
  grep -vE '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b' || true
}

CC_AGG=$(aggregate "claude-code" "$CC" | filter_uuids)
AN_AGG=$(aggregate "anicca" "$ANICCA" | filter_uuids)

emit_section() {
  local key="$1"
  local agg="$2"
  TOP=$(echo "$agg" | head -10 | awk -F'\t' '{printf "{\"skill\":\"%s\",\"count_30d\":%d,\"count_7d\":%d,\"days_since\":%d},", $1, $2, $3, $4}' | sed 's/,$//')
  KILL=$(echo "$agg" | awk -F'\t' '$4 >= 21 && $2 == 0 {printf "{\"skill\":\"%s\",\"days_since\":%d},", $1, $4}' | sed 's/,$//')
  DOUBT=$(echo "$agg" | awk -F'\t' '$2 >= 1 && $2 <= 2 {printf "{\"skill\":\"%s\",\"count_30d\":%d,\"days_since\":%d},", $1, $2, $4}' | sed 's/,$//')
  TOTAL=$(echo "$agg" | grep -c . || echo "0")

  echo "  \"$key\": {"
  echo "    \"top\": [${TOP}],"
  echo "    \"kill_candidates\": [${KILL}],"
  echo "    \"doubt\": [${DOUBT}],"
  echo "    \"total_observed\": ${TOTAL}"
  echo "  },"
}

# Build JSON report
{
  echo "{"
  echo '  "generated_at": "'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'",'
  emit_section "claude_code" "$CC_AGG"
  emit_section "anicca" "$AN_AGG"

  # Inventory: total Anicca skills on disk + 5 most-recently-touched SKILL.md
  if [ -s "$INV" ]; then
    INV_COUNT=$(wc -l < "$INV" | tr -d ' ')
    RECENT=$(jq -s -c 'sort_by(.added_at) | reverse | .[0:5] | map({skill, added_at: (.added_at[0:10])})' "$INV" 2>/dev/null || echo '[]')
    echo "  \"inventory\": {"
    echo "    \"anicca_skills_on_disk\": $INV_COUNT,"
    echo "    \"most_recent_touched\": $RECENT"
    echo "  }"
  fi

  echo "}"
} > "$OUT"

echo "Report written to $OUT"
echo "---"
jq . "$OUT" 2>/dev/null || cat "$OUT"
