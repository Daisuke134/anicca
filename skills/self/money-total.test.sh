#!/usr/bin/env bash
set -uo pipefail; P=0; F=0; H="$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)"; A="$H/money-total.sh"
mk(){ local d; d="$(mktemp -d)"; printf 'capafy_monthly_payout_usd: %s\n' "$1">"$d/cap"; printf 'lm_mrr_usd: %s\n' "$2">"$d/lm"; echo "$d"; }
run(){ local d; d="$(mk "$1" "$2")"; MT_CAPAFY_STATE="$d/cap" MT_LM_STATE="$d/lm" MT_SPEND="${3:-200}" bash "$A"; rm -rf "$d"; }
a(){ echo "$2"|grep -qE "$3"&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 /$3/"; F=$((F+1)); }; }
a "both 0 → 0/DEMAND" "$(run 0.0 0.0)" 'monthly_revenue_total_usd: 0.0'
a "0 → DEMAND verdict" "$(run 0.0 0.0)" 'bottleneck = DEMAND'
a "20+30 → 50.0" "$(run 20.0 30.0)" 'monthly_revenue_total_usd: 50.0'
a "250 ≥ 200 → SUCCESS" "$(run 100.0 150.0)" 'verdict: SUCCESS'
a "NA loop → total NA (not masked)" "$(run NA 20.0)" 'monthly_revenue_total_usd: NA'
a "NA → UNTRUSTWORTHY" "$(run NA 20.0)" 'verdict: UNTRUSTWORTHY'
echo "=== $P passed $F failed ==="; [ "$F" = 0 ]&&echo GREEN||exit 1
