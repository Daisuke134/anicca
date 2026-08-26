#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)"
CODE_ROOT="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd -P)" || {
  echo "agent-economy: immutable release could not be resolved" >&2
  exit 2
}
RELEASE_ROOT="${ANICCA_RELEASE_ROOT:-$(cd "$CODE_ROOT/../.." 2>/dev/null && pwd -P)}"
REPO="${ANICCA_REPO:-$CODE_ROOT}"
case "$CODE_ROOT" in
  */.worktrees/*)
    echo "agent-economy: refusing worktree runtime path: $CODE_ROOT" >&2
    exit 2
    ;;
esac

die() { echo "agent-economy: $*" >&2; exit 2; }

[ -d "$RELEASE_ROOT/releases" ] || die "namespaced releases root is missing: $RELEASE_ROOT/releases"
RELEASE="$CODE_ROOT"
[ "$REPO" = "$CODE_ROOT" ] || die "runtime repository must be the executing release"
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
const crypto = require('node:crypto');
const [metadataPath, releasePath, releaseRoot] = process.argv.slice(2);
let metadata;
try { metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8')); } catch { process.exit(2); }
const real = (value) => fs.realpathSync.native(value);
if (!metadata || typeof metadata !== 'object') process.exit(3);
if (metadata.namespace !== 'life-manager') process.exit(4);
if (real(String(metadata.release_root || '')) !== real(releaseRoot)) process.exit(5);
if (metadata.release_id !== path.basename(releasePath)) process.exit(6);
if (!/^[0-9a-f]{40}$/.test(String(metadata.sha || ''))) process.exit(7);
if (metadata.git_commit !== metadata.sha) process.exit(8);
if (!(path.basename(releasePath) === metadata.sha || path.basename(releasePath).endsWith(`-${metadata.sha.slice(0, 8)}`))) process.exit(9);
if (metadata.current && real(String(metadata.current)) !== real(path.join(releaseRoot, 'current'))) process.exit(10);
if (!/^[0-9a-f]{64}$/.test(String(metadata.source_manifest_sha256 || ''))) process.exit(11);
const entries = [];
const releaseReal = real(releasePath);
const walk = (directory, prefix = '') => {
  for (const name of fs.readdirSync(directory).sort()) {
    const absolute = path.join(directory, name);
    const relative = prefix ? `${prefix}/${name}` : name;
    if (relative === 'RELEASE.json' || relative === 'SOURCE-MANIFEST.json' || relative === 'DEPENDENCY-MANIFEST.tsv' || relative.startsWith('node_modules/')) continue;
    const item = fs.lstatSync(absolute);
    if (item.isDirectory()) walk(absolute, relative);
    else if (item.isFile()) entries.push({ mode: (item.mode & 0o555).toString(8).padStart(4, '0'), path: relative, sha256: crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex') });
    else if (item.isSymbolicLink()) {
      let targetReal;
      try { targetReal = real(absolute); } catch { process.exit(14); }
      if (!(targetReal === releaseReal || targetReal.startsWith(`${releaseReal}${path.sep}`))) process.exit(15);
      const target = fs.readlinkSync(absolute);
      entries.push({ mode: (item.mode & 0o555).toString(8).padStart(4, '0'), path: relative, sha256: crypto.createHash('sha256').update(target).digest('hex'), target });
    }
  }
};
walk(releasePath);
entries.sort((a, b) => a.path.localeCompare(b.path));
const manifestPath = path.join(releasePath, 'SOURCE-MANIFEST.json');
let manifestRaw;
try { manifestRaw = fs.readFileSync(manifestPath); } catch { process.exit(12); }
const expectedManifest = Buffer.from(JSON.stringify({ entries, version: 1 }) + '\n');
if (!manifestRaw.equals(expectedManifest) || crypto.createHash('sha256').update(manifestRaw).digest('hex') !== metadata.source_manifest_sha256) process.exit(13);
if (!/^[0-9a-f]{64}$/.test(String(metadata.dependency_tree_manifest_sha256 || ''))) process.exit(16);
const dependencyRoot = path.join(releasePath, 'node_modules');
if (!fs.existsSync(dependencyRoot) || fs.lstatSync(dependencyRoot).isSymbolicLink()) process.exit(19);
const dependencyReal = real(dependencyRoot);
const dependencyLines = [];
const walkDependencies = (directory, prefix = 'node_modules') => {
  for (const name of fs.readdirSync(directory).sort()) {
    const absolute = path.join(directory, name);
    const relative = `${prefix}/${name}`;
    const item = fs.lstatSync(absolute);
    if (item.isDirectory()) walkDependencies(absolute, relative);
    else if (item.isFile()) dependencyLines.push(`file\t${relative}\t${(item.mode & 0o555).toString(8)}\t${crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex')}\t-`);
    else if (item.isSymbolicLink()) {
      let target;
      try { target = fs.realpathSync.native(absolute); } catch { process.exit(20); }
      if (!(target === dependencyReal || target.startsWith(`${dependencyReal}${path.sep}`))) process.exit(21);
      dependencyLines.push(`symlink\t${relative}\t${(item.mode & 0o555).toString(8)}\t-\t${fs.readlinkSync(absolute)}`);
    }
  }
};
walkDependencies(dependencyRoot);
dependencyLines.sort((a, b) => Buffer.compare(Buffer.from(a.split('\t')[1]), Buffer.from(b.split('\t')[1])));
let dependencyManifest;
try { dependencyManifest = fs.readFileSync(path.join(releasePath, 'DEPENDENCY-MANIFEST.tsv')); } catch { process.exit(22); }
const expectedDependencies = Buffer.from(dependencyLines.length ? `${dependencyLines.join('\n')}\n` : '');
if (!dependencyManifest.equals(expectedDependencies) || crypto.createHash('sha256').update(dependencyManifest).digest('hex') !== metadata.dependency_tree_manifest_sha256) process.exit(23);
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
  [ -L "$item" ] && continue
  mode="$(stat -f '%Lp' "$item" 2>/dev/null || stat -c '%a' "$item" 2>/dev/null)" \
    || die "could not inspect sealed release permissions"
  [ $((8#$mode & 0222)) -eq 0 ] || die "sealed release remains writable"
done < <(find "$RELEASE" -mindepth 1 -print0)

[ -x "$REPO/runtime/anicca-daemon.sh" ] || die "missing daemon at $REPO/runtime/anicca-daemon.sh"

if [ "${ANICCA_VALIDATE_RELEASE_ONLY:-0}" = "1" ]; then
  echo "agent-economy: sealed release validation passed ($RELEASE_ID)"
  exit 0
fi

export ANICCA_REPO="$CODE_ROOT" ANICCA_CODE_ROOT="$CODE_ROOT"
export ANICCA_RELEASE_ROOT
export ANICCA_RELEASE_ID="$RELEASE_ID" ANICCA_RELEASE_SHA="$RELEASE_SHA"
if [ "${ANICCA_ECONOMY_CREATE_EVM_WALLET:-0}" = "1" ]; then
  /usr/bin/env node "$REPO/runtime/compute-proxy/ensure-wallet.mjs" >/dev/null
fi
exec /bin/bash "$REPO/runtime/anicca-daemon.sh"
