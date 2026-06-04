#!/usr/bin/env bash
# Spawn a sovereign Anicca child instance.
# Usage:
#   spawn-child.sh [--dry-run] [--host=daytona] [--confirm] <name>
# --confirm: explicit intent marker for autonomous (unattended) real spawns, e.g. the
#            #327c spawn-watcher cron. Accepted-but-optional for interactive CLI use.
# Exit codes:
#   0  success (sandbox up, heartbeat fired, colony row written)
#   64 bad input (preflight failed)
#   75 cost cap not met (wallet < $5 USDC)
#   1  other error (provision/bootstrap failed; sandbox MAY exist — caller must investigate)
set -euo pipefail
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=0
HOST=daytona
NAME=""
CONFIRM=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --host=*)  HOST="${1#--host=}"; shift ;;
    --confirm) CONFIRM=1; shift ;;
    --help)    sed -n '1,18p' "$0"; exit 0 ;;
    -*)        echo "spawn-child: unknown flag $1" >&2; exit 64 ;;
    *)         NAME="$1"; shift ;;
  esac
done

[ "$HOST" = "daytona" ] || { echo "spawn-child: host=$HOST not implemented in Wave 1 (Daytona only)" >&2; exit 64; }

# 1) Preflight (cost cap, env, name validation, duplicate check).
#    Dry-run skips the cost cap (it never spends) but still validates name/env/duplicate.
SPAWN_DRY_RUN="$DRY_RUN" "$SKILL_DIR/scripts/preflight.sh" "$NAME" >/dev/null

# 2) Compute constitution hash ONCE (mid-spawn edits land in the NEXT spawn, not this one)
SHA=$("$SKILL_DIR/scripts/colony/constitution-hash.sh")

# 3) DRY RUN — never touch wallet or Daytona API
if [ "$DRY_RUN" = "1" ]; then
  DRY_RUN=1 "$SKILL_DIR/scripts/host-daytona/provision.sh" "$NAME" /dev/null \
    /Users/anicca/anicca-oss/CONSTITUTION.md "$SHA"
  exit 0
fi

# 4) Generate child wallet (secret; 600-perm temp file under ~/.hermes/state)
mkdir -p /Users/anicca/.hermes/state
WALLET_TMP=$(mktemp /Users/anicca/.hermes/state/.tmp-childwallet-XXXX.json)
trap 'shred -u "$WALLET_TMP" 2>/dev/null || rm -f "$WALLET_TMP"' EXIT
umask 077
"$SKILL_DIR/scripts/colony/gen-wallet.sh" > "$WALLET_TMP"
chmod 600 "$WALLET_TMP"
ADDR=$("$JQ" -r '.address' "$WALLET_TMP")

# 5) Append PROVISIONAL row to colony so we never lose track of the spawn even if step 6 fails
COLONY=/Users/anicca/.hermes/state/colony.jsonl
"$SKILL_DIR/scripts/colony/append.sh" \
  "$NAME" "$HOST" "PENDING" "$ADDR" "$SHA" "provisioning" >/dev/null

# If provisioning fails, flip the dangling provisional row to "failed" (do not leave it
# stuck at "provisioning") so the ledger stays honest. Single-writer last-line rewrite.
mark_failed() {
  local reason="$1"
  local tmp; tmp=$(mktemp /Users/anicca/.hermes/state/.tmp-colony-XXXX)
  head -n $(( $(wc -l < "$COLONY") - 1 )) "$COLONY" > "$tmp"
  tail -n 1 "$COLONY" | "$JQ" -c --arg r "$reason" '.status="failed" | .fail_reason=$r' >> "$tmp"
  mv "$tmp" "$COLONY"
}

# 6) Provision the sandbox + boot the child
if ! OUT=$("$SKILL_DIR/scripts/host-daytona/provision.sh" "$NAME" "$WALLET_TMP" \
       /Users/anicca/anicca-oss/CONSTITUTION.md "$SHA"); then
  mark_failed "provision.sh failed (see stderr above)"
  echo "spawn-child: provisioning failed for $NAME — colony row marked failed" >&2
  exit 1
fi
echo "$OUT"
SB_ID=$(echo "$OUT" | awk -F= '/^SANDBOX_ID=/{print $2}')
CHILD_HOME=$(echo "$OUT" | awk -F= '/^CHILD_HOME=/{print $2}')
[ -n "$CHILD_HOME" ] || CHILD_HOME=/home/daytona

# 7) Promote the colony row from provisioning to alive (single-writer; safe last-line rewrite)
TMP=$(mktemp /Users/anicca/.hermes/state/.tmp-colony-XXXX)
head -n $(( $(wc -l < "$COLONY") - 1 )) "$COLONY" > "$TMP"
LAST=$(tail -n 1 "$COLONY" | "$JQ" -c --arg sb "$SB_ID" --arg ch "$CHILD_HOME" '.sandbox_id=$sb | .child_home=$ch | .status="alive"')
printf '%s\n' "$LAST" >> "$TMP"
mv "$TMP" "$COLONY"

echo "spawn-child: $NAME alive on $HOST as $SB_ID (wallet $ADDR, home $CHILD_HOME, confirm=$CONFIRM)"
