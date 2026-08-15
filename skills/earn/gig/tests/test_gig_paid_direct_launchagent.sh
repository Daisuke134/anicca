#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
PLIST="$ROOT/skills/earn/gig/launchd/ai.anicca.hf-gig-paid-direct.plist"

plutil -lint "$PLIST" >/dev/null
test "$(plutil -extract Label raw -o - "$PLIST")" = 'ai.anicca.hf-gig-paid-direct'
test "$(plutil -extract StartInterval raw -o - "$PLIST")" = '300'
grep -q '/workspace/gig/releases/paid/current/skills/earn/gig/scripts/paid_direct.py' "$PLIST"
grep -q '/workspace/gig/evidence/paid-direct-live/latest.json' "$PLIST"
! grep -qE 'gig_pass\.sh|\.worktrees/' "$PLIST"

echo 'PASS: Paid direct runs independently every 5 minutes from an immutable release'
