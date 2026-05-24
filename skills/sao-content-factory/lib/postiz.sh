#!/usr/bin/env bash
# lib/postiz.sh — Postiz CLI wrapper
set -euo pipefail

# postiz_upload <file>
# Prints uploaded file URL on stdout
postiz_upload() {
  local file="$1"
  [ -f "$file" ] || { echo "ERR: file not found: $file" >&2; return 3; }

  local result url
  result=$(/opt/homebrew/bin/postiz upload "$file" 2>&1)
  url=$(echo "$result" | sed -n '/^{/,$p' | jq -r '.path // empty')
  [ -z "$url" ] && { echo "ERR: postiz upload failed: $result" >&2; return 4; }
  printf "%s" "$url"
}

# postiz_post_json <json_file>
# Submits a post via JSON config. Prints postId(s) on stdout.
postiz_post_json() {
  local json="$1"
  local result
  result=$(/opt/homebrew/bin/postiz posts:create --json "$json" 2>&1)
  if echo "$result" | grep -q "✅ Post created"; then
    echo "$result" | sed -n '/^\[/,$p' | jq -r '.[].postId'
  else
    echo "ERR: postiz post failed: $result" >&2
    return 4
  fi
}
