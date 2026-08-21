#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RECORDER="$ROOT/skills/writer-agent/scripts/record-quality-advisory.py"
TMP="$(mktemp -d /tmp/article-quality-advisory.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT

printf '%s\n' 'API Error: Request rejected (429)' >"$TMP/raw.txt"
python3 "$RECORDER" \
  --output "$TMP/advisories.jsonl" \
  --gate rubric \
  --lang en \
  --attempt 3 \
  --exit-code 1 \
  --raw-file "$TMP/raw.txt"

jq -e 'select(.kind == "quality_advisory" and .gate == "rubric" and .lang == "en" and .attempt == 3 and .exit_code == 1 and (.raw_output | contains("429")) and .verdict != "PASS")' "$TMP/advisories.jsonl" >/dev/null
echo 'PASS: quality advisory preserves raw failure evidence without fake PASS'
