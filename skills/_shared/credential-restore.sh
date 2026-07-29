#!/usr/bin/env bash
# credential-restore.sh — REQ-H3c camofox + Gmail OTP auto-login (sprint-2).
# ENV VAR pattern; no human-touch surfaces.
#
# Usage: credential-restore.sh <slot> <oauth_url>
set -uo pipefail

export ANICCA_SLOT="${1:-}"
export ANICCA_OAUTH_URL="${2:-}"
LOG="${HOME}/.openclaw/logs/${ANICCA_SLOT}-credential-restore.log"
mkdir -p "$(dirname "$LOG")"

# Sprint-2 cycle 2 wires the real 8-step camofox + Gmail OTP flow:
#  (i) launch camofox with ~/.cloak/profiles/anicca-login
#  (ii) navigate to $ANICCA_OAUTH_URL
#  (iii) fill GOOGLE_LOGIN_EMAIL + GOOGLE_LOGIN_PASSWORD from $HOME/.local/state/life-manager/.env
#  (iv) read OTP via gog gmail (subject contains "Claude"|"Anthropic")
#  (v) capture redirected callback URL with code=...
#  (vi) tmux send-keys "$code" Enter into slot pane
#  (vii) verify "Logged in as <email>" in pane
#  (viii) <slot>-cli.sh --restart
#
# Sprint-1 of this feature ships the SCAFFOLD: log the attempt + return non-zero so
# the caller (health-check.py dispatch) routes to bot2bot.sh post opinion-requested.
echo "$(date '+%F %T') credential-restore: scaffold (sprint-2 cycle 2 wires real flow)" >> "$LOG"
exit 1  # scaffold returns failure → bot2bot escalation
