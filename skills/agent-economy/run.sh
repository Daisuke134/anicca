#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd -P)"
ANICCA_HOME="${ANICCA_HOME:?ANICCA_HOME is required}"
LEDGER="${EARN_LEDGER:-$ANICCA_HOME/skills/earn/state/earn-ledger.jsonl}"
CORRECTIONS="${RECEIPT_CORRECTIONS:-$ANICCA_HOME/skills/earn/state/receipt-reconciliations.jsonl}"

exec /usr/bin/env node "$HERE/reconcile-receipts.mjs" "$LEDGER" "$CORRECTIONS"

