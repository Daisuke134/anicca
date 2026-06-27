#!/usr/bin/env bash
# VSDD oracle for akt-treasury.sh. STATIC invariants + BEHAVIORAL runs against a fake `akash` CLI that models the REAL
# settlement: an EXECUTED mint makes uact RISE (post-mint balance > pre-mint); a CANCELED mint (below min_mint) refunds
# so uact never rises. Proves: mints only below buffer, confirms via the uact balance DELTA (not tx code, not a stale
# ledger record), fails LOUD on a non-crediting mint, never touches the deploy path. Exit 0=PASS.
set -uo pipefail
D="/Users/operator/anicca/skills/self/spawn/scripts"; S="$D/akt-treasury.sh"
src="$(sed 's/#.*//' "$S")"; fails=0
have(){   grep -qE "$1" <<<"$src" || { echo "  - FAIL missing [$1] — $2"; fails=$((fails+1)); }; }
absent(){ grep -qE "$1" <<<"$src" && { echo "  - FAIL present [$1] — $2"; fails=$((fails+1)); }; true; }
ok(){     [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC ----------
have   "tx bme mint-act"                 "mints ACT from AKT"
have   "MIN_MINT|min_mint"               "min_mint awareness (chunk must clear it)"
have   "NEW_UACT|CUR_UACT"               "confirms the mint via the uact balance DELTA (robust, not a stale ledger record)"
have   "EXECUTED"                        "confirms success when uact rises"
have   "CANCELED"                        "warns when uact never rises (below min_mint)"
absent "deployment create|send-manifest" "OFF the deploy path (no per-spawn deploy here)"
have   "ACT_BUFFER"                      "only tops up when below buffer"
have   "exit 1"                          "fail-closed/loud"

# ---------- BEHAVIORAL: fake akash CLI (uact rises after mint iff executed) ----------
mkfake(){ cat <<FAKE
#!/usr/bin/env bash
echo "\$*" >> "\$T_REC"
M="${1}"
case "\$*" in
  *"keys show"*)        echo "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523" ;;
  *"tx bme mint-act"*)  touch "\$T_MARK"; echo '{"code":0}' ;;
  *"query bank balances"*)
    case "\$M" in
      enough) echo '{"balances":[{"denom":"uact","amount":"30000000"},{"denom":"uakt","amount":"75000000"}]}' ;;
      lowakt) echo '{"balances":[{"denom":"uact","amount":"0"},{"denom":"uakt","amount":"5000000"}]}' ;;
      executed) [ -f "\$T_MARK" ] && echo '{"balances":[{"denom":"uact","amount":"16000000"},{"denom":"uakt","amount":"50000000"}]}' \
                                   || echo '{"balances":[{"denom":"uact","amount":"0"},{"denom":"uakt","amount":"75000000"}]}' ;;
      *)      echo '{"balances":[{"denom":"uact","amount":"0"},{"denom":"uakt","amount":"75000000"}]}' ;;
    esac ;;
  *) echo '{}' ;;
esac
FAKE
}
runfake(){ local T; T="$(mktemp -d)"; REC="$T/rec"; : >"$REC"
  mkfake "$1" >"$T/akash"; chmod +x "$T/akash"
  OUT="$(AKASH_CLI="$T/akash" T_REC="$REC" T_MARK="$T/mark" AKASH_KEY_NAME=anicca-akash AKASH_NODE="http://x" \
         AKASH_CHAIN_ID="t" AKASH_KEYRING_BACKEND=test AKASH_POLL_SLEEP=0 TREASURY_MINT_TRIES=3 bash "$S" 2>"$T/err")"; rc=$?
  recd="$(cat "$REC")"; rm -rf "$T"; }

runfake enough
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "enough: exit $rc (want 0)"
grep -q "mint-act" <<<"$recd" && { echo "  - FAIL enough: minted despite ACT ≥ buffer"; fails=$((fails+1)); }; true

runfake executed
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "executed: exit $rc (want 0 — uact rose after mint)"
grep -q "mint-act" <<<"$recd" || { echo "  - FAIL executed: never minted"; fails=$((fails+1)); }

runfake canceled
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "canceled: exit $rc (want !=0 — uact never rose = below min_mint)"

runfake lowakt
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "lowakt: exit $rc (want !=0 — insufficient AKT, no swap wired)"
grep -q "mint-act" <<<"$recd" && { echo "  - FAIL lowakt: minted with insufficient AKT"; fails=$((fails+1)); }; true

[ $fails -eq 0 ] && { echo "PASS — akt-treasury invariants hold (static + balance-delta behavioral)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
