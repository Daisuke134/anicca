#!/usr/bin/env bash
# loop-scale.sh — STEP 6 SELF-SCALE: read roi.jsonl, propose strategy edit (via REQ-C3 gate).
# Sprint-1 scaffold; sprint-2 wires real scale-up (spawn alt accounts / raise cadence).
#
# Usage: loop-scale.sh <slot>
set -uo pipefail
SLOT="${1:-}"
ROI_PATH="${HOME}/loops/${SLOT}/roi.jsonl"
[ -f "$ROI_PATH" ] || { echo "loop-scale: roi.jsonl not found for ${SLOT}, skip"; exit 0; }

# Sprint-1 scaffold: emit a no-op decision.
# Sprint-2: compute roi_7day_jpy, decide scale-up / contract / disable.
echo "loop-scale: scaffold no-op (sprint-1); production scale logic deferred to sprint-2"
