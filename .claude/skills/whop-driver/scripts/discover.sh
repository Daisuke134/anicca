#!/usr/bin/env bash
# whop-driver/discover.sh — open Whop Discover Campaigns + screenshot
#
# Usage:
#   bash discover.sh <TID> [<out.png>]
#
# TID = target ID returned by login.sh (or any logged-in whop.com tab in
# CloakBrowser daily-driver). Defaults output to /tmp/whop-discover-<UTC>.png.
#
# Output (stdout, one JSON line):
#   {"tid": "...", "url": "...", "screenshot": "<path>"}
set -euo pipefail

TID="${1:?usage: discover.sh <TID> [out.png]}"
OUT="${2:-/tmp/whop-discover-$(date -u +%Y%m%dT%H%M%SZ).png}"

PY=/opt/homebrew/bin/python3
CDP=~/.claude/skills/ig-account-create/scripts/cdp.py
URL="https://whop.com/joined/contentrewards/discover-campaigns-B5C5S1vijHGVt9/app/"

"$PY" "$CDP" nav "$TID" "$URL" >/dev/null
sleep 12   # iframe needs ~10s to fully paint the campaign carousel

"$PY" "$CDP" shot "$TID" "$OUT" >/dev/null

ACTUAL_URL=$("$PY" "$CDP" url "$TID" | $PY -c "import json,sys;print(json.load(sys.stdin)['url'])")
echo "{\"tid\":\"$TID\",\"url\":\"$ACTUAL_URL\",\"screenshot\":\"$OUT\"}"
