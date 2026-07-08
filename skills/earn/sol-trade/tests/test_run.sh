#!/usr/bin/env bash
# Bash integration tests for skills/earn/sol-trade/run.sh (FIND-005 / verification-architecture.md
# PROP-011..016). Hermetic: no real network beyond a LOCAL fake Solana RPC bound to a random port
# (mirroring skills/earn/clip-promote/tests/fake_solana_rpc.mjs's ACTUAL proven pattern), no real
# franklin-trading CLI (a fixture executable placed first on $PATH for these invocations), and no
# real wallet (every keypair here is freshly generated for the test, never Franklin's real secret).
#
# $HOME is overridden to a throwaway fixture dir for every run.sh invocation in this file, so
# the forced `ANICCA_HOME=$HOME/.blockrun` derivation inside run.sh always resolves against OUR
# fixture tree, never the real ~/.blockrun. skills/earn/sol-trade/run.sh's own TRACE path is NOT
# env-overridable (hardcoded relative to the real repo), so this file snapshots the real
# skills/earn/state/sol-trade.trace.jsonl before running and restores it byte-for-byte on exit
# (snapshot-diff cleanup discipline) -- it never leaves test-only lines in real production state.
set -u
SK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"           # skills/earn/sol-trade
REPO="$(cd "$SK/../../.." && pwd)"                              # repo root
NODE=/opt/homebrew/bin/node; [ -x "$NODE" ] || NODE=node
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3
REAL_PATH="$PATH"

PASS=0; FAIL=0
ok(){ echo "  ok  $1"; PASS=$((PASS+1)); }
no(){ echo "  FAIL $1: $2"; FAIL=$((FAIL+1)); }

TMP="$(mktemp -d)"

# --- snapshot-diff cleanup: the real trace.jsonl is not env-overridable; back it up, restore on exit ---
# run.sh's own STATE_DIR is "$SKILL_DIR/../state" (skills/earn/state, a sibling of sol-trade/), not
# skills/earn/sol-trade/state -- mirror that exact relative path here. Assert the real state dir
# ALREADY exists (never `mkdir -p` it here): a wrong REAL_TRACE path must fail loudly, not silently
# create a phantom directory and back up nothing while run.sh still appends to the REAL file.
REAL_TRACE="$SK/../state/sol-trade.trace.jsonl"
if [ ! -d "$(dirname "$REAL_TRACE")" ]; then
  echo "FATAL: expected real state dir $(dirname "$REAL_TRACE") does not exist -- REAL_TRACE path is wrong; refusing to run (this would silently skip the trace backup while run.sh still writes to the real file)" >&2
  exit 1
fi
TRACE_BACKUP="$TMP/trace-original-backup.jsonl"
if [ -f "$REAL_TRACE" ]; then cp "$REAL_TRACE" "$TRACE_BACKUP"; else : > "$TRACE_BACKUP"; fi
RPC_PIDS=()
cleanup() {
  for p in "${RPC_PIDS[@]:-}"; do kill "$p" >/dev/null 2>&1 || true; done
  cp "$TRACE_BACKUP" "$REAL_TRACE" 2>/dev/null || rm -f "$REAL_TRACE"
  rm -rf "$TMP"
}
trap cleanup EXIT

trace_lines_now() { wc -l < "$REAL_TRACE" 2>/dev/null | tr -d ' '; }
trace_new_lines() { # $1 = line count BEFORE the invocation
  local before="$1"
  tail -n "+$((before + 1))" "$REAL_TRACE" 2>/dev/null
}

# --- fixture keypairs (real, freshly generated ed25519 Solana keypairs -- never Franklin's real key) ---
gen_keypair() {
  "$NODE" -e "
import('@solana/web3.js').then(async (web3) => {
  const bs58 = (await import('bs58')).default;
  const kp = web3.Keypair.generate();
  console.log(bs58.encode(kp.secretKey) + ' ' + kp.publicKey.toBase58());
});
"
}
read -r FRANKLIN_SECRET FRANKLIN_ADDR <<< "$(gen_keypair)"
read -r THIRDPARTY_SECRET THIRDPARTY_ADDR <<< "$(gen_keypair)"
if [ -z "$FRANKLIN_ADDR" ] || [ -z "$THIRDPARTY_ADDR" ]; then
  echo "FATAL: could not generate fixture Solana keypairs (is @solana/web3.js installed at $REPO?)" >&2
  exit 1
fi

# --- fixture $HOME tree ---
FAKE_HOME="$TMP/home"
mkdir -p "$FAKE_HOME/.blockrun/.automaton" "$FAKE_HOME/.third-party/.automaton" "$FAKE_HOME/.anicca-empty"
"$PY" -c "import json,sys;json.dump({'address':sys.argv[2],'secretKey':sys.argv[1],'secretKeyBytes':[]},open(sys.argv[3]+'/.blockrun/.automaton/solana.json','w'))" "$FRANKLIN_SECRET" "$FRANKLIN_ADDR" "$FAKE_HOME"
"$PY" -c "import json,sys;json.dump({'address':sys.argv[2],'secretKey':sys.argv[1],'secretKeyBytes':[]},open(sys.argv[3]+'/.third-party/.automaton/solana.json','w'))" "$THIRDPARTY_SECRET" "$THIRDPARTY_ADDR" "$FAKE_HOME"
# $FAKE_HOME/.anicca-empty deliberately has NO .automaton/solana.json -- automaton's real shape.

# --- fixture franklin-trading CLI stub, first on $PATH for every invocation below ---
FIXTURE_BIN="$TMP/bin"; mkdir -p "$FIXTURE_BIN"
cat > "$FIXTURE_BIN/franklin-trading" <<'STUB'
#!/bin/bash
# Test-only stub. Records that it was invoked (FT_STUB_MARKER) and, for its `start` subcommand
# ONLY (the ONLY subcommand this feature ever calls or stubs), emits FT_STUB_SIGS as one or more
# fixed-format "Signature: <sig>" receipt lines -- or an honest WAIT narrate line if unset/empty.
if [ -n "${FT_STUB_MARKER:-}" ]; then
  echo "invoked $(date -u +%s) args=$*" >> "$FT_STUB_MARKER"
fi
if [ "${1:-}" = "start" ]; then
  if [ -n "${FT_STUB_SIGS:-}" ]; then
    IFS=',' read -ra _SIGS <<< "$FT_STUB_SIGS"
    for s in "${_SIGS[@]}"; do
      echo "Signature: $s"
      echo "Solscan: https://solscan.io/tx/$s"
    done
  else
    echo "TradingSignal: neutral -- WAIT (no edge this session)"
  fi
  exit 0
fi
echo "unsupported subcommand: ${1:-}" >&2
exit 1
STUB
chmod +x "$FIXTURE_BIN/franklin-trading"

# --- start a fake Solana RPC server, return its PORT ---
start_fake_rpc() { # $1=wallet $2=delta $3=mode -> prints PORT
  local logf; logf="$(mktemp)"
  FAKE_RPC_WALLET="$1" FAKE_RPC_DELTA="$2" FAKE_RPC_MODE="$3" "$NODE" "$SK/tests/fake_solana_rpc.mjs" >"$logf" 2>&1 &
  local pid=$!
  RPC_PIDS+=("$pid")
  for _ in 1 2 3 4 5 6 7 8 9 10; do grep -q "PORT=" "$logf" 2>/dev/null && break; sleep 0.2; done
  sed -n 's/^PORT=//p' "$logf" | head -1
}

# run.sh invocation helper. args: ANICCA_HOME, EARN_LEDGER path, FT_STUB_SIGS, SOLANA_RPC_URL,
# extra_env (space-joined KEY=VAL pairs, may be empty), marker path -> sets RUN_OUT / RUN_RC.
run_pass() {
  local home_arg="$1" ledger="$2" sigs="$3" rpc="$4" extra="$5" marker="$6"
  RUN_OUT="$(env -i \
    HOME="$FAKE_HOME" \
    PATH="$FIXTURE_BIN:$REAL_PATH" \
    ANICCA_HOME="$home_arg" \
    EARN_LEDGER="$ledger" \
    FT_STUB_SIGS="$sigs" \
    FT_STUB_MARKER="$marker" \
    SOLANA_RPC_URL="$rpc" \
    ANICCA_TELEMETRY_URL="http://127.0.0.1:1" \
    SOL_TRADE_MAX_SPEND="0.01" \
    $extra \
    bash "$SK/run.sh" 2>&1)"
  RUN_RC=$?
}

# ============================================================================
# (a) PROP-005/PROP-014(c): Franklin-shaped identity (own ANICCA_HOME literally IS $HOME/.blockrun)
#     PROCEEDs and records exactly one ledger line with net_usdc == the RPC's delta.
# ============================================================================
LEDGER_A="$TMP/ledger-a.jsonl"
MARKER_A="$TMP/marker-a.log"
PORT_A="$(start_fake_rpc "$FRANKLIN_ADDR" "0.5" "ok")"
BEFORE_A="$(trace_lines_now)"
run_pass "$FAKE_HOME/.blockrun" "$LEDGER_A" "5111111111111111111111111111111111111111111111111111111111111111111111111111111111" \
  "http://127.0.0.1:$PORT_A" "" "$MARKER_A"
if [ -f "$MARKER_A" ] && [ -f "$LEDGER_A" ] \
  && "$NODE" -e "
import('$REPO/skills/_shared/lib/ledger.mjs').then(async m => {
  const rows = await m.readLedger('$LEDGER_A');
  process.exit(rows.length === 1 && rows[0].net_usdc === 0.5 && rows[0].wallet === '$FRANKLIN_ADDR'
    && rows[0].source === 'sol-trade' && rows[0].external !== true ? 0 : 1);
}).catch(() => process.exit(1));
"; then
  ok "(a) Franklin-shaped identity PROCEEDS, records exactly 1 ledger line (net_usdc=0.5, no external:true)"
else
  no "(a) franklin-proceeds" "rc=$RUN_RC marker=$([ -f "$MARKER_A" ] && echo yes || echo no) ledger=$(cat "$LEDGER_A" 2>/dev/null)"
fi
[ "$RUN_RC" -eq 0 ] && ok "(a) exit 0" || no "(a) exit-code" "got $RUN_RC"

# ============================================================================
# (b) PROP-014(a): automaton-shaped ANICCA_HOME (no resolvable Solana secret at all) HALTs BEFORE
#     franklin-trading is ever invoked -- the already-live cross-instance leak this feature fixes.
# ============================================================================
LEDGER_B="$TMP/ledger-b.jsonl"
MARKER_B="$TMP/marker-b.log"
BEFORE_B="$(trace_lines_now)"
run_pass "$FAKE_HOME/.anicca-empty" "$LEDGER_B" "" "http://127.0.0.1:1" "" "$MARKER_B"
if [ ! -f "$MARKER_B" ] && [ ! -f "$LEDGER_B" ] && [ "$RUN_RC" -eq 0 ] \
  && trace_new_lines "$BEFORE_B" | grep -q "identity-mismatch"; then
  ok "(b) automaton-shaped ANICCA_HOME HALTs before franklin-trading start (root cause 3 fix), exit 0, zero new ledger lines"
else
  no "(b) automaton-halts" "rc=$RUN_RC marker=$([ -f "$MARKER_B" ] && echo yes || echo no) trace_new=$(trace_new_lines "$BEFORE_B")"
fi

# ============================================================================
# (c) FIND-001 regression: an ambient ANICCA_SOLANA_PRIVATE_KEY set in the parent env (NOT via any
#     .env file -- sol-trade/run.sh sources none) must NOT bypass the identity-match guard for a
#     non-Franklin instance, even though the override, if it leaked into BOTH wallet-address-solana
#     invocations, would make them spuriously agree (the exact FIND-001 bypass).
# ============================================================================
LEDGER_C="$TMP/ledger-c.jsonl"
MARKER_C="$TMP/marker-c.log"
BEFORE_C="$(trace_lines_now)"
run_pass "$FAKE_HOME/.anicca-empty" "$LEDGER_C" "" "http://127.0.0.1:1" "ANICCA_SOLANA_PRIVATE_KEY=$THIRDPARTY_SECRET" "$MARKER_C"
if [ ! -f "$MARKER_C" ] && [ ! -f "$LEDGER_C" ] && [ "$RUN_RC" -eq 0 ]; then
  ok "(c) FIND-001 regression: ambient ANICCA_SOLANA_PRIVATE_KEY does NOT bypass the identity-match guard"
else
  no "(c) find-001-regression" "rc=$RUN_RC marker=$([ -f "$MARKER_C" ] && echo yes || echo no) ledger=$(cat "$LEDGER_C" 2>/dev/null)"
fi

# ============================================================================
# (d) PROP-014(b): a fixture ANICCA_HOME with its OWN resolvable-but-FOREIGN Solana secret still
#     HALTs -- "some wallet resolved" is not sufficient; it must be THE wallet the CLI will use.
# ============================================================================
LEDGER_D="$TMP/ledger-d.jsonl"
MARKER_D="$TMP/marker-d.log"
BEFORE_D="$(trace_lines_now)"
run_pass "$FAKE_HOME/.third-party" "$LEDGER_D" "" "http://127.0.0.1:1" "" "$MARKER_D"
if [ ! -f "$MARKER_D" ] && [ ! -f "$LEDGER_D" ] && [ "$RUN_RC" -eq 0 ] \
  && trace_new_lines "$BEFORE_D" | grep -q "identity-mismatch"; then
  ok "(d) resolvable-but-foreign wallet still HALTs (identity MATCH required, not mere non-emptiness)"
else
  no "(d) foreign-wallet-halts" "rc=$RUN_RC marker=$([ -f "$MARKER_D" ] && echo yes || echo no) trace_new=$(trace_new_lines "$BEFORE_D")"
fi

# ============================================================================
# (e) PROP-012: identity guard PASSES (Franklin-shaped) but the cumulative earn-guard HALTs on a
#     pre-seeded negative net for this wallet -- franklin-trading must still never be invoked.
# ============================================================================
LEDGER_E="$TMP/ledger-e.jsonl"
MARKER_E="$TMP/marker-e.log"
"$PY" -c "
import json
line = {'wallet':'$FRANKLIN_ADDR','source':'sol-trade','task':'seed-loss','earn_usdc':0,'cost_usdc':50,'net_usdc':-50,'wake':'seed'}
open('$LEDGER_E','w').write(json.dumps(line) + '\n')
"
BEFORE_E="$(trace_lines_now)"
run_pass "$FAKE_HOME/.blockrun" "$LEDGER_E" "" "http://127.0.0.1:1" "" "$MARKER_E"
LEDGER_E_LINES="$(wc -l < "$LEDGER_E" 2>/dev/null | tr -d ' ')"
if [ ! -f "$MARKER_E" ] && [ "$LEDGER_E_LINES" = "1" ] && [ "$RUN_RC" -eq 0 ] \
  && trace_new_lines "$BEFORE_E" | grep -q "earn-guard"; then
  ok "(e) PROP-012: cumulative earn-guard HALTs the pass BEFORE franklin-trading start, no new ledger line"
else
  no "(e) earn-guard-halts" "rc=$RUN_RC marker=$([ -f "$MARKER_E" ] && echo yes || echo no) ledger_lines=$LEDGER_E_LINES"
fi

# ============================================================================
# (f) FIND-002/003 (PROP-005 multi-step): multiple "Signature:" lines in one pass's stdout ->
#     only the LAST signature is recorded.
# ============================================================================
LEDGER_F="$TMP/ledger-f.jsonl"
MARKER_F="$TMP/marker-f.log"
SIG_FIRST="5222222222222222222222222222222222222222222222222222222222222222222222222222222222"
SIG_LAST="5333333333333333333333333333333333333333333333333333333333333333333333333333333333"
PORT_F="$(start_fake_rpc "$FRANKLIN_ADDR" "0.2" "ok")"
run_pass "$FAKE_HOME/.blockrun" "$LEDGER_F" "$SIG_FIRST,$SIG_LAST" "http://127.0.0.1:$PORT_F" "" "$MARKER_F"
if [ -f "$LEDGER_F" ] && "$NODE" -e "
import('$REPO/skills/_shared/lib/ledger.mjs').then(async m => {
  const rows = await m.readLedger('$LEDGER_F');
  process.exit(rows.length === 1 && rows[0].sig === '$SIG_LAST' ? 0 : 1);
}).catch(() => process.exit(1));
"; then
  ok "(f) multi-signature pass records the LAST signature only (FIND-002/003)"
else
  no "(f) last-sig" "ledger=$(cat "$LEDGER_F" 2>/dev/null)"
fi

# ============================================================================
# (g) PROP-016/FIND-007: RPC verify failure (getSignatureStatuses/getTransaction erroring) ->
#     zero new earn-ledger.jsonl lines, exactly ONE new trace.jsonl "sol-verify-failed" line,
#     exit 0 (never a crash, never a NaN/Infinity net_usdc).
# ============================================================================
LEDGER_G="$TMP/ledger-g.jsonl"
MARKER_G="$TMP/marker-g.log"
SIG_G="5444444444444444444444444444444444444444444444444444444444444444444444444444444444"
PORT_G="$(start_fake_rpc "$FRANKLIN_ADDR" "0.5" "malformed")"
BEFORE_G="$(trace_lines_now)"
run_pass "$FAKE_HOME/.blockrun" "$LEDGER_G" "$SIG_G" "http://127.0.0.1:$PORT_G" "" "$MARKER_G"
if [ ! -f "$LEDGER_G" ] && [ "$RUN_RC" -eq 0 ] \
  && trace_new_lines "$BEFORE_G" | grep -q '"action":"sol-verify-failed".*"status":"verify-error"'; then
  ok "(g) PROP-016: RPC verify-error degrades to a trace-only sol-verify-failed line, zero ledger lines, exit 0"
else
  no "(g) verify-error-degrade" "rc=$RUN_RC ledger=$(cat "$LEDGER_G" 2>/dev/null) trace_new=$(trace_new_lines "$BEFORE_G")"
fi

# ============================================================================
# (h) baseline edge case: no "Signature:" line at all (agent WAITed) -> zero new ledger lines.
# ============================================================================
LEDGER_H="$TMP/ledger-h.jsonl"
MARKER_H="$TMP/marker-h.log"
run_pass "$FAKE_HOME/.blockrun" "$LEDGER_H" "" "http://127.0.0.1:1" "" "$MARKER_H"
if [ ! -f "$LEDGER_H" ] && [ "$RUN_RC" -eq 0 ]; then
  ok "(h) no Signature: line (WAIT) -> zero new ledger lines"
else
  no "(h) no-sig-no-record" "rc=$RUN_RC ledger=$(cat "$LEDGER_H" 2>/dev/null)"
fi

echo ""; echo "$PASS/$((PASS+FAIL)) passed"
[ "$FAIL" -eq 0 ]
