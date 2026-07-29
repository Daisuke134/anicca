#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
GIG="$ROOT/skills/gig-work"
README="$ROOT/README.md"
HOURLY="$GIG/launchd/ai.anicca.hf-gig-hourly-report.plist"
WEEKLY="$GIG/launchd/ai.anicca.hf-gig-weekly-report.plist"

grep -q 'scripts/telegram_report.py.*daily' "$GIG/gig_daily_report.sh"
! grep -q 'openclaw message send' "$GIG/gig_daily_report.sh" || { echo 'daily report bypasses durable outbox'; exit 1; }
test ! -e "$HOURLY" || { echo 'duplicate hourly report must stay removed; pass hook is per-wake'; exit 1; }
test -f "$WEEKLY" || { echo 'weekly Telegram report LaunchAgent missing'; exit 1; }
plutil -lint "$WEEKLY" >/dev/null
test "$(plutil -extract Label raw -o - "$WEEKLY")" = 'ai.anicca.hf-gig-weekly-report'
test "$(plutil -extract StartCalendarInterval.Weekday raw -o - "$WEEKLY")" = '1'
test "$(plutil -extract StartCalendarInterval.Hour raw -o - "$WEEKLY")" = '9'
test "$(plutil -extract StartCalendarInterval.Minute raw -o - "$WEEKLY")" = '12'
grep -q 'scripts/telegram_report.py.*weekly' "$GIG/gig_weekly_report.sh"
! grep -q 'openclaw message send' "$GIG/gig_weekly_report.sh" || { echo 'weekly report bypasses durable outbox'; exit 1; }
grep -Fq 'REPLY_LANE_RC=$?' "$GIG/gig_pass.sh"
grep -Fq '0|2)' "$GIG/gig_pass.sh" || {
  echo 'full pass drops verified Telegram events when another reply needs reconcile'; exit 1;
}
! grep -q 'ai.anicca.hf-gig-hourly-report.plist' "$README" || { echo 'README resurrects duplicate hourly unit'; exit 1; }
grep -q 'cp skills/gig-work/launchd/ai.anicca.hf-gig-weekly-report.plist' "$README"
grep -q 'launchctl bootstrap.*ai.anicca.hf-gig-weekly-report.plist' "$README"
echo 'PASS: per-wake, daily, and weekly reports use the durable Telegram publisher'
