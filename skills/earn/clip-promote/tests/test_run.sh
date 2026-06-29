#!/usr/bin/env bash
# Unit tests for the clip-promote slot harness: (1) discover emits a valid one-line JSON + exit 0;
# (2) the portable watchdog trips to 124 on a blocking step (REQ-9); (3) FIND-301 — the SAME PII env
# var that makes a direct record.mjs call THROW is stripped by `env -i`, so the RECORD subprocess records.
set -u
SK="$HOME/anicca/skills/earn/clip-promote"
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

echo ""; echo "$PASS/$((PASS+FAIL)) passed"
[ "$FAIL" -eq 0 ]
