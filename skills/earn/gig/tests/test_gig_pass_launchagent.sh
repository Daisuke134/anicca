#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
LEGACY_PLIST="$ROOT/skills/earn/gig/launchd/ai.anicca.hf-gig-pass.plist"
APPLY_PLIST="$ROOT/skills/earn/gig/launchd/ai.anicca.hf-gig-apply-direct.plist"
REGISTRY="$ROOT/config/launchd/agents/gig.json"

# The old plist remains readable history until Storefront parity closes, but it
# is not an active control-plane owner.
test -f "$LEGACY_PLIST"
plutil -lint "$LEGACY_PLIST" >/dev/null
test "$(plutil -extract Label raw -o - "$LEGACY_PLIST")" = 'ai.anicca.hf-gig-pass'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"] // null' "$REGISTRY")" = 'null'

plutil -lint "$APPLY_PLIST" >/dev/null
test "$(plutil -extract Label raw -o - "$APPLY_PLIST")" = 'ai.anicca.hf-gig-apply-direct'
test "$(jq -r '.agents["ai.anicca.hf-gig-apply-direct"].desired_state' "$REGISTRY")" = 'enabled'

echo 'PASS: legacy pass is history only; Apply direct is the active registry owner'
