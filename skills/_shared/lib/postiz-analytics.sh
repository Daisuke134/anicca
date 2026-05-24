#!/usr/bin/env bash
# postiz-analytics.sh — shared Postiz analytics/listing wrappers.
#
# Source it:  source ~/.openclaw/skills/_shared/lib/postiz-analytics.sh
# Requires POSTIZ_API_KEY (auto-sourced from ~/.openclaw/.env if unset).
#
# Functions (all print JSON / TSV to stdout, never publish anything):
#   pa_env                         ensure POSTIZ_API_KEY is exported
#   pa_integrations                → JSON array [{id,name,identifier,disabled}]
#   pa_posts [n]                   → JSON array of latest n posts (default 50)
#   pa_posts_for <substr> [n]      → posts whose releaseURL matches substr (x.com, tiktok, etc)
#   pa_post_metrics <postId>       → JSON {postId, metrics:[{label,value}]}
#   pa_platform <integrationId>    → raw platform analytics JSON
#   pa_top <substr> <n>            → top n posts by first-metric value (views/impressions) for a platform substr
#
# Deterministic only. No LLM, no posting. (HARD RULE #6 safe.)

POSTIZ_BIN="${POSTIZ_BIN:-/opt/homebrew/bin/postiz}"

pa_env() {
  if [ -z "${POSTIZ_API_KEY:-}" ] && [ -f "$HOME/.openclaw/.env" ]; then
    set -a; . "$HOME/.openclaw/.env"; set +a
  fi
  [ -n "${POSTIZ_API_KEY:-}" ] || { echo "ERR: POSTIZ_API_KEY unset" >&2; return 3; }
}

# strip CLI banner, keep first JSON value
_pa_json() { sed -n '/^[[{]/,$p'; }

pa_integrations() {
  pa_env || return 3
  "$POSTIZ_BIN" integrations:list 2>&1 | _pa_json \
    | jq '[ .[] | {id, name, identifier:(.identifier // .providerIdentifier // "?"), disabled:(.disabled // false)} ]'
}

pa_posts() {
  pa_env || return 3
  local n="${1:-50}"
  "$POSTIZ_BIN" posts:list 2>&1 | _pa_json \
    | jq --argjson n "$n" '(.posts // .) | .[0:$n] | [ .[] | {id, state, releaseURL, integration, publishDate} ]'
}

pa_posts_for() {
  pa_env || return 3
  local sub="$1" n="${2:-10}"
  "$POSTIZ_BIN" posts:list 2>&1 | _pa_json \
    | jq --arg s "$sub" --argjson n "$n" \
      '(.posts // .) | map(select(.releaseURL != null and (.releaseURL|test($s)))) | .[0:$n] | [ .[] | {id, state, releaseURL} ]'
}

pa_post_metrics() {
  pa_env || return 3
  local pid="$1"
  local raw
  raw=$("$POSTIZ_BIN" analytics:post "$pid" 2>&1 | _pa_json)
  echo "$raw" | jq -c --arg id "$pid" \
    '{postId:$id, metrics:[ .[]? | {label, value:(.data[-1].total // .data[-1].value // .value // .total // "0")} ]}' \
    2>/dev/null || echo "{\"postId\":\"$pid\",\"metrics\":[],\"error\":\"no analytics\"}"
}

pa_platform() {
  pa_env || return 3
  "$POSTIZ_BIN" analytics:platform "$1" 2>&1 | _pa_json
}

# Platform → releaseURL regex. X posts are twitter.com (NOT x.com) — use this map,
# do not hand-write the regex at call sites.
pa_re() {
  case "$1" in
    x|twitter|X)        echo 'twitter\.com|x\.com/.+/status' ;;
    tt|tiktok|TikTok)   echo 'tiktok\.com' ;;
    ig|instagram|IG)    echo 'instagram\.com' ;;
    yt|youtube|YT)      echo 'youtube\.com|youtu\.be' ;;
    *)                  echo "$1" ;;  # passthrough: already a regex
  esac
}

# pa_top_platform <x|tt|ig|yt> <n>: convenience — resolves the regex then pa_top
pa_top_platform() { pa_top "$(pa_re "$1")" "${2:-3}"; }

# pa_top_content <x|tt|ig|yt> <n>: top n posts WITH their text content + metrics.
# Used by hot-hooks-refresh so the model can see the actual winning hooks.
pa_top_content() {
  pa_env || return 3
  local plat="$1" n="${2:-3}" re tmp
  re=$(pa_re "$plat")
  tmp=$(mktemp)
  pa_top "$re" "$n" > "$tmp"     # valid JSON array of {postId,score,metrics}
  "$POSTIZ_BIN" posts:list 2>&1 | _pa_json | jq \
    --slurpfile top "$tmp" --arg s "$re" --arg plat "$plat" '
      ((.posts // .) | map(select(.releaseURL!=null and (.releaseURL|test($s))))
        | .[0:25] | map({(.id):{content,releaseURL,state}}) | add) as $cm
      | ($top[0] // []) | [ .[] | (
          ($cm[.postId].content // "") as $c
          | ($cm[.postId].releaseURL // "") as $u
          | {
            platform:$plat, postId, score,
            metric:(.metrics[0].label // ""),
            content:(if ($c|gsub("\\s";"")) == "" then ("(media-only post — " + (if $u != "" then $u else .postId end) + ")") else $c end),
            url:$u,
            metrics } ) ]'
  rm -f "$tmp"
}

# pa_top <releaseURL-substr> <n>: latest 25 matching posts, fetch metrics, sort desc by first numeric metric
pa_top() {
  pa_env || return 3
  local sub="$1" n="${2:-3}"
  pa_posts_for "$sub" 25 | jq -r '.[].id' | while IFS= read -r pid; do
    [ -n "$pid" ] && pa_post_metrics "$pid"
  done | jq -s --argjson n "$n" '
      map(. + {score: ((.metrics[0].value // "0") | tonumber? // 0)})
      | sort_by(-.score) | .[0:$n]'
}
