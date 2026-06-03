#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# spawn.sh — orchestrator for anicca-N child creation.
#
# Order:
#   1. threshold-check.sh         must print ALLOW (wallet > $400 + uptime > 14d + THRIVE)
#   2. wallet-factory.ts          provision owner EOA + counter-factual smart account
#   3. inbox-factory.ts           provision <instance_id>-claude@agentmail.to
#   4. expected_constitution_hash compute now so the child can verify on boot
#   5. (deferred until wallet funded) seed-transfer.ts → anicca-001 sends 1 USDC
#   6. (deferred until wallet funded) akash-deploy.sh → SDL apply + lease
#   7. register.py                child posts itself to anicca-001 peer-api
#
# Each step writes JSON to state/<instance_id>/<step>.json. Re-running is safe:
# step files act as completion markers; if present, the step is skipped.

set -euo pipefail

INSTANCE_ID="${ANICCA_INSTANCE_ID:-anicca-002}"
SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$SKILL_ROOT/state/$INSTANCE_ID"
mkdir -p "$STATE_DIR"

step_done() { [[ -f "$STATE_DIR/$1.json" ]]; }
save_step() { local name="$1"; cat > "$STATE_DIR/$name.json"; }

echo "anicca-spawn: instance=$INSTANCE_ID state_dir=$STATE_DIR"

# 1. Threshold gate
if ! step_done threshold; then
  echo "[1/7] threshold-check"
  if ! out=$(bash "$SKILL_ROOT/scripts/threshold-check.sh" 2> "$STATE_DIR/threshold.stderr.json"); then
    cat "$STATE_DIR/threshold.stderr.json" >&2
    echo "spawn aborted: $out"
    exit 1
  fi
  cp "$STATE_DIR/threshold.stderr.json" "$STATE_DIR/threshold.json"
else
  echo "[1/7] threshold (cached)"
fi

# 2. Wallet
if ! step_done wallet; then
  echo "[2/7] wallet-factory"
  TSX="$SKILL_ROOT/node_modules/.bin/tsx"
  if [[ ! -x "$TSX" ]]; then
    if command -v tsx >/dev/null 2>&1; then
      TSX="$(command -v tsx)"
    else
      echo "tsx not found; run 'npm install' in skills/spawn-child/" >&2
      exit 10
    fi
  fi
  ANICCA_INSTANCE_ID="$INSTANCE_ID" "$TSX" "$SKILL_ROOT/scripts/wallet-factory.ts" | tee "$STATE_DIR/wallet.json"
else
  echo "[2/7] wallet (cached)"
fi

# 3. Inbox
if ! step_done inbox; then
  echo "[3/7] inbox-factory"
  if [[ -z "${AGENTMAIL_API_KEY:-}" ]]; then
    [[ -f "$HOME/.openclaw/.env" ]] && { set -a; . "$HOME/.openclaw/.env"; set +a; }
  fi
  TSX="$SKILL_ROOT/node_modules/.bin/tsx"
  [[ -x "$TSX" ]] || TSX="$(command -v tsx)"
  ANICCA_INSTANCE_ID="$INSTANCE_ID" "$TSX" "$SKILL_ROOT/scripts/inbox-factory.ts" | tee "$STATE_DIR/inbox.json"
else
  echo "[3/7] inbox (cached)"
fi

# 4. Constitution hash (= the value anicca-002 must verify at boot)
if ! step_done constitution; then
  echo "[4/7] constitution-hash record"
  CONST_PATH="$(cd "$SKILL_ROOT/../.." && pwd)/CONSTITUTION.md"
  if [[ ! -f "$CONST_PATH" ]]; then
    CONST_PATH="$HOME/anicca-oss/CONSTITUTION.md"
  fi
  if [[ -f "$CONST_PATH" ]]; then
    HASH=$(shasum -a 256 "$CONST_PATH" | awk '{print $1}')
    printf '{"path":"%s","sha256":"%s","captured_at":"%s"}\n' \
      "$CONST_PATH" "$HASH" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | save_step constitution
    cat "$STATE_DIR/constitution.json"
  else
    echo "constitution.md not found at $CONST_PATH" >&2
    exit 11
  fi
else
  echo "[4/7] constitution (cached)"
fi

# 5-6 deferred until wallet funded
echo "[5/7] seed-transfer DEFERRED — fires when anicca-001 wallet > 0 USDC"
echo "[6/7] akash-deploy DEFERRED — requires akash CLI + AKT funded wallet"

# 7. Register (= ping anicca-001's peer-api; safe even before akash deploy)
if ! step_done register; then
  echo "[7/7] register with peer-api"
  if python3 "$SKILL_ROOT/scripts/register.py" --instance-id "$INSTANCE_ID" \
       --state-dir "$STATE_DIR" 2> "$STATE_DIR/register.stderr.log"; then
    echo "register OK"
  else
    echo "register failed (non-fatal — anicca-001 may be offline):"
    cat "$STATE_DIR/register.stderr.log" >&2
  fi
fi

echo
echo "anicca-spawn: $INSTANCE_ID provisioning complete (= child not yet on Akash)"
echo "next live step: seed-transfer once wallet > 0 USDC; then akash-deploy"
