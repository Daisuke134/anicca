#!/usr/bin/env bash
# donation — dispatch on $MODE
#   MODE=install   → one-shot: discover charity, register, save card, first donation, seed ledger
#   MODE=monthly   → recurring: donate 1% of MRR via saved payment, update ledger, push to anicca-products

set -uo pipefail

SKILL=~/.openclaw/skills/donation
MODE="${MODE:?MODE must be 'install' or 'monthly'}"

case "$MODE" in
  install) exec bash "$SKILL/scripts/install.sh" "$@" ;;
  monthly) exec bash "$SKILL/scripts/monthly.sh" "$@" ;;
  *) echo "❌ unknown MODE='$MODE' (expected: install | monthly)" >&2; exit 2 ;;
esac
