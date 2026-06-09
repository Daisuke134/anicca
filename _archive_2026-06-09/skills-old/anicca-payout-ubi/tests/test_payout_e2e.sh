#!/usr/bin/env bash
# E2E for anicca-payout-ubi. Dry-run + live-validation only (NO broadcast).
# Wallet=100, runtime/mo=10 → reserve=30 → distributable=70 → 10% = 7.00 USDC.
# Asserts: (1) dry-run math, (2) confirm-without-live refused, (3) live mode REQUIRES
# allow_live:true AND label != "PLACEHOLDER" — placeholder fixture must fail closed,
# (4) ANICCA_PAYOUT_TEST=1 toggles guard-absent OK path; without it, missing guard → blocked.
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
RUN="$SKILL/scripts/payout-ubi.sh"
STATE=/Users/anicca/.hermes/state/payout.jsonl
mkdir -p /Users/anicca/.hermes/state
BEFORE=$(wc -l < "$STATE" 2>/dev/null || echo 0)

CFO="$SKILL/tests/fixtures/anicca-cfo.synthetic.json"
RECIP="$SKILL/tests/fixtures/ubi-recipients.synthetic.json"          # allow_live:true, label "test-sink"
PLACEHOLDER="$SKILL/tests/fixtures/ubi-recipients.placeholder.json"  # allow_live:false, label "PLACEHOLDER"

# --- Case 1: dry-run (default) — ANICCA_PAYOUT_TEST=1 allows guard-absent OK ---
OUT=$(ANICCA_PAYOUT_TEST=1 \
      ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
      ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$RECIP" \
      "$RUN" --dry-run)
RC=$?
echo "[case1 dry-run] rc=$RC out=$OUT"
[ $RC -eq 0 ] || { echo "FAIL: dry-run expected rc=0 got $RC"; exit 1; }
echo "$OUT" | /usr/bin/jq -e '.action == "dry-run"' >/dev/null \
  || { echo "FAIL: expected action=dry-run"; exit 1; }
echo "$OUT" | /usr/bin/jq -e '.would_send_usd == 7.00 or .would_send_usd == 7' >/dev/null \
  || { echo "FAIL: expected would_send_usd=7.00 (got $(echo "$OUT" | /usr/bin/jq -c .))"; exit 1; }
echo "$OUT" | /usr/bin/jq -e '.recipients | length == 1' >/dev/null \
  || { echo "FAIL: expected 1 recipient row"; exit 1; }
echo "$OUT" | /usr/bin/jq -e '.recipients[0].address == "0x000000000000000000000000000000000ABCDEF1"' >/dev/null \
  || { echo "FAIL: recipient address mismatch"; exit 1; }
echo "$OUT" | /usr/bin/jq -e '(.recipients[0].amount_usd == 7.00) or (.recipients[0].amount_usd == 7)' >/dev/null \
  || { echo "FAIL: recipient amount_usd != 7.00"; exit 1; }

# --- Case 2: --confirm WITHOUT ANICCA_PAYOUT_LIVE=1 → refused-no-live-env ---
OUT2=$(ANICCA_PAYOUT_TEST=1 \
       ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
       ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$RECIP" \
       "$RUN" --confirm)
RC2=$?
echo "[case2 confirm-without-live] rc=$RC2 out=$OUT2"
[ $RC2 -eq 0 ] || { echo "FAIL: confirm-without-live expected rc=0 got $RC2"; exit 1; }
echo "$OUT2" | /usr/bin/jq -e '.action == "refused-no-live-env"' >/dev/null \
  || { echo "FAIL: confirm-without-live expected action=refused-no-live-env"; exit 1; }

# --- Case 3: LIVE env + confirm + PLACEHOLDER recipient → MUST fail closed (no broadcast) ---
# Codex P4-burn-address-live-risk: even with ANICCA_PAYOUT_LIVE=1, the PLACEHOLDER
# fixture (allow_live:false, label="PLACEHOLDER") MUST exit non-zero with the
# live-recipient-validation-failed action.
OUT3=$(ANICCA_PAYOUT_TEST=1 \
       ANICCA_PAYOUT_LIVE=1 \
       ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
       ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$PLACEHOLDER" \
       "$RUN" --confirm) || RC3=$?
RC3="${RC3:-0}"
echo "[case3 placeholder-in-live] rc=$RC3 out=$OUT3"
[ "$RC3" -ne 0 ] || { echo "FAIL: placeholder-in-live expected non-zero rc, got $RC3"; exit 1; }
echo "$OUT3" | /usr/bin/jq -e '.action == "live-recipient-validation-failed"' >/dev/null \
  || { echo "FAIL: placeholder-in-live expected action=live-recipient-validation-failed"; exit 1; }
echo "$OUT3" | /usr/bin/jq -e '.reason | test("PLACEHOLDER|allow_live")' >/dev/null \
  || { echo "FAIL: placeholder-in-live expected reason mentioning PLACEHOLDER or allow_live"; exit 1; }
echo "$OUT3" | /usr/bin/jq -e '.sent == null or (.sent | length == 0)' >/dev/null \
  || { echo "FAIL: placeholder-in-live MUST NOT report any sent rows"; exit 1; }

# --- Case 4: ANICCA_PAYOUT_TEST unset + guard symlink absent → blocked-by-guard (fail closed) ---
# Codex P4-guard-bypass-ok: production must fail closed when guard is missing.
GUARD_LINK=/Users/anicca/.hermes/skills/anicca-constitution-guard
GUARD_BAK=""
if [ -L "$GUARD_LINK" ] || [ -e "$GUARD_LINK" ]; then
  GUARD_BAK="${GUARD_LINK}.test-bak.$$"
  mv "$GUARD_LINK" "$GUARD_BAK"
fi
unset ANICCA_PAYOUT_TEST
OUT4=$(ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
       ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$RECIP" \
       "$RUN" --dry-run) || RC4=$?
RC4="${RC4:-0}"
[ -n "$GUARD_BAK" ] && mv "$GUARD_BAK" "$GUARD_LINK"  # restore
echo "[case4 guard-absent-prod] rc=$RC4 out=$OUT4"
[ "$RC4" -ne 0 ] || { echo "FAIL: guard-absent-prod expected non-zero rc, got $RC4"; exit 1; }
echo "$OUT4" | /usr/bin/jq -e '.action == "blocked-by-guard"' >/dev/null \
  || { echo "FAIL: guard-absent-prod expected action=blocked-by-guard"; exit 1; }
echo "$OUT4" | /usr/bin/jq -e '.reason | test("guard_not_installed")' >/dev/null \
  || { echo "FAIL: guard-absent-prod expected reason=guard_not_installed"; exit 1; }

# State log delta: cases 1, 2, 3, 4 each MUST have appended one line.
AFTER=$(wc -l < "$STATE")
DELTA=$((AFTER - BEFORE))
[ $DELTA -ge 4 ] || { echo "FAIL: expected ≥4 new payout rows, got $DELTA"; exit 1; }

LAST=$(tail -n 1 "$STATE")
for k in ts action; do
  echo "$LAST" | /usr/bin/jq -e ".$k" >/dev/null \
    || { echo "FAIL: payout row missing $k: $LAST"; exit 1; }
done

echo "PASS"
