#!/usr/bin/env bash
# content-metrics-daily — pull last-24h Postiz analytics for every active integration,
# write per-account JSON, post (or print if DRY_RUN) the Slack digest.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/postiz.sh
source "$SKILL_DIR/lib/postiz.sh"
# shellcheck source=lib/report.sh
source "$SKILL_DIR/lib/report.sh"

PORTFOLIO="${PORTFOLIO:-$HOME/.openclaw/state/postiz-integrations.json}"
OUT_ROOT="${OUT_ROOT:-$HOME/.openclaw/workspace/content-metrics}"
DRY_RUN="${CONTENT_METRICS_DRY_RUN:-false}"

if [[ ! -f "$PORTFOLIO" ]]; then
  echo "Portfolio not found: $PORTFOLIO" >&2
  exit 1
fi

# Time window: yesterday 00:00 → now (Asia/Tokyo)
START="$(TZ=Asia/Tokyo date -d "yesterday" +%Y-%m-%dT00:00:00 2>/dev/null || TZ=Asia/Tokyo date -v-1d +%Y-%m-%dT00:00:00)"
END="$(TZ=Asia/Tokyo date +%Y-%m-%dT%H:%M:%S)"
TODAY="$(TZ=Asia/Tokyo date +%Y-%m-%d)"
DAY_DIR="$OUT_ROOT/$TODAY"
mkdir -p "$DAY_DIR"

echo "[content-metrics-daily] window=$START → $END  out=$DAY_DIR  dry_run=$DRY_RUN"

# In DRY_RUN, do NOT hit Postiz unless POSTIZ_API_KEY is set; emit synthetic rows so we still
# render the would-be table. Real run: fetch + persist + aggregate.
ROWS_FILE="$(mktemp)"

if [[ "$DRY_RUN" == "true" && -z "${POSTIZ_API_KEY:-}" ]]; then
  echo "[dry_run] POSTIZ_API_KEY unset — emitting synthetic rows."
  python3 - "$PORTFOLIO" > "$ROWS_FILE" <<'PY'
import sys, json
with open(sys.argv[1]) as f: portfolio = json.load(f)
for integ in portfolio.get("integrations", []):
    if not integ.get("active"): continue
    print(json.dumps({
        "handle": integ["handle"], "platform": integ["platform"],
        "posts": 0, "total_views": 0, "total_likes": 0, "engagement_rate": 0,
    }))
PY
else
  POSTS_LIST="$(postiz_list_posts "$START" "$END" || echo '{"posts":[]}')"
  jq -c '.integrations[] | select(.active==true)' "$PORTFOLIO" | while read -r integ; do
    iid=$(jq -r '.id' <<<"$integ")
    handle=$(jq -r '.handle' <<<"$integ")
    platform=$(jq -r '.platform' <<<"$integ")
    out_file="$DAY_DIR/${platform}-$(echo "$handle" | tr -c 'A-Za-z0-9_-' '_').json"

    # post ids belonging to this integration in window — PUBLISHED only
    # (DRAFT/ERROR posts have no analytics; including them yields false zeros)
    post_ids=$(echo "$POSTS_LIST" | jq -r --arg iid "$iid" \
      '[.posts[]? | select(.integration.id==$iid and .state=="PUBLISHED") | .id] | .[]')

    : > "$out_file.analytics.tmp"
    while IFS= read -r pid; do
      [[ -z "$pid" ]] && continue
      if [[ "$DRY_RUN" == "true" ]]; then
        echo "[dry_run] would GET analytics/post/$pid for $handle ($platform)"
      else
        postiz_get_analytics "$pid" >> "$out_file.analytics.tmp"
        echo >> "$out_file.analytics.tmp"
      fi
    done <<<"$post_ids"

    # Build per-account JSON
    if [[ "$DRY_RUN" == "true" ]]; then
      jq -nc --arg h "$handle" --arg p "$platform" --arg iid "$iid" \
        '{handle:$h, platform:$p, integration_id:$iid, posts:0, total_views:0, total_likes:0, engagement_rate:0, dry_run:true}' \
        | tee -a "$ROWS_FILE" > "$out_file"
    else
      agg=$(postiz_aggregate < "$out_file.analytics.tmp")
      jq -nc --argjson agg "$agg" --arg h "$handle" --arg p "$platform" --arg iid "$iid" \
        '$agg + {handle:$h, platform:$p, integration_id:$iid}' \
        | tee -a "$ROWS_FILE" > "$out_file"
    fi
    rm -f "$out_file.analytics.tmp"
  done
fi

echo
if [[ "$DRY_RUN" == "true" ]]; then
  echo "----- DRY_RUN — would post to #metrics ({{profile.channels.reportChannel}}) -----"
  format_daily_table < "$ROWS_FILE"
  echo "----- end DRY_RUN -----"
else
  # Cron delivery is set to announce; we just print the formatted block — it lands in #metrics.
  format_daily_table < "$ROWS_FILE"
fi

rm -f "$ROWS_FILE"
