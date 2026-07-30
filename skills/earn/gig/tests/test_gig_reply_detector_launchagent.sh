#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
PLIST="$ROOT/skills/earn/gig/launchd/ai.anicca.hf-gig-reply-detector.plist"

test -f "$PLIST" || { echo 'reply detector LaunchAgent missing'; exit 1; }
test "$(plutil -extract Label raw -o - "$PLIST")" = 'ai.anicca.hf-gig-reply-detector'
test "$(plutil -extract StartInterval raw -o - "$PLIST")" = '300'
test "$(plutil -extract RunAtLoad raw -o - "$PLIST")" = 'true'
test "$(plutil -extract ProgramArguments.0 raw -o - "$PLIST")" = '/bin/bash'
test "$(plutil -extract ProgramArguments.1 raw -o - "$PLIST")" = '__LIFE_MANAGER_REPO__/skills/earn/gig/scripts/run_with_cdp_lock.sh'
test "$(plutil -extract ProgramArguments.2 raw -o - "$PLIST")" = 'gig-reply-detector'
grep -q '/skills/earn/gig/scripts/reply_detector.py' "$PLIST"
! grep -q 'gig_pass.sh' "$PLIST" || { echo 'fallback scheduler launches expensive full pass'; exit 1; }
echo 'PASS: OS scheduler runs only the lightweight reply detector every five minutes'
