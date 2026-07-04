#!/usr/bin/env bash
# test-loop.sh — anti-fake behavioral tests. Seams only; NO live cred, NO real prod file touched.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; LOOP="$HERE/loop.sh"; PASS=0; FAIL=0
# run <cap_acct> <cap_payout> <cap_trend> <lm_subs> <log_age_days | "none">
run(){ local T; T="$(mktemp -d)"; local F="$T/fx" S="$T/state" LOG="$T/daily_loop.log" RQ="$T/req.json"; mkdir -p "$F" "$S"
  printf '%s' "$1">"$F/cap_acct.json"; printf '%s' "$2">"$F/cap_payout.json"; printf '%s' "$3">"$F/cap_trend.json"; printf '%s' "$4">"$F/lm_subs.json"
  local age="${5:-0}"
  if [ "$age" = "none" ]; then LOG="$T/absent.log"; else touch "$LOG"; [ "$age" -gt 0 ] && touch -t "$(date -v-${age}d +%Y%m%d%H%M 2>/dev/null || date -d "-${age} days" +%Y%m%d%H%M)" "$LOG"; fi
  LMCAP_TEST=1 LMCAP_FIXTURE="$F" LMCAP_DIR="$T" LMCAP_LOGFILE="$LOG" LMCAP_REQ="$RQ" STRIPE_SECRET_KEY="sk_live_test" bash "$LOOP" >/dev/null 2>&1
  echo "REQEXISTS=$([ -f "$RQ" ] && echo yes || echo no)"; cat "$S/STATE.md"; rm -rf "$T"; }
a(){ if echo "$2" | grep -qE "$3"; then echo "  ok $1"; PASS=$((PASS+1)); else echo "  FAIL $1 (want /$3/)"; FAIL=$((FAIL+1)); fi; }
ACC='{"code":0,"data":{"email":"x"}}'; PAY0='{"code":0,"data":[{"amount":0.0,"payoutMonth":"2026-06"}]}'
T0='{"code":0,"data":{"data":[{"netRevenue":0}]}}'; SUBS0='{"object":"list","data":[]}'
SUB20='{"object":"list","data":[{"items":{"data":[{"quantity":1,"price":{"unit_amount":2000,"recurring":{"interval":"month"}}}]}}]}'
PAYMULTI='{"code":0,"data":[{"amount":50.0,"payoutMonth":"2026-05"},{"amount":0.0,"payoutMonth":"2026-06"}]}'

echo "A: Capafy payout ERROR -> monthly NA not 0"; O="$(run "$ACC" '{"code":401}' "$T0" "$SUBS0" 0)"; a "payout-err-NA" "$O" '^capafy_monthly_payout_usd: NA'
echo "B: Stripe ERROR -> lm_mrr NA + READ-FAILED"; O="$(run "$ACC" "$PAY0" "$T0" '{"error":{"message":"bad"}}' 0)"; a "stripe-err-NA" "$O" '^lm_mrr_usd: NA'; a "READ-FAILED" "$O" '^status: READ-FAILED'
echo "C: real 20/mo sub -> 20.0 (dollars, live shape)"; O="$(run "$ACC" "$PAY0" "$T0" "$SUB20" 0)"; a "real-20" "$O" '^lm_mrr_usd: 20.0'; a "EARNING" "$O" '^status: EARNING'
echo "D: true 0 -> 0.0 + NO revenue"; O="$(run "$ACC" "$PAY0" "$T0" "$SUBS0" 0)"; a "monthly-0" "$O" '^monthly_revenue_usd: 0.0'; a "NO-rev" "$O" '^status: NO realised'
echo "E: STALE log (5d) -> HEAL + selfheal-request"; O="$(run "$ACC" "$PAY0" "$T0" "$SUBS0" 5)"; a "stale-heal" "$O" 'CAPAFY-LOOP-STALE'; a "req-written" "$O" '^REQEXISTS=yes'
echo "F: healthy -> NO selfheal-request"; O="$(run "$ACC" "$PAY0" "$T0" "$SUBS0" 0)"; a "no-req" "$O" '^REQEXISTS=no'
echo "G: multi payout (old 50 + recent 0) -> picks LATEST 0.0 not max 50 (FIND-015)"; O="$(run "$ACC" "$PAYMULTI" "$T0" "$SUBS0" 0)"; a "latest-not-max" "$O" '^capafy_monthly_payout_usd: 0.0'
echo "H: log MISSING -> CAPAFY-LOOP-NEVER-RAN (FIND-016)"; O="$(run "$ACC" "$PAY0" "$T0" "$SUBS0" none)"; a "never-ran" "$O" 'CAPAFY-LOOP-NEVER-RAN'

echo ""; echo "=== $PASS passed, $FAIL failed ==="; [ "$FAIL" = 0 ] && echo ALL_GREEN || exit 1
