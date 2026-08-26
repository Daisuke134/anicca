#!/usr/bin/env bash
# cut-loop-release.sh — turn a commit into an immutable release that launchd can point at.
#
#   bash bin/cut-loop-release.sh [<ref>]        # default: HEAD
#
# Why this exists: 221 of the 241 launchd agents on this machine run their code straight out of a
# git working tree (measured 2026-08-17 via bin/launchd_inventory.py). A working tree follows
# whoever is working in it, so a branch switch deletes a scheduled job's code out from under it --
# which is exactly what happened to the x-repost loop that day.
#
# The shape is the one this house already uses for the gig lanes (~/gig/releases/<repo>/<sha>/) and
# the one Capistrano documents: releases accumulate under their own id, a single `current` symlink
# selects one, and rollback is moving that symlink back. 12-factor V puts it plainly -- "it is
# impossible to make changes to the code at runtime" -- which a chmod -R a-w export enforces
# literally rather than by convention.
#
# State is deliberately NOT inside a release: see LOOPS_STATE_ROOT below.
set -uo pipefail
# Resolve tools only from fixed trusted directories. The caller's PATH is intentionally ignored so
# a launchd environment or a poisoned shell cannot shadow npm/node with a bespoke executable.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOOPS_ROOT="${LOOPS_ROOT:-$HOME/loops}"
RELEASES="$LOOPS_ROOT/releases"
CURRENT="$LOOPS_ROOT/current"
PREVIOUS="$LOOPS_ROOT/previous"
STRICT_NAMESPACE=0
[ "$(basename "$LOOPS_ROOT")" = "life-manager" ] && STRICT_NAMESPACE=1
RELEASE_LOCK="$LOOPS_ROOT/.release-lock"
# state root is intentionally not resolved here (see RELEASE.json note below)
KEEP="${LOOPS_KEEP_RELEASES:-5}"
ROLLBACK=0
if [ "${1:-}" = "--rollback" ]; then
  [ "$#" -eq 1 ] || { echo "cut-loop-release: --rollback takes no ref" >&2; exit 2; }
  ROLLBACK=1
fi
REF="${1:-HEAD}"
TRUSTED_BIN_DIRS=(/opt/homebrew/bin /usr/local/bin /usr/bin /bin /usr/sbin /sbin)

resolve_trusted_tool() {
  local tool="$1" directory
  for directory in "${TRUSTED_BIN_DIRS[@]}"; do
    if [ -x "$directory/$tool" ]; then
      printf '%s\n' "$directory/$tool"
      return 0
    fi
  done
  return 1
}

NPM_BIN="$(resolve_trusted_tool npm 2>/dev/null || true)"
NODE_BIN="$(resolve_trusted_tool node 2>/dev/null || true)"

die() { echo "cut-loop-release: $*" >&2; exit 1; }

acquire_release_lock() {
  mkdir -p "$LOOPS_ROOT" || die "cannot create release root"
  while ! mkdir "$RELEASE_LOCK" 2>/dev/null; do
    local owner reclaim
    owner="$(cat "$RELEASE_LOCK/pid" 2>/dev/null || true)"
    case "$owner" in
      ''|*[!0-9]*) reclaim=1 ;;
      *) kill -0 "$owner" 2>/dev/null && die "release lock is held by pid $owner"; reclaim=1 ;;
    esac
    if [ "$reclaim" -eq 1 ]; then
      local stale="$RELEASE_LOCK.reclaim.$$"
      rm -rf "$stale" 2>/dev/null || true
      if mv "$RELEASE_LOCK" "$stale" 2>/dev/null; then
        rm -rf "$stale"
      fi
    fi
  done
  printf '%s\n' "$$" > "$RELEASE_LOCK/pid" || die "cannot record release lock owner"
  trap 'rm -f "$RELEASE_LOCK/pid" 2>/dev/null || true; rmdir "$RELEASE_LOCK" 2>/dev/null || true' EXIT
}

verify_release_seal_path() {
  local target="$1" item mode
  mode="$(stat -f '%Lp' "$target" 2>/dev/null || stat -c '%a' "$target" 2>/dev/null)" \
    || die "could not inspect sealed release permissions"
  if [ $((8#$mode & 0222)) -ne 0 ]; then
    die "sealed release remains writable"
  fi
  while IFS= read -r -d '' item; do
    [ -L "$item" ] && continue
    mode="$(stat -f '%Lp' "$item" 2>/dev/null || stat -c '%a' "$item" 2>/dev/null)" \
      || die "could not inspect sealed release permissions"
    case "$mode" in
      ''|*[!0-7]*) die "invalid sealed release permissions" ;;
    esac
    if [ $((8#$mode & 0222)) -ne 0 ]; then
      die "sealed release remains writable"
    fi
  done < <(find "$target" -mindepth 1 -print0)
}

validate_release_target() {
  local target="$1" root="$2" resolved releases_real metadata_path
  [ -d "$target" ] || die "release target is missing: $target"
  resolved="$(cd "$target" && pwd -P)" || die "release target cannot be resolved: $target"
  releases_real="$(cd "$root/releases" 2>/dev/null && pwd -P)" \
    || die "namespaced releases root is missing: $root/releases"
  case "$resolved" in
    "$releases_real"/*) ;;
    *) die "release target escapes namespaced releases root: $target" ;;
  esac
  metadata_path="$resolved/RELEASE.json"
  [ -f "$metadata_path" ] && [ ! -L "$metadata_path" ] \
    || die "release metadata is missing: $metadata_path"
  if [ "$STRICT_NAMESPACE" -eq 1 ]; then
    "$NODE_BIN" - "$metadata_path" "$resolved" "$root" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
const [metadataPath, releasePath, releaseRoot] = process.argv.slice(2);
let metadata;
try { metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8')); } catch { process.exit(2); }
if (!metadata || typeof metadata !== 'object') process.exit(3);
const real = (value) => fs.realpathSync.native(value);
if (real(String(metadata.release_root || '')) !== real(releaseRoot)) process.exit(4);
if (metadata.namespace !== 'life-manager') process.exit(5);
if (metadata.release_id !== path.basename(releasePath)) process.exit(6);
if (!/^[0-9a-f]{40}$/.test(String(metadata.sha || ''))) process.exit(7);
if (metadata.git_commit !== metadata.sha) process.exit(8);
if (!(path.basename(releasePath) === metadata.sha || path.basename(releasePath).endsWith(`-${metadata.sha.slice(0, 8)}`))) process.exit(9);
if (metadata.current && real(String(metadata.current)) !== real(path.join(releaseRoot, 'current'))) process.exit(10);
NODE
    [ "$?" -eq 0 ] || die "release metadata identity is invalid: $metadata_path"
    verify_release_seal_path "$resolved"
  fi
  printf '%s\n' "$resolved"
}

replace_link() {
  local link="$1" target="$2"
  local temporary="${link}.swap.$$"
  rm -f "$temporary"
  ln -s "$target" "$temporary" || return 1
  mv -fh "$temporary" "$link" || { rm -f "$temporary"; return 1; }
}

[ -n "$NODE_BIN" ] || die "node executable is unavailable"
acquire_release_lock

if [ "$ROLLBACK" -eq 1 ]; then
  [ -L "$CURRENT" ] || die "current release pointer is missing"
  [ -L "$PREVIOUS" ] || die "previous release pointer is missing"
  CURRENT_TARGET="$(readlink "$CURRENT")"
  PREVIOUS_TARGET="$(readlink "$PREVIOUS")"
  validate_release_target "$CURRENT" "$LOOPS_ROOT" >/dev/null \
    || die "current release metadata is invalid"
  validate_release_target "$PREVIOUS" "$LOOPS_ROOT" >/dev/null \
    || die "previous release metadata is invalid"
  [ "$(cd "$CURRENT" && pwd -P)" != "$(cd "$PREVIOUS" && pwd -P)" ] \
    || die "current and previous already select the same release"
  replace_link "$CURRENT" "$PREVIOUS_TARGET" || die "could not move current release pointer"
  replace_link "$PREVIOUS" "$CURRENT_TARGET" || {
    replace_link "$CURRENT" "$CURRENT_TARGET" || true
    die "could not move previous release pointer"
  }
  POINTERS_OK=1
  if [ "${LOOPS_TEST_FAIL_ROLLBACK_READBACK:-0}" = "1" ]; then
    POINTERS_OK=0
  fi
  [ "$(readlink "$CURRENT")" = "$PREVIOUS_TARGET" ] || POINTERS_OK=0
  [ "$(readlink "$PREVIOUS")" = "$CURRENT_TARGET" ] || POINTERS_OK=0
  validate_release_target "$CURRENT" "$LOOPS_ROOT" >/dev/null || POINTERS_OK=0
  validate_release_target "$PREVIOUS" "$LOOPS_ROOT" >/dev/null || POINTERS_OK=0
  if [ "$POINTERS_OK" -ne 1 ]; then
    replace_link "$CURRENT" "$CURRENT_TARGET" || true
    replace_link "$PREVIOUS" "$PREVIOUS_TARGET" || true
    RESTORED_OK=1
    [ "$(readlink "$CURRENT")" = "$CURRENT_TARGET" ] || RESTORED_OK=0
    [ "$(readlink "$PREVIOUS")" = "$PREVIOUS_TARGET" ] || RESTORED_OK=0
    validate_release_target "$CURRENT" "$LOOPS_ROOT" >/dev/null || RESTORED_OK=0
    validate_release_target "$PREVIOUS" "$LOOPS_ROOT" >/dev/null || RESTORED_OK=0
    [ "$RESTORED_OK" -eq 1 ] || die "rollback restoration failed"
    die "rollback readback failed"
  fi
  echo "current -> $(readlink "$CURRENT") (rollback)"
  exit 0
fi

[ -n "$NPM_BIN" ] || die "npm executable is unavailable"

validate_release_node_modules() {
  local node_modules="$DEST/node_modules"
  [ -d "$node_modules" ] || die "dependency install produced no node_modules"
  [ ! -L "$node_modules" ] || die "release node_modules must be a directory"
  local node_modules_real
  node_modules_real="$(realpath "$node_modules" 2>/dev/null)" || die "release node_modules path cannot be resolved"
  local link resolved
  while IFS= read -r -d '' link; do
    resolved="$(realpath "$link" 2>/dev/null)" \
      || die "dependency symlink cannot be resolved"
    case "$resolved" in
      "$node_modules_real"|"$node_modules_real"/*) ;;
      *) die "dependency symlink escapes release node_modules" ;;
    esac
  done < <(find "$node_modules" -type l -print0)
}

dependency_entries() {
  (
    cd "$DEST" || exit 1
    find node_modules \( -type f -o -type l \) -print | LC_ALL=C sort | while IFS= read -r file; do
      local mode kind target content_hash
      mode="$(stat -f '%Lp' "$file" 2>/dev/null || stat -c '%a' "$file" 2>/dev/null)" \
        || exit 1
      if [ -L "$file" ]; then
        kind="symlink"
        target="$(readlink "$file")" || exit 1
        content_hash="-"
        mode="$(printf '%o' $((8#$mode & 0555)))"
      else
        kind="file"
        target="-"
        content_hash="$(shasum -a 256 "$file" | awk '{print $1}')" || exit 1
        mode="$(printf '%o' $((8#$mode & 0555)))"
      fi
      printf '%s\t%s\t%s\t%s\t%s\n' "$kind" "$file" "$mode" "$content_hash" "$target"
    done
  )
}

dependency_digest() {
  dependency_entries | shasum -a 256 | awk '{print $1}'
}

dependency_manifest() {
  local manifest="$DEST/DEPENDENCY-MANIFEST.tsv"
  dependency_entries > "$manifest" || die "could not create dependency manifest"
  DEPENDENCY_TREE_MANIFEST_SHA256="$(shasum -a 256 "$manifest" | awk '{print $1}')" \
    || die "could not digest dependency manifest"
}

source_manifest() {
  local manifest="$DEST/SOURCE-MANIFEST.json"
  SOURCE_MANIFEST_SHA256="$(python3 - "$DEST" "$manifest" <<'PY'
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = Path(sys.argv[2])
root_real = Path(os.path.realpath(root))
entries = []
for path in sorted(root.rglob("*")):
    relative = path.relative_to(root).as_posix()
    if relative in {"RELEASE.json", "SOURCE-MANIFEST.json", "DEPENDENCY-MANIFEST.tsv"} or relative.startswith("node_modules/"):
        continue
    item = path.lstat()
    if stat.S_ISREG(item.st_mode):
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append({"path": relative, "mode": format(stat.S_IMODE(item.st_mode) & 0o555, "04o"), "sha256": content_hash})
    elif stat.S_ISLNK(item.st_mode):
        target = os.readlink(path)
        target_real = Path(os.path.realpath(path))
        if target_real != root_real and root_real not in target_real.parents:
            raise SystemExit(f"source symlink escapes release: {relative}")
        content_hash = hashlib.sha256(target.encode()).hexdigest()
        entries.append({"path": relative, "mode": "0000", "sha256": content_hash, "target": target})
payload = {"version": 1, "entries": entries}
encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
manifest.write_bytes(encoded)
print(hashlib.sha256(encoded).hexdigest())
PY
)" || die "could not create source manifest"
}

verify_release_seal() {
  verify_release_seal_path "$DEST"
}

SHA="$(git -C "$REPO_ROOT" rev-parse "$REF" 2>/dev/null)" || die "cannot resolve ref '$REF'"
SHORT="${SHA:0:8}"

# A release nobody else can fetch is not reproducible, and the acceptance bar this house already
# applies to the gig lanes is that the installed SHA is an ancestor of origin/main.
if ! git -C "$REPO_ROOT" cat-file -e "$SHA^{commit}" 2>/dev/null; then
  die "$SHORT is not a commit"
fi
git -C "$REPO_ROOT" fetch --quiet origin 2>/dev/null || echo "cut-loop-release: WARNING fetch failed, ancestry check uses stale refs" >&2
if git -C "$REPO_ROOT" merge-base --is-ancestor "$SHA" origin/main 2>/dev/null; then
  PROVENANCE="ancestor-of-origin-main"
elif git -C "$REPO_ROOT" branch -r --contains "$SHA" 2>/dev/null | grep -q .; then
  PROVENANCE="pushed-not-yet-on-main"
  echo "cut-loop-release: NOTE $SHORT is pushed but not on origin/main yet" >&2
else
  die "$SHORT exists only locally -- push it before cutting a release"
fi

DEST="$RELEASES/$(date +%Y%m%dT%H%M%S)-$SHORT"
# Two safe release cuts can happen in one wall-clock second (for example, a deployment test followed
# immediately by a rollback fixture). Keep the timestamp-readable id while avoiding a collision.
if [ -e "$DEST" ]; then
  DEST="${DEST}-$$"
fi
[ -e "$DEST" ] && die "$DEST already exists"
# Only the release dir: each loop's state dir belongs to that loop's job, and creating a shared
# empty one here would advertise a location nothing actually writes to.
mkdir -p "$DEST" || die "cannot create $DEST"

# git archive exports the committed tree only: no .git, no untracked scratch, no local edits. That
# is the difference between "a copy of the commit" and "a copy of someone's desk".
if ! git -C "$REPO_ROOT" archive --format=tar "$SHA" | tar -x -C "$DEST"; then
  rm -rf "$DEST"
  die "export of $SHORT failed"
fi

# Record only the committed archive contents. Dependency installation and release metadata are
# generated afterwards and are intentionally excluded so source integrity remains reproducible.
source_manifest

# Dependencies are installed in the exported tree, never in the source checkout. `npm ci` is
# intentionally lockfile-fixed and scripts are disabled so a release cannot execute an unreviewed
# package hook while it is being assembled. The resulting release-local node_modules is what the
# resident runtime resolves (including viem); source node_modules is neither read nor copied.
if [ -f "$DEST/package.json" ] || [ -f "$DEST/package-lock.json" ]; then
  [ -f "$DEST/package.json" ] && [ -f "$DEST/package-lock.json" ] \
    || { rm -rf "$DEST"; die "release dependency manifests are incomplete"; }
  if ! (cd "$DEST" && "$NPM_BIN" ci --ignore-scripts --no-audit --no-fund); then
    rm -rf "$DEST"
    die "lockfile-fixed dependency install failed"
  fi
  LOCKFILE_SHA256="$(shasum -a 256 "$DEST/package-lock.json" | awk '{print $1}')" \
    || { rm -rf "$DEST"; die "could not digest package-lock.json"; }
  DEPENDENCY_MANIFEST_SHA256="$(shasum -a 256 "$DEST/package.json" | awk '{print $1}')" \
    || { rm -rf "$DEST"; die "could not digest package.json"; }
  validate_release_node_modules
  DEPENDENCY_SHA256="$(dependency_digest)" \
    || { rm -rf "$DEST"; die "could not digest installed dependencies"; }
  dependency_manifest
  NODE_VERSION="$("$NODE_BIN" --version 2>/dev/null)" \
    || { rm -rf "$DEST"; die "could not read node runtime version"; }
  NPM_VERSION="$("$NPM_BIN" --version 2>/dev/null)" \
    || { rm -rf "$DEST"; die "could not read npm runtime version"; }
else
  rm -rf "$DEST"
  die "release dependency manifests are missing"
fi

if ! cat >"$DEST/RELEASE.json" <<EOF
{
  "sha": "$SHA",
  "git_commit": "$SHA",
  "release_id": "$(basename "$DEST")",
  "release_root": "$LOOPS_ROOT",
  "namespace": "$(basename "$LOOPS_ROOT")",
  "current": "$CURRENT",
  "previous": "$PREVIOUS",
  "ref": "$REF",
  "provenance": "$PROVENANCE",
  "cut_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "repo": "$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null)",
  "state_root": "${LOOPS_STATE_ROOT:-set per loop by its launchd job, not by this release}",
  "lockfile_sha256": "$LOCKFILE_SHA256",
  "dependency_manifest_sha256": "$DEPENDENCY_MANIFEST_SHA256",
  "dependency_sha256": "$DEPENDENCY_SHA256",
  "dependency_tree_manifest_sha256": "$DEPENDENCY_TREE_MANIFEST_SHA256",
  "source_manifest_sha256": "$SOURCE_MANIFEST_SHA256",
  "runtime_versions": {
    "node": "$NODE_VERSION",
    "npm": "$NPM_VERSION"
  }
}
EOF
then
  rm -rf "$DEST"
  die "could not write RELEASE.json"
fi

chmod -R a-w "$DEST" || die "could not seal release permissions"
verify_release_seal

# rename(2) over an existing symlink is atomic, so no pass can ever observe a missing `current`.
# -h is load-bearing: without it mv follows `current` into the directory it points at and creates
# the new link INSIDE the old release instead of replacing it. Preserve the exact old target as
# `previous` before publishing the new release so rollback never rebuilds or guesses a SHA.
# Keep the old `ln -sfn` ordering rule in mind: create a sibling temporary link, then rename it.
OLD_PREVIOUS=""
OLD_PREVIOUS_PRESENT=0
if [ -L "$PREVIOUS" ]; then
  OLD_PREVIOUS="$(readlink "$PREVIOUS")"
  validate_release_target "$PREVIOUS" "$LOOPS_ROOT" >/dev/null \
    || die "previous release metadata is invalid"
  OLD_PREVIOUS_PRESENT=1
elif [ -e "$PREVIOUS" ]; then
  die "previous release pointer is not a symlink"
fi
EXPECTED_PREVIOUS="$OLD_PREVIOUS"
if [ -L "$CURRENT" ]; then
  OLD_CURRENT="$(readlink "$CURRENT")"
  validate_release_target "$CURRENT" "$LOOPS_ROOT" >/dev/null \
    || die "current release metadata is invalid"
  replace_link "$PREVIOUS" "$OLD_CURRENT" || die "could not move the previous release pointer"
  EXPECTED_PREVIOUS="$OLD_CURRENT"
elif [ -e "$CURRENT" ]; then
  die "current release pointer is not a symlink"
fi
if [ "${LOOPS_TEST_FAIL_CURRENT_SWAP:-0}" = "1" ]; then
  if [ "$OLD_PREVIOUS_PRESENT" -eq 1 ]; then
    replace_link "$PREVIOUS" "$OLD_PREVIOUS" || true
  else
    rm -f "$PREVIOUS"
  fi
  die "injected current swap failure"
fi
if ! replace_link "$CURRENT" "$DEST"; then
  if [ "$OLD_PREVIOUS_PRESENT" -eq 1 ]; then
    replace_link "$PREVIOUS" "$OLD_PREVIOUS" || true
  else
    rm -f "$PREVIOUS"
  fi
  die "could not move the current symlink"
fi
POINTERS_OK=1
if [ "${LOOPS_TEST_FAIL_POST_CURRENT_READBACK:-0}" = "1" ]; then
  POINTERS_OK=0
fi
[ "$(readlink "$CURRENT")" = "$DEST" ] || POINTERS_OK=0
validate_release_target "$CURRENT" "$LOOPS_ROOT" >/dev/null || POINTERS_OK=0
if [ -n "$EXPECTED_PREVIOUS" ]; then
  [ -L "$PREVIOUS" ] && [ "$(readlink "$PREVIOUS")" = "$EXPECTED_PREVIOUS" ] \
    && validate_release_target "$PREVIOUS" "$LOOPS_ROOT" >/dev/null || POINTERS_OK=0
else
  [ ! -e "$PREVIOUS" ] || POINTERS_OK=0
fi
if [ "$POINTERS_OK" -ne 1 ]; then
  if [ -n "${OLD_CURRENT:-}" ]; then
    replace_link "$CURRENT" "$OLD_CURRENT" || true
  else
    rm -f "$CURRENT"
  fi
  if [ "$OLD_PREVIOUS_PRESENT" -eq 1 ]; then
    replace_link "$PREVIOUS" "$OLD_PREVIOUS" || true
  else
    rm -f "$PREVIOUS"
  fi
  RESTORED_OK=1
  if [ -n "${OLD_CURRENT:-}" ]; then
    [ "$(readlink "$CURRENT")" = "$OLD_CURRENT" ] || RESTORED_OK=0
    validate_release_target "$CURRENT" "$LOOPS_ROOT" >/dev/null || RESTORED_OK=0
  else
    [ ! -e "$CURRENT" ] || RESTORED_OK=0
  fi
  if [ "$OLD_PREVIOUS_PRESENT" -eq 1 ]; then
    [ "$(readlink "$PREVIOUS")" = "$OLD_PREVIOUS" ] || RESTORED_OK=0
    validate_release_target "$PREVIOUS" "$LOOPS_ROOT" >/dev/null || RESTORED_OK=0
  else
    [ ! -e "$PREVIOUS" ] || RESTORED_OK=0
  fi
  [ "$RESTORED_OK" -eq 1 ] || die "release pointer restoration failed"
  die "release pointer readback failed"
fi

# Keep a few older releases so rollback is a symlink move rather than a rebuild.
ls -1dt "$RELEASES"/*/ 2>/dev/null | tail -n +$((KEEP + 1)) | while IFS= read -r old; do
  [ "$(readlink "$CURRENT")" = "${old%/}" ] && continue
  [ -L "$PREVIOUS" ] && [ "$(readlink "$PREVIOUS")" = "${old%/}" ] && continue
  chmod -R u+w "$old" 2>/dev/null || true
  rm -rf "$old"
  echo "cut-loop-release: pruned $(basename "${old%/}")"
done

echo "current -> $(readlink "$CURRENT")  ($PROVENANCE)"
