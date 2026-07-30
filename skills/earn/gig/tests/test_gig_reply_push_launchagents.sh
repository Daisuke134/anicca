#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
RECEIVER="$ROOT/skills/earn/gig/launchd/ai.anicca.hf-gig-reply-push.plist"
WATCH="$ROOT/skills/earn/gig/launchd/ai.anicca.hf-gig-gmail-watch.plist"

for plist in "$RECEIVER" "$WATCH"; do
  test -f "$plist" || { echo "missing LaunchAgent: $plist"; exit 1; }
  plutil -lint "$plist" >/dev/null
  test "$(plutil -extract RunAtLoad raw -o - "$plist")" = 'true'
  test "$(plutil -extract KeepAlive raw -o - "$plist")" = 'true'
done
test "$(plutil -extract Label raw -o - "$RECEIVER")" = 'ai.anicca.hf-gig-reply-push'
grep -q '/skills/earn/gig/scripts/reply_push_server.py' "$RECEIVER"
test "$(plutil -extract Label raw -o - "$WATCH")" = 'ai.anicca.hf-gig-gmail-watch'
grep -q '/skills/earn/gig/scripts/run_gig_gmail_watch.sh' "$WATCH"
! grep -q -- '--include-body' "$ROOT/skills/earn/gig/scripts/run_gig_gmail_watch.sh"
! grep -q 'agent_runner\|gig_pass.sh' "$RECEIVER" || { echo 'push receiver invokes model/full pass directly'; exit 1; }
echo 'PASS: Gmail push receiver and watch are persistent model-free services'
