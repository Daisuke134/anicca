#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd -P)"
ANICCA_HOME="${ANICCA_HOME:?ANICCA_HOME is required}"
LEDGER="${EARN_LEDGER:-$ANICCA_HOME/skills/earn/state/earn-ledger.jsonl}"
CORRECTIONS="${RECEIPT_CORRECTIONS:-$ANICCA_HOME/skills/earn/state/receipt-reconciliations.jsonl}"
CANDIDATE_INBOX="${REVENUE_RECEIPT_INBOX:-$ANICCA_HOME/skills/earn/state/revenue-receipts.inbox.jsonl}"
REVENUE_JOURNAL="${REVENUE_RECEIPT_JOURNAL:-$ANICCA_HOME/skills/earn/state/revenue-receipts.jsonl}"
COMPUTE_COST_LOG="${COMPUTE_COST_LOG:-$HOME/.blockrun/cost_log.jsonl}"
SHELTER_COST_LEDGER="${SHELTER_COST_LEDGER:-$HOME/.hermes/state/shelter-cost.jsonl}"

/usr/bin/env node "$HERE/reconcile-receipts.mjs" "$LEDGER" "$CORRECTIONS" "$CANDIDATE_INBOX" "$REVENUE_JOURNAL" >/dev/null
exec /usr/bin/env node "$HERE/status.mjs" "$LEDGER" "$CORRECTIONS" "$COMPUTE_COST_LOG" "$SHELTER_COST_LEDGER" "$REVENUE_JOURNAL"
