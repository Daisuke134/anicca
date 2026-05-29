#!/usr/bin/env bash
# heartbeat-extract-queue.sh — append recurring Pattern-Keys from ERRORS.md to
# the skill-extraction queue (~/.openclaw/state/skill-extraction-queue.txt).
#
# Dedup-preserving: keys already present in the queue are not re-added.
# Best-effort: failures must not break the heartbeat.

set -uo pipefail

QUEUE="$HOME/.openclaw/state/skill-extraction-queue.txt"
ERRS="$HOME/.openclaw/.learnings/ERRORS.md"
EXTRACT="$HOME/.openclaw/skills/_shared/pattern-extract.py"

mkdir -p "$(dirname "$QUEUE")"
touch "$QUEUE"

[ -f "$EXTRACT" ] || { echo "[queue] pattern-extract.py missing" >&2; exit 0; }
[ -f "$ERRS" ]    || { echo "[queue] ERRORS.md missing" >&2;    exit 0; }

ADDED=0
# pattern-extract.py prints "<count>\t<key>" lines (count desc).
while IFS=$'\t' read -r _count key; do
  [ -z "${key:-}" ] && continue
  if ! grep -qxF "$key" "$QUEUE"; then
    printf '%s\n' "$key" >> "$QUEUE"
    ADDED=$((ADDED+1))
  fi
done < <(python3 "$EXTRACT" "$ERRS" 2 2>/dev/null || true)

echo "[queue] added=$ADDED total=$(wc -l < "$QUEUE" | tr -d ' ')"
