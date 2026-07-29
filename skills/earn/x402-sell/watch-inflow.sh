#!/bin/bash
# watch-inflow.sh — session-independent external-buyer watch (launchd, every 30 min).
# Runs verify-inflow.mjs over the last 2h; on the FIRST external inflow it writes a
# flag file + macOS notification so any session (or Dais) sees the zero-to-one moment.
set -o pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# Parameterizable per instance: X402_PAYTO selects the watched wallet (verify-inflow.mjs reads it),
# X402_WATCH_TAG separates log/flag files (default = founder watch).
TAG="${X402_WATCH_TAG:-}"
LOG="$HOME/.local/state/life-manager/.logs/x402-inflow${TAG:+-$TAG}.jsonl"
FLAG="$HOME/.local/state/life-manager/.logs/x402-first-external${TAG:+-$TAG}.json"
mkdir -p "$(dirname "$LOG")"

OUT="$(cd "$DIR" && /usr/bin/env node verify-inflow.mjs 2 2>/dev/null)"
SUMMARY="$(printf '%s' "$OUT" | /usr/bin/env node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{const m=d.match(/\{[\s\S]*?\n\}/);const j=JSON.parse(m[0]);console.log(JSON.stringify({ts:new Date().toISOString(),external:j.EXTERNAL,externalUsdc:j.externalUsdc,inflows:j.inflows}))}catch(e){console.log(JSON.stringify({ts:new Date().toISOString(),error:String(e).slice(0,120)}))}})")"
printf '%s\n' "$SUMMARY" >> "$LOG"

EXT="$(printf '%s' "$SUMMARY" | grep -o '"external":[0-9]*' | grep -o '[0-9]*$')"
if [ -n "$EXT" ] && [ "$EXT" -gt 0 ] && [ ! -f "$FLAG" ]; then
  printf '%s\n' "$OUT" > "$FLAG"
  /usr/bin/osascript -e 'display notification "EXTERNAL x402 buyer paid — zero-to-one! See $HOME/.local/state/life-manager/.logs/x402-first-external.json" with title "x402 ZERO-TO-ONE" sound name "Glass"' >/dev/null 2>&1 || true
fi
exit 0
