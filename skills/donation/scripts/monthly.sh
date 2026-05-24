#!/usr/bin/env bash
# DEPRECATED — donation v1 monthly run is now a Python pipeline. This shim
# forwards to the new entrypoints so any cron still pointing at monthly.sh
# keeps working during the transition.

set -uo pipefail

SKILL=~/.openclaw/skills/donation
echo "⚠️  donation/scripts/monthly.sh is a deprecation shim → forwarding to Python v1 chain."

python3 "$SKILL/scripts/compute-revenue.py" || exit $?
python3 "$SKILL/scripts/transfer.py"        || exit $?
python3 "$SKILL/scripts/pdf-receipt.py"     || exit $?
python3 "$SKILL/scripts/public-tweet.py"    || exit $?
