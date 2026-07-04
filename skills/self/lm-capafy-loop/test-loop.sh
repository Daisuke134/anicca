#!/usr/bin/env bash
# test-loop.sh — anti-fake behavioral tests. Uses seams so NO live cred and NO real prod file is touched
# (FIND-011: LMCAP_LOGFILE + LMCAP_REQ are temp; the real daily_loop.log is never touched).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; LOOP="$HERE/loop.sh"; PASS=0; FAIL=0
# run <cap_acct> <cap_payout> <cap_trend> <lm_subs> <log_age_days>
run(){ local T; T="$(mktemp -d)"; local F="$T/fx" S="$T/state" LOG="$T/daily_loop.log" RQ="$T/req.json"; mkdir -p "$F" "$S"
  printf '%s' "$1">"$F/cap_acct.json"; printf '%s' "$2">"$F/cap_payout.json"; printf '%s' "$3">"$F/cap_trend.json"; printf '%s' "$4">"$F/lm_subs.json"
  touch "$LOG"; [ "${5:-0}" -gt 0 ] && touch -t "$(date -v-${5}d +%Y%m%d%H%M 2>/dev/null || date -d "-${5} days" +%Y%m%d%H%M)" "$LOG"
  LMCAP_TEST=1 LMCAP_FIXTURE="$F" LMCAP_DIR="$T" LMCAP_LOGFILE="$LOG" LMCAP_REQ="$RQ" STRIPE_SECRET_KEY="sk_live_test" bash "$LOOP" >/dev/null 2>&1
  echo "REQEXISTS=$([ -f "$RQ" ] && echo yes || echo no)"; cat "$S/STATE.md"; rm -rf "$T"; }
a(){ if echo "$2"|grep -qE "$3"; then echo "  ✓ $1"; PASS=$((PASS+1)); else echo "  ✗ $1 — want /$3/, got:$(echo "$2"|grep -E "$4"|head -1)"; FAIL=$((FAIL+1)); fi; }
ACC='{"code":0,"data":{"email":"x"}}'; PAY0='{"code":0,"data":[{"amount":0.0,"payoutMonth":"2026-06"}]}'; T0='{"code":0,"data":{"data":[{"netRevenue":0}]}}'; SUBS0='{"object":"list","data":[]}'

echo "A: Capafy payout ERROR → capafy_monthly NA not 0 (FIND-002)"; O="$(run "$ACC" '{"code":401}' "$T0" "$SUBS0" 0)"; a "payout err→NA" "$O" '^capafy_monthly_payout_usd: NA' 'capafy_monthly'
echo "B: Stripe ERROR → lm_mrr NA + READ-FAILED (FIND-002/003)"; O="$(run "$ACC" "$PAY0" "$T0" '{"error":{"message":"bad"}}' 0)"; a "stripe err→NA" "$O" '^lm_mrr_usd: NA' 'lm_mrr'; a "→READ-FAILED" "$O" '^status: READ-FAILED' 'status'
echo "C: real \$20/mo sub (live shape items.data.price.unit_amount) → 20.0 (FIND-001/013)"; O="$(run "$ACC" "$PAY0" "$T0" '{"object":"list","data":[{"items":{"data":[{"quantity":1,"price":{"unit_amount":2000,"recurring":{"interval":"month"}}}]}}]}' 0)"; a "real \$20→20.0" "$O" '^lm_mrr_usd: 20.0' 'lm_mrr'; a "→EARNING" "$O" '^status: EARNING' 'status'
echo "D: true \$0 → 0.0 + NO revenue"; O="$(run "$ACC" "$PAY0" "$T0" "$SUBS0" 0)"; a "monthly 0.0" "$O" '^monthly_revenue_usd: 0.0' 'monthly_revenue'; a "→NO revenue" "$O" '^status: NO realised' 'status'
echo "E: STALE publish log (5d) → HEAL CAPAFY-LOOP-STALE (FIND-008/011, freshness tested, real log untouched)"; O="$(run "$ACC" "$PAY0" "$T0" "$SUBS0" 5)"; a "stale→heal" "$O" 'CAPAFY-LOOP-STALE' 'heal_first'; a "→selfheal-request written" "$O" '^REQEXISTS=yes' 'REQEXISTS'
echo "F: healthy → NO selfheal-request"; O="$(run "$ACC" "$PAY0" "$T0" "$SUBS0" 0)"; a "healthy→no req" "$O" '^REQEXISTS=no' 'REQEXISTS'

echo ""; echo "=== $PASS passed, $FAIL failed ==="; [ "$FAIL" = 0 ] && echo ALL_GREEN || exit 1
