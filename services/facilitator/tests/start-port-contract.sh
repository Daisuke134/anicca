#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
SANDBOX="$TEST_ROOT/facilitator"
PID_FILE="$TEST_ROOT/fake.pid"
BASE_PORT=$((20000 + ($$ % 20000)))
REQUESTED_PORT=$((BASE_PORT + 1))

cleanup() {
  if [ -s "$PID_FILE" ]; then
    FAKE_PID="$(tr -d '[:space:]' < "$PID_FILE")"
    if [[ "$FAKE_PID" =~ ^[0-9]+$ ]]; then kill "$FAKE_PID" 2>/dev/null || true; fi
  fi
  rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

mkdir -p "$SANDBOX/x402-rs/target/release"
cp "$SOURCE_DIR/start.sh" "$SANDBOX/start.sh"
cp "$SOURCE_DIR/tests/fake-facilitator.mjs" \
  "$SANDBOX/x402-rs/target/release/x402-facilitator"
chmod +x "$SANDBOX/start.sh" "$SANDBOX/x402-rs/target/release/x402-facilitator"

jq -n \
  --argjson port "$BASE_PORT" \
  '{port:$port,host:"127.0.0.1",chains:{},schemes:[]}' \
  > "$SANDBOX/config.mainnet.json"
cp "$SANDBOX/config.mainnet.json" "$SANDBOX/config.json"
BEFORE_HASH="$(shasum -a 256 "$SANDBOX/config.mainnet.json" | awk '{print $1}')"

FAKE_FACILITATOR_PID_FILE="$PID_FILE" \
  GIG_CHAIN=base \
  PORT="$REQUESTED_PORT" \
  /bin/bash "$SANDBOX/start.sh" >/dev/null

curl -fsS "http://127.0.0.1:$REQUESTED_PORT/health" \
  | jq -e '.ok == true' >/dev/null
AFTER_HASH="$(shasum -a 256 "$SANDBOX/config.mainnet.json" | awk '{print $1}')"
[ "$BEFORE_HASH" = "$AFTER_HASH" ]

printf 'PASS start.sh binds the requested port without mutating canonical config\n'
