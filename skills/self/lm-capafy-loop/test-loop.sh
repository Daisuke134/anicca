#!/usr/bin/env bash
# test-loop.sh — behavioral tests for the anti-fake invariants (FIND-004). Uses the LMCAP_TEST fixture
# seam so NO live credential is touched. Asserts the VALUE lines (the anti-fake core), not just status.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOOP="$HERE/loop.sh"; PASS=0; FAIL=0
run(){ # <fixture-json-for-cap_acct> <cap_trend> <lm_subs> <codes...>
  local T; T="$(mktemp -d)"; local F="$T/fx"; local S="$T/state"; mkdir -p "$F" "$S"
  printf '%s' "$1" > "$F/cap_acct.json"; echo 200 > "$F/cap_acct.code"
  printf '%s' "$2" > "$F/cap_trend.json"; echo 200 > "$F/cap_trend.code"
  printf '%s' "$3" > "$F/lm_subs.json";  echo 200 > "$F/lm_subs.code"
  # fresh fake capafy loop log so the staleness heal doesn't fire
  mkdir -p "$HOME/.openclaw/skills/capafy-autopublish/state"; touch "$HOME/.openclaw/skills/capafy-autopublish/state/daily_loop.log"
  LMCAP_TEST=1 LMCAP_FIXTURE="$F" LMCAP_DIR="$T" STRIPE_SECRET_KEY="sk_live_test" bash "$LOOP" >/dev/null 2>&1
  cat "$S/STATE.md"; rm -rf "$T"
}
assert(){ local label="$1" got="$2" want="$3"; if echo "$got" | grep -qE "$want"; then echo "  ✓ $label"; PASS=$((PASS+1)); else echo "  ✗ $label — wanted /$want/, got: $(echo "$got"|tr '\n' '|')"; FAIL=$((FAIL+1)); fi; }

OK='{"code":0,"data":{"email":"x"}}'
echo "TEST A: Capafy sales API ERROR (code 401) → capafy rev = NA, NOT masked as 0 (FIND-002)"
OUT="$(run "$OK" '{"code":401,"msg":"expired"}' '{"object":"list","data":[]}')"
assert "capafy error → NA" "$OUT" '^capafy_net_revenue_usd_3d: NA'

echo "TEST B: Stripe API ERROR body → lm_mrr = NA + status READ-FAILED, NOT \$0 (FIND-002/003)"
OUT="$(run "$OK" '{"code":0,"data":{"data":[{"netRevenue":0}]}}' '{"error":{"message":"bad key"}}')"
assert "stripe error → NA" "$OUT" '^lm_mrr_usd: NA'
assert "NA → READ-FAILED status" "$OUT" '^status: READ-FAILED'

echo "TEST C: real \$20/mo sub → lm_mrr = 20.0 (DOLLARS not count) (FIND-001)"
OUT="$(run "$OK" '{"code":0,"data":{"data":[{"netRevenue":0}]}}' '{"object":"list","data":[{"items":{"data":[{"quantity":1,"price":{"unit_amount":2000,"recurring":{"interval":"month"}}}]}}]}')"
assert "real \$20 sub → 20.0" "$OUT" '^lm_mrr_usd: 20.0'
assert "earning status" "$OUT" '^status: EARNING'

echo "TEST D: healthy but genuinely \$0 → honest 0.0 + NO-revenue status (true zero is fine)"
OUT="$(run "$OK" '{"code":0,"data":{"data":[{"netRevenue":0},{"netRevenue":0}]}}' '{"object":"list","data":[]}')"
assert "true zero capafy → 0.0" "$OUT" '^capafy_net_revenue_usd_3d: 0.0'
assert "0 → NO revenue status" "$OUT" '^status: NO realised revenue'

echo ""
echo "=== RESULT: $PASS passed, $FAIL failed ==="
[ "$FAIL" = 0 ] && echo "ALL GREEN" || exit 1
