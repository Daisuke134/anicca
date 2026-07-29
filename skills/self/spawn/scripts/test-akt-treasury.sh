#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# VSDD oracle for akt-treasury.sh. STATIC invariants + BEHAVIORAL runs against a fake `akash` CLI that models the REAL
# settlement TRAPS the live run exposed:
#  (a) EPOCH DELAY — an executed mint credits uact only AFTER several polls (not instantly); so the poll LOOP must
#      actually iterate (a regression to a single post-mint read would never see the rise → FAIL).
#  (b) STALE LEDGER — the impl must NOT trust `bme ledger records[-1]` (an executed mint leaves it on an older
#      canceled record); fenced by the STATIC `absent "records[-1]"` check below, not a runtime fake branch.
# A CANCELED mint never credits uact. Exit 0=PASS.
set -uo pipefail
D="$LIFE_MANAGER_REPO/skills/self/spawn/scripts"; S="$D/akt-treasury.sh"
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
absent "records\[-1\]"                    "must NOT trust the stale ledger records[-1] (the live-run trap)"
absent "deployment create|send-manifest" "OFF the deploy path (no per-spawn deploy here)"
have   "ACT_BUFFER"                      "only tops up when below buffer"
have   "exit 1"                          "fail-closed/loud"

# ---------- BEHAVIORAL: fake akash CLI (epoch-delayed credit + stale-ledger trap) ----------
mkfake(){ cat <<FAKE
#!/usr/bin/env bash
echo "\$*" >> "\$T_REC"
M="${1}"
case "\$*" in
  *"keys show"*)        echo "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523" ;;
  *"tx bme mint-act"*)  touch "\$T_MARK"; echo '{"code":0}' ;;
  # NOTE: no `bme ledger` branch — the impl must NOT call it (the stale-records[-1] trap is fenced by the STATIC
  # `absent "records\[-1\]"` check above, which greps the comment-stripped impl). A live `bme ledger` call here would
  # be dead code / false coverage.
  *"query bank balances"*)
    case "\$M" in
      enough) echo '{"balances":[{"denom":"uact","amount":"30000000"},{"denom":"uakt","amount":"75000000"}]}' ;;
      lowakt) echo '{"balances":[{"denom":"uact","amount":"0"},{"denom":"uakt","amount":"5000000"}]}' ;;
      executed)
        if [ -f "\$T_MARK" ]; then
          N=\$(( \$(cat "\$T_CNT" 2>/dev/null || echo 0) + 1 )); echo "\$N" > "\$T_CNT"
          # EPOCH DELAY: uact rises only on the 2nd post-mint poll, so the loop must iterate
          if [ "\$N" -ge 2 ]; then echo '{"balances":[{"denom":"uact","amount":"16000000"},{"denom":"uakt","amount":"50000000"}]}'
          else echo '{"balances":[{"denom":"uact","amount":"0"},{"denom":"uakt","amount":"75000000"}]}'; fi
        else echo '{"balances":[{"denom":"uact","amount":"0"},{"denom":"uakt","amount":"75000000"}]}'; fi ;;
      *)      echo '{"balances":[{"denom":"uact","amount":"0"},{"denom":"uakt","amount":"75000000"}]}' ;;
    esac ;;
  *) echo '{}' ;;
esac
FAKE
}
runfake(){ local T; T="$(mktemp -d)"; REC="$T/rec"; : >"$REC"
  mkfake "$1" >"$T/akash"; chmod +x "$T/akash"
  OUT="$(AKASH_CLI="$T/akash" T_REC="$REC" T_MARK="$T/mark" T_CNT="$T/cnt" AKASH_KEY_NAME=anicca-akash AKASH_NODE="http://x" \
         AKASH_CHAIN_ID="t" AKASH_KEYRING_BACKEND=test AKASH_POLL_SLEEP=0 TREASURY_MINT_TRIES=5 bash "$S" 2>"$T/err")"; rc=$?
  recd="$(cat "$REC")"; rm -rf "$T"; }

runfake enough
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "enough: exit $rc (want 0)"
grep -q "mint-act" <<<"$recd" && { echo "  - FAIL enough: minted despite ACT ≥ buffer"; fails=$((fails+1)); }; true

runfake executed
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "executed: exit $rc (want 0 — uact rose on the 2nd poll)"
grep -q "mint-act" <<<"$recd" || { echo "  - FAIL executed: never minted"; fails=$((fails+1)); }
# the loop had to iterate ≥2 times to see the delayed rise (≥3 balance calls: 1 pre-mint + ≥2 polls)
ok "$([ "$(grep -c 'query bank balances' <<<"$recd")" -ge 3 ] && echo 1 || echo 0)" "executed: poll loop iterated for the epoch-delayed credit (>=3 balance reads)"

runfake canceled
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "canceled: exit $rc (want !=0 — uact never rose = below min_mint)"

runfake lowakt
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "lowakt: exit $rc (want !=0 — insufficient AKT, no swap wired)"
grep -q "mint-act" <<<"$recd" && { echo "  - FAIL lowakt: minted with insufficient AKT"; fails=$((fails+1)); }; true

[ $fails -eq 0 ] && { echo "PASS — akt-treasury invariants hold (static + epoch-delay + stale-ledger-trap behavioral)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
