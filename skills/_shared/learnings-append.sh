#!/usr/bin/env bash
# learnings-append.sh — append a structured entry to .learnings/{LEARNINGS,ERRORS}.md.
#
# Args:
#   $1 = kind (success | failure)
#   $2 = category (e.g. best_practice, correction, insight, knowledge_gap)
#   $3 = pattern_key (dot-separated, e.g. uber.license.metadata-required)
#   $4 = round (escalation round number, 1..6)
#   $5 = summary (single-line)
#   $6 = details (optional, multi-line ok)
#
# Stdout: the new entry's ID (e.g. LRN-20260529-742 or ERR-20260529-103).
# Stderr: any errors.

set -uo pipefail

if [ "$#" -lt 5 ]; then
  echo "[learnings-append] usage: $0 <success|failure> <category> <pattern_key> <round> <summary> [<details>]" >&2
  exit 2
fi

KIND="$1"; CATEGORY="$2"; PATTERN_KEY="$3"; ROUND="$4"; SUMMARY="$5"; DETAILS="${6:-}"
LEARN_DIR="$HOME/.openclaw/.learnings"
mkdir -p "$LEARN_DIR"

DATE=$(date -u +%Y%m%d)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SUFFIX=$(printf '%03d' $((RANDOM % 1000)))

case "$KIND" in
  success)
    FILE="$LEARN_DIR/LEARNINGS.md"
    ID="LRN-$DATE-$SUFFIX"
    ;;
  failure)
    FILE="$LEARN_DIR/ERRORS.md"
    ID="ERR-$DATE-$SUFFIX"
    ;;
  *)
    echo "[learnings-append] kind must be 'success' or 'failure', got '$KIND'" >&2
    exit 2
    ;;
esac

cat >> "$FILE" <<ENT

## [$ID] $CATEGORY

**Logged**: $TS
**Pattern-Key**: $PATTERN_KEY
**Round**: $ROUND

### Summary
$SUMMARY

### Details
$DETAILS

---
ENT

echo "$ID"
