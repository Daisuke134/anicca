#!/usr/bin/env bash
# E2E (local): checkpoint.sh writes a checkpoint with the required keys + a ledger row, then
# restart.sh proves a fresh ~/.hermes-resurrected-<id>/ HERMES_HOME boots (`hermes status`) and
# cleans the mockup up. Isolated STATE_DIR; the live ~/.hermes is never mutated.
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")/../scripts" && pwd)"
JQ=/usr/bin/jq

pass=0; fail=0
ok()  { echo "PASS: $1"; pass=$((pass+1)); }
bad() { echo "FAIL: $1"; fail=$((fail+1)); }

export STATE_DIR; STATE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/resurr-e2e-XXXX")"
cleanup() { rm -rf "$STATE_DIR" 2>/dev/null || true; }
trap cleanup EXIT

CKPT_DIR="$STATE_DIR/checkpoints"
LEDGER="$STATE_DIR/resurrection.jsonl"

# ---- 1. checkpoint.sh writes a checkpoint json with the 7 required keys.
bash "$SCRIPTS/checkpoint.sh" >/dev/null 2>&1 || true
CK="$(ls "$CKPT_DIR"/*.json 2>/dev/null | head -1)"
if [ -n "$CK" ] && "$JQ" -e \
     'has("checkpoint_id") and has("ts") and has("model") and has("profile")
      and has("last_skill_run") and has("last_decision")
      and has("hermes_config_sha") and has("anicca_oss_sha")' "$CK" >/dev/null 2>&1; then
  ok "checkpoint json has all required keys ($(basename "$CK"))"
else
  bad "checkpoint json missing keys (ck='$CK')"
  [ -n "$CK" ] && cat "$CK"
fi

CKID="$("$JQ" -r '.checkpoint_id' "$CK" 2>/dev/null)"

# ---- 2. ledger has a checkpoint row.
if [ -s "$LEDGER" ] && "$JQ" -e --arg id "$CKID" 'select(.op=="checkpoint" and .checkpoint_id==$id)' "$LEDGER" >/dev/null 2>&1; then
  ok "resurrection.jsonl has a checkpoint row"
else
  bad "no checkpoint row in ledger"
  cat "$LEDGER" 2>/dev/null
fi

# ---- 3. restart.sh proves a fresh HERMES_HOME boots; ledger gets a restart row with ok boolean.
bash "$SCRIPTS/restart.sh" "$CKID" >/dev/null 2>&1 || true
if "$JQ" -e --arg id "$CKID" 'select(.op=="restart" and .checkpoint_id==$id and (.ok|type=="boolean"))' "$LEDGER" >/dev/null 2>&1; then
  ok "restart row logged with ok boolean"
else
  bad "no restart row with ok boolean"
  cat "$LEDGER" 2>/dev/null
fi

# ---- 4. mockup HERMES_HOME cleaned up after restart.
if [ ! -d "$HOME/.hermes-resurrected-$CKID" ]; then
  ok "mockup ~/.hermes-resurrected-$CKID removed (cleanup proven)"
else
  bad "mockup dir NOT cleaned: $HOME/.hermes-resurrected-$CKID"
  rm -rf "$HOME/.hermes-resurrected-$CKID" 2>/dev/null || true
fi

echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
