#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; LOOP="$HERE/loop.sh"; PASS=0; FAIL=0
run(){ local T; T="$(mktemp -d)"; local F="$T/fx" S="$T/state" LOG="$T/dl.log" RQ="$T/req.json"; mkdir -p "$F" "$S"
  printf '%s' "$1">"$F/cap_acct.json"; printf '%s' "$2">"$F/cap_payout.json"; printf '%s' "$3">"$F/cap_trend.json"
  local age="${4:-0}"; if [ "$age" = "none" ]; then LOG="$T/absent.log"; else touch "$LOG"; [ "$age" -gt 0 ] && touch -t "$(date -v-${age}d +%Y%m%d%H%M 2>/dev/null||date -d "-${age} days" +%Y%m%d%H%M)" "$LOG"; fi
  CAPAFY_TEST=1 CAPAFY_FIXTURE="$F" CAPAFY_DIR="$T" CAPAFY_LOGFILE="$LOG" CAPAFY_REQ="$T/req.json" bash "$LOOP" >/dev/null 2>&1
  echo "REQ=$([ -f "$T/req.json" ]&&echo yes||echo no)"; cat "$S/STATE.md"; rm -rf "$T"; }
a(){ echo "$2"|grep -qE "$3" && { echo "  ok $1"; PASS=$((PASS+1)); } || { echo "  FAIL $1 (/$3/)"; FAIL=$((FAIL+1)); }; }
ACC='{"code":0,"data":{"email":"x"}}'; P0='{"code":0,"data":[{"amount":0.0,"payoutMonth":"2026-06"}]}'; T0='{"code":0,"data":{"data":[{"netRevenue":0}]}}'
a "payout-err→NA"   "$(run "$ACC" '{"code":401}' "$T0" 0)"                                                   '^capafy_monthly_payout_usd: NA'
a "true-0→0.0"      "$(run "$ACC" "$P0" "$T0" 0)"                                                            '^capafy_monthly_payout_usd: 0.0'
a "multi→latest(0)" "$(run "$ACC" '{"code":0,"data":[{"amount":50,"payoutMonth":"2026-05"},{"amount":0,"payoutMonth":"2026-06"}]}' "$T0" 0)" '^capafy_monthly_payout_usd: 0.0'
a "stale→heal+req"  "$(run "$ACC" "$P0" "$T0" 5)"                                                            'CAPAFY-LOOP-STALE'
a "stale→REQyes"    "$(run "$ACC" "$P0" "$T0" 5)"                                                            '^REQ=yes'
a "never-ran"       "$(run "$ACC" "$P0" "$T0" none)"                                                         'CAPAFY-LOOP-NEVER-RAN'
a "healthy→no-req"  "$(run "$ACC" "$P0" "$T0" 0)"                                                            '^REQ=no'
echo "=== capafy-loop: $PASS passed $FAIL failed ==="; [ "$FAIL" = 0 ] && echo GREEN || exit 1
