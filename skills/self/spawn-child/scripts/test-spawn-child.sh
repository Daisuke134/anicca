#!/usr/bin/env bash
# Test oracle for self/spawn-child run.sh. STATIC invariants (grep, comments stripped) + BEHAVIORAL runs
# against a fake provider-services (query-only responses) so both the NOT-YET and READY branches are
# exercised deterministically WITHOUT ever touching real money (no real tx is possible via the fake
# binary; the real-wallet run is a separate manual fresh-evidence step, see SKILL.md "Verify").
# Exit 0=PASS, 1=FAIL.
set -uo pipefail
D="$(cd "$(dirname "$0")/.." && pwd)"
S="$D/run.sh"
src="$(sed 's/#.*//' "$S")"
fails=0
have(){   grep -qE "$1" <<<"$src" || { echo "  - FAIL missing [$1] — $2"; fails=$((fails+1)); }; }
absent(){ grep -qE "$1" <<<"$src" && { echo "  - FAIL present [$1] — $2"; fails=$((fails+1)); }; true; }
ok(){     [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC: this script must NEVER be able to move money ----------
# INV-1 checks ACTUAL invocations (\$PS ... tx / send-manifest / mint-act), not prose that merely
# mentions these words while explaining what the script does NOT do.
absent '"\$PS"[^\n]*( tx |send-manifest)'  "INV-1a gate NEVER invokes a provider-services tx/send-manifest subcommand"
absent 'mint-act|tx bank send'             "INV-1b gate NEVER mints or sends funds"
have   "query bank balances"                                                              "INV-2 uses the read-only balance query"
have   "computeSpawnGate"                                                                 "INV-3 delegates the decision to the pure, tested gate function"
have   "exit 0"                                                                            "INV-4 NOT-YET is not a failure (exit 0)"
absent "spawn OK\?|proceed\?|continue\?"                                                    "INV-5 no human-in-the-loop prompt"

# ---------- BEHAVIORAL: faithful fake provider-services (query-only) ----------
mkfake(){ # $1 = uakt balance to report
  cat <<FAKE
#!/usr/bin/env bash
echo "\$*" >> "\$SC_REC"
case "\$*" in
  *"keys show"*)         echo "akash1testfakefakefakefakefakefakefakefakefake" ;;
  *"query bank balances"*) echo '{"balances":[{"denom":"uakt","amount":"${1}"}],"pagination":{}}' ;;
  *)                     echo "{}" ;;
esac
FAKE
}
runfake(){ # $1 = uakt balance, $2 = cost_akt, $3 = buffer_akt -> sets OUT, rc, recd
  local T; T="$(mktemp -d)"; REC="$T/rec"; : >"$REC"
  mkfake "$1" >"$T/provider-services"; chmod +x "$T/provider-services"
  cat > "$T/config.json" <<CFG
{"akash_key_name":"anicca-akash","akash_keyring_backend":"test","spawn_cost_akt":${2},"buffer_akt":${3},"recipient_chain":"akashnet-2","funding_route":"solana/8453 -> noble-1 -> osmosis-1 -> akashnet-2","sdl_template":"sdl/child.yaml"}
CFG
  OUT="$(SC_REC="$REC" PROVIDER_SERVICES="$T/provider-services" AKASH_KEY_NAME=anicca-akash \
         AKASH_NODE="http://localhost:1" AKASH_CHAIN_ID="testchain" AKASH_KEYRING_BACKEND=test \
         ANICCA_STATE_DIR="$T/state" \
         bash "$S" --config "$T/config.json" 2>"$T/err")"; rc=$?
  recd="$(cat "$REC")"; ledger="$T/state/spawn-child-gate.jsonl"
  rm -rf "$T"
}

# NOT-YET: 1.8575 AKT (1857500 uakt, the REAL live balance 2026-07-05) vs cost 25 + buffer 1 = threshold 26
runfake 1857500 25 1
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "behavioral NOT-YET: exit $rc (must be 0, not a failure) — $(tail -1 <<<"$OUT")"
grep -q '"ready":false' <<<"$OUT" || { echo "  - FAIL: expected ready:false in output"; fails=$((fails+1)); }
grep -q "NOT-YET" <<<"$OUT" || { echo "  - FAIL: expected NOT-YET message"; fails=$((fails+1)); }
grep -qE 'query bank balances' <<<"$recd" || { echo "  - FAIL: balance query never called"; fails=$((fails+1)); }
grep -qE 'deployment create|lease create|send-manifest|mint-act|bank send' <<<"$recd" \
  && { echo "  - FAIL: a money-moving/deploy command was invoked in NOT-YET path"; fails=$((fails+1)); }; true

# READY: balance 30 AKT vs cost 25 + buffer 1 = threshold 26 -> ready, still NO deploy/tx call
runfake 30000000 25 1
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "behavioral READY: exit $rc — $(tail -1 <<<"$OUT")"
grep -q '"ready":true' <<<"$OUT" || { echo "  - FAIL: expected ready:true in output"; fails=$((fails+1)); }
grep -q "READY" <<<"$OUT" || { echo "  - FAIL: expected READY message"; fails=$((fails+1)); }
grep -q "next steps" <<<"$OUT" || { echo "  - FAIL: expected next-steps guidance (agent decides, not auto-executed)"; fails=$((fails+1)); }
grep -qE 'deployment create|lease create|send-manifest|mint-act|bank send' <<<"$recd" \
  && { echo "  - FAIL: a money-moving/deploy command was invoked in READY path (must NEVER auto-fire)"; fails=$((fails+1)); }; true

# boundary: balance exactly AT threshold -> ready
runfake 26000000 25 1
grep -q '"ready":true' <<<"$OUT" || { echo "  - FAIL: exact-threshold balance should be ready"; fails=$((fails+1)); }

# fail-closed: akash key not resolvable -> exit != 0, no fake success
T="$(mktemp -d)"
cat > "$T/config.json" <<CFG
{"akash_key_name":"missing-key","akash_keyring_backend":"test","spawn_cost_akt":25,"buffer_akt":1,"recipient_chain":"akashnet-2","funding_route":"x","sdl_template":"sdl/child.yaml"}
CFG
cat > "$T/provider-services" <<'FAKE'
#!/usr/bin/env bash
case "$*" in
  *"keys show"*) exit 1 ;;
  *) echo "{}" ;;
esac
FAKE
chmod +x "$T/provider-services"
OUT2="$(PROVIDER_SERVICES="$T/provider-services" AKASH_NODE="http://localhost:1" AKASH_CHAIN_ID="testchain" \
        ANICCA_STATE_DIR="$T/state" bash "$S" --config "$T/config.json" 2>&1)"; rc2=$?
rm -rf "$T"
ok "$([ $rc2 -ne 0 ] && echo 1 || echo 0)" "fail-closed: missing akash key -> exit != 0 (got $rc2)"

[ $fails -eq 0 ] && { echo "PASS — spawn-child gate invariants hold (static: no money-moving calls + behavioral: NOT-YET/READY/boundary/fail-closed)"; exit 0; } \
                  || { echo "FAIL ($fails)"; exit 1; }
