#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
PLIST="$ROOT/skills/earn/gig/launchd/ai.anicca.hf-gig-reply-detector.plist"

test -f "$PLIST" || { echo 'reply detector LaunchAgent missing'; exit 1; }
test "$(plutil -extract Label raw -o - "$PLIST")" = 'ai.anicca.hf-gig-reply-detector'
test "$(plutil -extract StartInterval raw -o - "$PLIST")" = '180'
test "$(plutil -extract RunAtLoad raw -o - "$PLIST")" = 'true'
test "$(plutil -extract ProgramArguments.0 raw -o - "$PLIST")" = '/opt/homebrew/bin/python3'
test "$(plutil -extract ProgramArguments.1 raw -o - "$PLIST")" = '/workspace/life-manager/skills/earn/gig/scripts/reply_detector.py'
test "$(plutil -extract ProgramArguments.2 raw -o - "$PLIST")" = '--trigger'
test "$(plutil -extract ProgramArguments.3 raw -o - "$PLIST")" = 'fallback'
! grep -q 'run_with_cdp_lock.sh' "$PLIST" || { echo 'reply detector still wraps the whole wake in a CDP lock'; exit 1; }
! grep -q 'gig_pass.sh' "$PLIST" || { echo 'fallback scheduler launches expensive full pass'; exit 1; }
! grep -Eq 'GIG_REPLY_PASS_TOKEN_BUDGET|GIG_DAILY_TOKEN_BUDGET|GIG_BUDGET_DAILY_SCOPE|ANICCA_BUDGET_REQUIRED' "$PLIST" || { echo 'reply detector still exports obsolete pass budget env'; exit 1; }
echo 'PASS: OS scheduler runs only the lightweight reply detector every 3 minutes'
