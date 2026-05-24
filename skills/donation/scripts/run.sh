#!/usr/bin/env bash
# DEPRECATED — donation skill rewritten to v1 (Stripe Connect rail).
# This shim now invokes the new Python pipeline so any cron payload still
# pointing at run.sh keeps working during the transition.
#
# v1 entrypoints:
#   python3 ~/.openclaw/skills/donation/scripts/compute-revenue.py
#   python3 ~/.openclaw/skills/donation/scripts/transfer.py
#   python3 ~/.openclaw/skills/donation/scripts/pdf-receipt.py
#   python3 ~/.openclaw/skills/donation/scripts/public-tweet.py
#
# The agent-{{profile.lateness.stakeholders.channel}}-driven v2 lives at ~/.openclaw/skills/donation-v2-archive/.

set -uo pipefail

SKILL=~/.openclaw/skills/donation
MODE="${MODE:-monthly}"

echo "⚠️  donation/scripts/run.sh is a deprecation shim. Use the Python entrypoints directly."
echo "    Forwarding MODE=$MODE to the v1 monthly chain in DRY_RUN=${DONATION_DRY_RUN:-true}..."

case "$MODE" in
  monthly)
    python3 "$SKILL/scripts/compute-revenue.py" || exit $?
    python3 "$SKILL/scripts/transfer.py"        || exit $?
    python3 "$SKILL/scripts/pdf-receipt.py"     || exit $?
    python3 "$SKILL/scripts/public-tweet.py"    || exit $?
    ;;
  install)
    echo "❌ MODE=install no longer exists in v1. Charity onboarding is manual; see SKILL.md."
    exit 2
    ;;
  *)
    echo "❌ unknown MODE='$MODE'  (expected: monthly)" >&2
    exit 2
    ;;
esac
