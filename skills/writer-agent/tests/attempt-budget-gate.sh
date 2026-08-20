#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$ROOT/scripts/attempt-budget-gate.sh"

continue_json="$(bash "$GATE" --started-at 1000 --now 1100 --revise-attempts 6 --reader-attempts 6)"
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["verdict"] == "CONTINUE"; assert d["limits"]["revise_attempts"] == 6; assert d["limits"]["reader_attempts"] == 6' "$continue_json"

set +e
carry_json="$(ARTICLE_MID_BUDGET_USD=99 ARTICLE_MID_MAX_REVISE_ATTEMPTS=999 bash "$GATE" --started-at 1000 --now 1100 --revise-attempts 7 --reader-attempts 7)"
carry_rc=$?
set -e
[ "$carry_rc" -eq 1 ]
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["verdict"] == "STOP_SPENDING"; assert d["token_budget_usd"] == 4; assert len(d["reasons"]) == 2' "$carry_json"

printf 'MAX_ALLOWED_CASE=%s\nSTOP_SPENDING_RC=%s\nHARD_CAP_CASE=%s\n' "$continue_json" "$carry_rc" "$carry_json"
