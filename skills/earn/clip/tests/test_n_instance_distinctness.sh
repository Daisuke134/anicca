#!/usr/bin/env bash
# PROP-004: resolve paths for N instance names, assert every resolved path
# (queue/posted/accounts/ledger, across ALL instances) is pairwise distinct —
# a set-based check, not eyeballing two instances at a time.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTANCES=("" "myclaude" "clawrouter" "clawrouter-2")
ALL_PATHS=()

for inst in "${INSTANCES[@]}"; do
  (
    if [ -n "$inst" ]; then export ANICCA_INSTANCE="$inst"; else unset ANICCA_INSTANCE; fi
    unset EARN_LEDGER
    source "$DIR/_instance_paths.sh"
    printf '%s\n%s\n%s\n%s\n' "$CLIP_QUEUE" "$CLIP_POSTED" "$CLIP_ACCTS" "$CLIP_LEDGER"
  )
done > /tmp/vcsdd-n-instance-paths.$$

while IFS= read -r p; do ALL_PATHS+=("$p"); done < /tmp/vcsdd-n-instance-paths.$$
rm -f /tmp/vcsdd-n-instance-paths.$$

TOTAL=${#ALL_PATHS[@]}
UNIQUE=$(printf '%s\n' "${ALL_PATHS[@]}" | sort -u | wc -l | tr -d ' ')

if [ "$TOTAL" != "$UNIQUE" ]; then
  echo "FAIL: $TOTAL resolved paths across ${#INSTANCES[@]} instances, only $UNIQUE unique (collision detected)"
  printf '%s\n' "${ALL_PATHS[@]}" | sort | uniq -d
  exit 1
fi
echo "ALL PASS ($TOTAL paths, $UNIQUE unique, ${#INSTANCES[@]} instances)"
