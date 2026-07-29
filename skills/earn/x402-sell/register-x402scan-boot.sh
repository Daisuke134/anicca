#!/usr/bin/env bash
# register-x402scan-boot.sh — run x402scan SIWX registration from a dependency-complete copy.
# Runtime skill sync deliberately excludes node_modules; on local instances the canonical repo
# retains @x402/extensions, so use that copy exactly as seller-boot-v2.sh already does for serving.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -d "$DIR/node_modules/@x402/extensions" ]; then
  REPO="${ANICCA_REPO:-${LIFE_MANAGER_REPO:-$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null)}}"
  [ -d "$REPO/skills/earn/x402-sell/node_modules/@x402/extensions" ] \
    && DIR="$REPO/skills/earn/x402-sell"
fi
exec /usr/bin/env node "$DIR/register-x402scan.mjs"
