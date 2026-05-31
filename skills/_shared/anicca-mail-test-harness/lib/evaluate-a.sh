#!/usr/bin/env bash
# evaluate-a.sh — Category A (silent_archive) verifier.
# Args: <yaml_path> <ts>
# Exit: 0=pass, 1=fail

set -uo pipefail
YAML="$1"
TS="$2"
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

CASE_ID=$(basename "$YAML" .yaml)
echo "    [A] verifying $CASE_ID..."

# Read verify rules from YAML
THREAD_QUERY=$(python3 -c "
import yaml
with open('$YAML') as f:
    d = yaml.safe_load(f)
for v in d.get('verify', []):
    if v.get('type') == 'gmail_label':
        print(v.get('thread_query','').replace('{ts}','$TS'))
        break
")

if [ -z "$THREAD_QUERY" ]; then
  echo "    ⚠ no gmail_label verify rule found"
  exit 1
fi

# Find the thread matching the test
SEARCH=$(/opt/homebrew/bin/gog gmail search "$THREAD_QUERY" \
  --account "$GOG_ACCOUNT" --max 5 --json --results-only 2>&1)

THREAD_ID=$(echo "$SEARCH" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    items = d if isinstance(d, list) else d.get('messages', [])
    if items:
        print(items[0].get('threadId', items[0].get('id','')))
except Exception as e:
    pass
" 2>/dev/null)

if [ -z "$THREAD_ID" ]; then
  echo "    ⚠ thread not found for query: $THREAD_QUERY"
  exit 1
fi

# Check INBOX label absent
LABELS=$(/opt/homebrew/bin/gog gmail thread get "$THREAD_ID" \
  --account "$GOG_ACCOUNT" --json 2>&1 | \
  python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    labels = set()
    for m in d.get('messages', []):
        labels.update(m.get('labelIds', []))
    print(','.join(sorted(labels)))
except Exception:
    pass
")

if echo "$LABELS" | grep -qw "INBOX"; then
  echo "    ❌ INBOX label still present (expected absent) · labels=$LABELS"
  exit 1
fi

echo "    ✓ INBOX label absent (archived) · labels=$LABELS"
exit 0
