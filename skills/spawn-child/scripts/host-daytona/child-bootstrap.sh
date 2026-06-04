#!/usr/bin/env bash
# Runs INSIDE the Daytona sandbox (Ubuntu) as the FIRST command.
#
# Child uses plain `jq` (Ubuntu /usr/bin/jq), NEVER /opt/homebrew/bin/jq (macOS-only).
# WALLET_PRIVATE_KEY is NOT read from the environment. Parent writes /tmp/wallet.json (0600)
#   before invoking us; we read it from disk, never via `export`.
# Hermes is pinned to the SAME git commit the parent runs (HERMES_GIT_REF); the upstream
#   PyPI `hermes-agent` is an unrelated package line, so we install from git to match exactly.
#
# Expects in env (NOT WALLET_PRIVATE_KEY):
#   $CHILD_NAME, $CONSTITUTION_SHA, $WALLET_ADDRESS,
#   $HERMES_GIT_URL, $HERMES_GIT_REF, $HERMES_EXPECT_VERSION
# Expects on disk (staged by parent BEFORE this runs):
#   /tmp/CONSTITUTION.md, /tmp/heartbeat-skill.tar.gz, /tmp/wallet.json (0600)
# Exits 7 if constitution hash mismatches.
set -euo pipefail

HOME_DIR=$HOME
mkdir -p "$HOME_DIR/.hermes/state" "$HOME_DIR/.hermes/skills"

# 0) Ensure jq is on PATH; install via apt-get if missing.
if ! command -v jq >/dev/null 2>&1; then
  sudo apt-get update -qq && sudo apt-get install -y -qq jq || { apt-get update -qq && apt-get install -y -qq jq; }
fi
JQ=$(command -v jq)  # plain `jq` — Ubuntu /usr/bin/jq

# 1) Verify constitution hash BEFORE doing anything else
ACTUAL_SHA=$(sha256sum /tmp/CONSTITUTION.md | awk '{print $1}')
if [ "$ACTUAL_SHA" != "$CONSTITUTION_SHA" ]; then
  echo "child-bootstrap: CONSTITUTION HASH MISMATCH ($ACTUAL_SHA != $CONSTITUTION_SHA) — refusing to boot" >&2
  exit 7
fi
cp /tmp/CONSTITUTION.md "$HOME_DIR/.hermes/AGENTS.md"
echo "$CONSTITUTION_SHA" > "$HOME_DIR/.hermes/state/constitution.sha"

# 2) Install minimal deps: Python 3, pip, venv, git, curl
if ! command -v python3 >/dev/null || ! command -v git >/dev/null || ! command -v pip3 >/dev/null; then
  (sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv git curl) \
    || (apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv git curl)
fi

# 3) Install Hermes — PINNED to the parent's exact git commit (cross-plan rule X1).
#    PyPI `hermes-agent` is a DIFFERENT package line; installing from git@<ref> guarantees
#    parent/child parity. If the ref disappears upstream, this exits non-zero and a new plan re-pins.
HERMES_VENV="$HOME_DIR/.hermes/venv"
python3 -m venv "$HERMES_VENV"
"$HERMES_VENV/bin/pip" install --quiet --upgrade pip
"$HERMES_VENV/bin/pip" install --quiet "git+${HERMES_GIT_URL}@${HERMES_GIT_REF}"
HERMES_BIN="$HERMES_VENV/bin/hermes"
[ -x "$HERMES_BIN" ] || { echo "child-bootstrap: hermes install from git did not produce a binary" >&2; exit 1; }
"$HERMES_BIN" --version 2>&1 | grep -E "${HERMES_EXPECT_VERSION//./\\.}" \
  || { echo "child-bootstrap: hermes version != ${HERMES_EXPECT_VERSION} — drift, refusing" >&2; exit 1; }
ln -snf "$HERMES_BIN" "$HOME_DIR/.local/bin/hermes" 2>/dev/null || { mkdir -p "$HOME_DIR/.local/bin"; ln -snf "$HERMES_BIN" "$HOME_DIR/.local/bin/hermes"; }

# 4) Install the heartbeat skill
mkdir -p "$HOME_DIR/.hermes/skills/anicca-heartbeat"
tar -xzf /tmp/heartbeat-skill.tar.gz -C "$HOME_DIR/.hermes/skills/anicca-heartbeat"
chmod +x "$HOME_DIR/.hermes/skills/anicca-heartbeat/scripts/"*.sh

# 5) Move the child's wallet from /tmp (parent placed it there, 0600) to ~/.hermes/state.
[ -f /tmp/wallet.json ] || { echo "child-bootstrap: /tmp/wallet.json missing (parent did not stage wallet)" >&2; exit 1; }
WALLET_PRIVATE_KEY=$("$JQ" -r '.private_key' /tmp/wallet.json)
[[ "$WALLET_PRIVATE_KEY" =~ ^0x[a-f0-9]{64}$ ]] \
  || { echo "child-bootstrap: wallet.json private_key not 0x-prefixed 64-hex — refusing" >&2; exit 1; }

umask 077
"$JQ" -n \
  --arg address "$WALLET_ADDRESS" \
  --arg private_key "$WALLET_PRIVATE_KEY" \
  '{address:$address, private_key:$private_key, balance_usdc:0}' \
  > "$HOME_DIR/.hermes/state/wallet.json"
chmod 600 "$HOME_DIR/.hermes/state/wallet.json"

unset WALLET_PRIVATE_KEY
shred -u /tmp/wallet.json 2>/dev/null || rm -f /tmp/wallet.json

# 6) Write child identity
cat > "$HOME_DIR/.hermes/state/identity.json" <<JSON
{"name":"$CHILD_NAME","generation":1,"parent":"genesis","host":"daytona","spawned_at":"$(date -u +%FT%TZ)","hermes_version":"${HERMES_EXPECT_VERSION}"}
JSON

# 7) Fire heartbeat ONCE synchronously so parent can verify within 10 min.
#    heartbeat.sh + lifeline-check.sh read STATE_DIR / HERMES_BIN / CONSTITUTION from env.
STATE_DIR="$HOME_DIR/.hermes/state" HERMES_BIN="$HERMES_BIN" \
  CONSTITUTION="$HOME_DIR/.hermes/AGENTS.md" \
  "$HOME_DIR/.hermes/skills/anicca-heartbeat/scripts/heartbeat.sh"

# 8) Serve the state dir over :8080 so the parent can read heartbeat via a Daytona-public URL
#    (sovereignty proof, DoD #10). Best-effort background server; failure does NOT block boot.
( cd "$HOME_DIR/.hermes/state" && nohup python3 -m http.server 8080 >/dev/null 2>&1 & ) || \
  echo "child-bootstrap: heartbeat http server deferred"

# 9) Schedule recurring heartbeat (best-effort; failure here does NOT block boot)
"$HERMES_BIN" cron create "every 30m" \
  --name anicca-heartbeat \
  --script "$HOME_DIR/.hermes/skills/anicca-heartbeat/scripts/heartbeat.sh" \
  --no-agent 2>/dev/null || echo "cron schedule deferred — parent will retry"

echo "child-bootstrap: OK $CHILD_NAME at $(date -u +%FT%TZ)"
