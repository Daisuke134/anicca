#!/usr/bin/env bash
# One-shot human-assisted DistroKid login.
# Run this manually ONCE on the Mac Mini before enabling the cron.
# Opens a real Chrome window via playwright-cli in headed mode.
# You log in (including 2FA if any). The named session "distrokid" persists
# its storage state for subsequent headless cron runs.
#
# Usage:
#   bash ~/.openclaw/skills/anicca-music-factory/scripts/setup-login.sh

set -euo pipefail

echo "================================================================"
echo "  Opening DistroKid signin in playwright-cli session 'distrokid'"
echo "  Session storage will persist for the cron to reuse."
echo "================================================================"
echo ""
echo "  → Log in fully (including 2FA if asked)."
echo "  → When you see your dashboard, this session is ready."
echo "  → Then run: bash scripts/dry-run.sh  to test upload."
echo ""

PROFILE_DIR="$HOME/.openclaw/playwright-cli/distrokid-profile"
mkdir -p "$PROFILE_DIR"
echo "  → persistent profile dir: $PROFILE_DIR"
playwright-cli -s=distrokid open https://distrokid.com/signin/ --headed --persistent --profile="$PROFILE_DIR"
