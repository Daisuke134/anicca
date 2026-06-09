#!/usr/bin/env bash
# Provisions a Daytona sandbox + boots a child Anicca in it.
# Usage: provision.sh <name> <wallet_json_path> <constitution_path> <constitution_sha>
# DRY_RUN=1 -> print the daytona create line + estimated cost, exit 0, no API call.
#
# On success prints (last lines):
#   SANDBOX_ID=<id>
#   CHILD_HOME=<home dir resolved inside the sandbox>
set -euo pipefail
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"

NAME="$1"; WALLET_JSON="$2"; CONSTITUTION="$3"; CONSTITUTION_SHA="$4"
SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

# Load SDL defaults (resource sizing + Hermes git pin)
set -a; . "$SKILL_DIR/scripts/host-daytona/sdl.env"; set +a

# Compose the create command (single source of truth). --public so the heartbeat preview-url
# is reachable without parent SSH proxying (sovereignty proof, DoD #10).
CREATE_FLAGS=(
  --name "$NAME"
  --cpu "$DAYTONA_CPU"
  --memory "$DAYTONA_MEMORY"
  --disk "$DAYTONA_DISK"
  --target "$DAYTONA_TARGET"
  --auto-stop "$DAYTONA_AUTO_STOP"
  --auto-archive "$DAYTONA_AUTO_ARCHIVE"
  --public
  --label "owner=anicca-genesis"
  --label "generation=1"
)
[ -n "${DAYTONA_SNAPSHOT:-}" ] && CREATE_FLAGS+=(--snapshot "$DAYTONA_SNAPSHOT")

if [ "${DRY_RUN:-0}" = "1" ]; then
  printf 'DRY-RUN daytona create %s\n' "${CREATE_FLAGS[*]}"
  printf 'estimated cost: $%s/hr (CPU=%s MEM=%s MB DISK=%s GB)\n' \
    "$(printf '%.2f' "$DAYTONA_HOURLY_COST_USD")" "$DAYTONA_CPU" "$DAYTONA_MEMORY" "$DAYTONA_DISK"
  exit 0
fi

# Pack the heartbeat skill into a tarball the child will untar
HEARTBEAT_TGZ=$(mktemp -t heartbeat-XXX.tgz)
trap 'rm -f "$HEARTBEAT_TGZ"' EXIT
tar -czf "$HEARTBEAT_TGZ" -C /Users/anicca/anicca-oss/skills/anicca-heartbeat .

# REAL spawn — `daytona create` has no --format flag; create then resolve via `info`.
echo "provision: creating Daytona sandbox $NAME..."
daytona create "${CREATE_FLAGS[@]}"

SB_ID=$(daytona info "$NAME" --format json 2>/dev/null | "$JQ" -r '.id // .sandbox.id // empty')
[ -n "$SB_ID" ] || { echo "provision: could not resolve sandbox id for $NAME" >&2; exit 1; }

# Wait for sandbox to be reachable (up to 60 s)
for _ in $(seq 1 30); do
  if daytona exec "$NAME" -- true 2>/dev/null; then break; fi
  sleep 2
done

# Resolve the child's HOME (sandbox user may be `daytona` or `root` depending on image).
CHILD_HOME=$(daytona exec "$NAME" -- bash -lc 'printf %s "$HOME"' 2>/dev/null || echo "/home/daytona")
[ -n "$CHILD_HOME" ] || CHILD_HOME=/home/daytona

# Upload constitution + heartbeat tarball + bootstrap script via `exec ... -- cat > /tmp/X`.
daytona exec "$NAME" -- bash -c "cat > /tmp/CONSTITUTION.md" < "$CONSTITUTION"
daytona exec "$NAME" -- bash -c "cat > /tmp/heartbeat-skill.tar.gz" < "$HEARTBEAT_TGZ"
daytona exec "$NAME" -- bash -c "cat > /tmp/child-bootstrap.sh" < "$SKILL_DIR/scripts/host-daytona/child-bootstrap.sh"
daytona exec "$NAME" -- chmod +x /tmp/child-bootstrap.sh

# The child's private key NEVER becomes an environment variable. Stream the entire wallet
# JSON to /tmp/wallet.json via stdin (no argv exposure, no shell history) at umask 077;
# child-bootstrap.sh reads it from disk, then shred -u's the staged copy.
W_ADDR=$("$JQ" -r '.address' "$WALLET_JSON")
cat "$WALLET_JSON" | daytona exec "$NAME" -- bash -c 'umask 077; cat > /tmp/wallet.json && chmod 600 /tmp/wallet.json'

# Run bootstrap — WALLET_PRIVATE_KEY is INTENTIONALLY ABSENT from env. Non-secret values
# (name, sha, address, hermes git pin) ride as env; the bootstrap reads the key from /tmp.
daytona exec "$NAME" -- bash -c "
  set -e
  export CHILD_NAME='$NAME'
  export CONSTITUTION_SHA='$CONSTITUTION_SHA'
  export WALLET_ADDRESS='$W_ADDR'
  export HERMES_GIT_URL='$HERMES_GIT_URL'
  export HERMES_GIT_REF='$HERMES_GIT_REF'
  export HERMES_EXPECT_VERSION='$HERMES_EXPECT_VERSION'
  /tmp/child-bootstrap.sh
"

echo "provision: $NAME bootstrap returned OK; sandbox_id=$SB_ID home=$CHILD_HOME"
echo "SANDBOX_ID=$SB_ID"
echo "CHILD_HOME=$CHILD_HOME"
