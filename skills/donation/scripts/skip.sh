#!/usr/bin/env bash
# donation skip <YYYY-MM> — write a skip sentinel honored by the monthly cron.
#
# Usage:
#   bash ~/.openclaw/skills/donation/scripts/skip.sh 2026-05
#   bash ~/.openclaw/skills/donation/scripts/skip.sh 2026-05 "feeding ourselves this month"
#
# Removes the sentinel:
#   bash ~/.openclaw/skills/donation/scripts/skip.sh 2026-05 --unskip

set -uo pipefail

PERIOD="${1:?usage: skip.sh YYYY-MM [reason|--unskip]}"
ARG2="${2:-}"

WORKSPACE="$HOME/.openclaw/workspace/donation"
mkdir -p "$WORKSPACE"
SENTINEL="$WORKSPACE/skipped-$PERIOD.json"

if [ "$ARG2" = "--unskip" ]; then
  if [ -f "$SENTINEL" ]; then
    rm -f "$SENTINEL"
    echo "✅ removed skip sentinel for $PERIOD"
  else
    echo "ℹ️  no sentinel for $PERIOD; nothing to do"
  fi
  exit 0
fi

REASON="${ARG2:-no reason given}"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
USER_NAME="${USER:-unknown}"

cat > "$SENTINEL" <<EOF
{
  "period": "$PERIOD",
  "skipped_at": "$TS",
  "skipped_by": "$USER_NAME",
  "reason": "$REASON"
}
EOF

echo "✅ wrote $SENTINEL"
echo "    monthly cron for $PERIOD will be a no-op while this file exists."
