#!/usr/bin/env bash
set -euo pipefail

RELEASE_ROOT="${ANICCA_RELEASE_ROOT:-$HOME/loops/life-manager}"
REPO="${ANICCA_REPO:-${LIFE_MANAGER_REPO:-$RELEASE_ROOT/current}}"
case "$REPO" in
  */.worktrees/*)
    echo "agent-economy: refusing worktree runtime path: $REPO" >&2
    exit 2
    ;;
esac

die() { echo "agent-economy: $*" >&2; exit 2; }

CURRENT_LINK="$RELEASE_ROOT/current"
[ "$REPO" = "$CURRENT_LINK" ] || die "runtime must resolve through $CURRENT_LINK"
[ -L "$CURRENT_LINK" ] || die "namespaced current pointer is missing: $CURRENT_LINK"
[ -d "$RELEASE_ROOT/releases" ] || die "namespaced releases root is missing: $RELEASE_ROOT/releases"
RELEASE="$(cd "$REPO" 2>/dev/null && pwd -P)" || die "current release target cannot be resolved"
RELEASES="$(cd "$RELEASE_ROOT/releases" 2>/dev/null && pwd -P)" || die "namespaced releases root cannot be resolved"
case "$RELEASE" in
  "$RELEASES"/*) ;;
  *) die "current release escapes the namespaced releases root" ;;
esac
[ -f "$RELEASE/RELEASE.json" ] && [ ! -L "$RELEASE/RELEASE.json" ] \
  || die "sealed release metadata is missing: $RELEASE/RELEASE.json"

METADATA_FIELDS="$(node - "$RELEASE/RELEASE.json" "$RELEASE" "$RELEASE_ROOT" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
const [metadataPath, releasePath, releaseRoot] = process.argv.slice(2);
let metadata;
try { metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8')); } catch { process.exit(2); }
const real = (value) => fs.realpathSync.native(value);
if (!metadata || typeof metadata !== 'object') process.exit(3);
if (metadata.namespace !== 'life-manager') process.exit(4);
if (real(String(metadata.release_root || '')) !== real(releaseRoot)) process.exit(5);
if (metadata.release_id !== path.basename(releasePath)) process.exit(6);
if (!/^[0-9a-f]{40}$/.test(String(metadata.sha || ''))) process.exit(7);
if (!(path.basename(releasePath) === metadata.sha || path.basename(releasePath).endsWith(`-${metadata.sha.slice(0, 8)}`))) process.exit(8);
if (metadata.current && real(String(metadata.current)) !== real(path.join(releaseRoot, 'current'))) process.exit(9);
process.stdout.write(`${metadata.release_id}\t${metadata.sha}`);
NODE
)" || die "sealed release metadata is invalid"
IFS=$'\t' read -r RELEASE_ID RELEASE_SHA <<EOF
$METADATA_FIELDS
EOF

if [ -n "${ANICCA_RELEASE_ID:-}" ] && [ "$ANICCA_RELEASE_ID" != "$RELEASE_ID" ]; then
  die "release id does not match sealed metadata"
fi
if [ -n "${ANICCA_RELEASE_SHA:-}" ] && [ "$ANICCA_RELEASE_SHA" != "$RELEASE_SHA" ]; then
  die "release sha does not match sealed metadata"
fi

mode="$(stat -f '%Lp' "$RELEASE" 2>/dev/null || stat -c '%a' "$RELEASE" 2>/dev/null)" \
  || die "could not inspect sealed release permissions"
[ $((8#$mode & 0222)) -eq 0 ] || die "sealed release remains writable"
while IFS= read -r -d '' item; do
  case "$item" in
    "$RELEASE/state/effective-cron"|"$RELEASE/state/effective-cron"/*) continue ;;
  esac
  [ -L "$item" ] && continue
  mode="$(stat -f '%Lp' "$item" 2>/dev/null || stat -c '%a' "$item" 2>/dev/null)" \
    || die "could not inspect sealed release permissions"
  [ $((8#$mode & 0222)) -eq 0 ] || die "sealed release remains writable"
done < <(find "$RELEASE" -mindepth 1 -print0)

[ -x "$REPO/runtime/anicca-daemon.sh" ] || die "missing daemon at $REPO/runtime/anicca-daemon.sh"

export ANICCA_REPO="$REPO"
export ANICCA_RELEASE_ROOT
export ANICCA_RELEASE_ID="$RELEASE_ID" ANICCA_RELEASE_SHA="$RELEASE_SHA"
if [ "${ANICCA_ECONOMY_CREATE_EVM_WALLET:-0}" = "1" ]; then
  /usr/bin/env node "$REPO/runtime/compute-proxy/ensure-wallet.mjs" >/dev/null
fi
exec /bin/bash "$REPO/runtime/anicca-daemon.sh"
