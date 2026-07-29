#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# Unit tests for the clip-promote slot harness: (1) discover emits a valid one-line JSON + exit 0;
# (2) the portable watchdog trips to 124 on a blocking step (REQ-9); (3) FIND-301 — the SAME PII env
# var that makes a direct record.mjs call THROW is stripped by `env -i`, so the RECORD subprocess records.
set -u
SK="$LIFE_MANAGER_REPO/skills/earn/clip-promote"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3
NODE=/opt/homebrew/bin/node; [ -x "$NODE" ] || NODE=node
PASS=0; FAIL=0
ok(){ echo "  ok  $1"; PASS=$((PASS+1)); }
no(){ echo "  FAIL $1: $2"; FAIL=$((FAIL+1)); }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# (1) discover smoke
OUT="$(EARN_MODE=discover CLIP_PROMOTE_STATE="$TMP/state.json" EARN_LEDGER="$TMP/ledger.jsonl" bash "$SK/run.sh" 2>/dev/null)"
RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | "$PY" -c "import json,sys;d=json.load(sys.stdin);assert d['slot']=='earn/clip-promote';assert d['did'].startswith('discover');assert d['earned_usdc']==0" 2>/dev/null; then
  ok "discover emits valid JSON, exit 0"
else no "discover" "rc=$RC out=$OUT"; fi

# (2) watchdog primitive: a portable timeout returns 124 on a step that blocks past the deadline
TB="$(command -v timeout || command -v gtimeout || true)"
if [ -n "$TB" ]; then
  "$TB" 1 sleep 5; RC=$?
  [ "$RC" -eq 124 ] && ok "timeout binary trips to 124 (REQ-9 watchdog)" || no "watchdog" "expected 124 got $RC"
else
  ok "no timeout binary — pure fallback path (skipped primitive)"
fi

# (3) FIND-301 regression — direct record.mjs call WITH a PII env var THROWS (malice-guard intact)…
REC_JSON='{"wallet":"w","source":"promote.fun","task":"t","earn_usdc":1,"cost_usdc":0,"sig":"sigPII","confirmed":true,"chain":"solana","external":true,"wake":"w"}'
A="$(GOOGLE_LOGIN=leaked "$NODE" -e "import('$SK/../lib/record.mjs').then(m=>m.record(process.argv[1],process.argv[2])).then(()=>console.log('NO_THROW')).catch(()=>console.log('THREW'))" "$REC_JSON" "$TMP/a.jsonl" 2>/dev/null)"
[ "$A" = "THREW" ] && ok "PII env present → record.mjs THROWS (guard intact)" || no "guard-intact" "got '$A'"

# …and the SAME PII var is stripped by `env -i` (the run.sh RECORD invocation) → records cleanly.
B="$(GOOGLE_LOGIN=leaked env -i PATH="$PATH" HOME="$HOME" "$NODE" -e "import('$SK/../lib/record.mjs').then(m=>m.record(process.argv[1],process.argv[2])).then(()=>console.log('NO_THROW')).catch(e=>console.log('THREW:'+e.message))" "$REC_JSON" "$TMP/b.jsonl" 2>/dev/null)"
if [ "$B" = "NO_THROW" ] && [ -s "$TMP/b.jsonl" ]; then ok "env -i strips PII → RECORD records (FIND-301 fix)"; else no "env-i-fix" "got '$B'"; fi

# (4) FIND-001 — run.sh's blocked_or integration: 124 ⇒ blocked:human:<step> + exit 0 (not just the bare binary)
B1="$(PY="$PY"; . "$SK/_lib.sh"; (blocked_or campaign 124 "x") )"; RC1=$?
if echo "$B1" | "$PY" -c "import json,sys;d=json.load(sys.stdin);assert d['did']=='blocked:human:campaign';assert d['earned_usdc']==0" 2>/dev/null && [ "$RC1" -eq 0 ]; then
  ok "blocked_or(124) → blocked:human + exit 0 (REQ-9 integration)"
else no "blocked_or-124" "rc=$RC1 out=$B1"; fi
B2="$(PY="$PY"; . "$SK/_lib.sh"; (blocked_or post 7 "post:failed") )"; RC2=$?
if echo "$B2" | "$PY" -c "import json,sys;assert json.load(sys.stdin)['did']=='post:failed'" 2>/dev/null && [ "$RC2" -eq 0 ]; then
  ok "blocked_or(non-124) → narrate + exit 0"
else no "blocked_or-narrate" "rc=$RC2 out=$B2"; fi

# (5) FIND-002 — RECORD→DONE shell glue E2E (run.sh execute) against a LOCAL fake Solana RPC.
"$NODE" "$SK/tests/fake_solana_rpc.mjs" >"$TMP/rpc.log" 2>&1 &
RPC_PID=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do grep -q "PORT=" "$TMP/rpc.log" 2>/dev/null && break; sleep 0.3; done
PORT="$(sed -n 's/^PORT=//p' "$TMP/rpc.log" | head -1)"
SIG="52RZBMCUqGWrWPZCJo82xDaYusUhGNFNCEzW51nyJNhFN9AECae9dWyp8TQQZMP731LpP2Xu8JDpJDRxp3xCRD7m"
"$PY" -c "import json;json.dump({'phase':'WITHDRAW','sig':'$SIG'},open('$TMP/rstate.json','w'))"
if [ -n "$PORT" ]; then
  OUT5="$(EARN_MODE=execute SOLANA_RPC_URL="http://127.0.0.1:$PORT" \
          CLIP_PROMOTE_STATE="$TMP/rstate.json" EARN_LEDGER="$TMP/rledger.jsonl" \
          GOOGLE_LOGIN=leaked bash "$SK/run.sh" 2>/dev/null)"
  # did=record:DONE, earned>0, ledger has a profitable line, state reset to idle, PII didn't break it.
  if echo "$OUT5" | "$PY" -c "import json,sys;d=json.load(sys.stdin);assert d['did'].startswith('record:DONE'),d;assert d['earned_usdc']>0,d" 2>/dev/null \
     && [ -s "$TMP/rledger.jsonl" ] \
     && "$NODE" -e "import('$SK/../../_shared/lib/ledger.mjs').then(async m=>{const r=await m.readLedger('$TMP/rledger.jsonl');process.exit(r.length===1&&m.isProfitable(r[0])?0:1)})" 2>/dev/null \
     && "$PY" -c "import json;assert json.load(open('$TMP/rstate.json')).get('phase')=='idle'" 2>/dev/null; then
    ok "run.sh execute RECORD → record:DONE + profitable ledger line + slot freed (FIND-002, even with PII env)"
  else no "record-e2e" "out=$OUT5 ledger=$(cat "$TMP/rledger.jsonl" 2>/dev/null)"; fi
else no "record-e2e" "fake RPC did not start: $(cat "$TMP/rpc.log" 2>/dev/null)"; fi
kill "$RPC_PID" 2>/dev/null

echo ""; echo "$PASS/$((PASS+FAIL)) passed"
[ "$FAIL" -eq 0 ]
