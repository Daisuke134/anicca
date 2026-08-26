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
# Keep an explicitly supplied PATH first so contract tests can provide an isolated toolchain, then
# append the fixed macOS lookup locations used by launchd. The cutter has no executable-path env
# override; npm/node are always resolved through command lookup.
if [ -n "${PATH:-}" ]; then
  export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
else
  export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOOPS_ROOT="${LOOPS_ROOT:-$HOME/loops}"
RELEASES="$LOOPS_ROOT/releases"
CURRENT="$LOOPS_ROOT/current"
# state root is intentionally not resolved here (see RELEASE.json note below)
KEEP="${LOOPS_KEEP_RELEASES:-5}"
REF="${1:-HEAD}"
NPM_BIN="$(command -v npm 2>/dev/null || true)"
NODE_BIN="$(command -v node 2>/dev/null || true)"

die() { echo "cut-loop-release: $*" >&2; exit 1; }

[ -n "$NPM_BIN" ] || die "npm executable is unavailable"
[ -n "$NODE_BIN" ] || die "node executable is unavailable"

validate_release_node_modules() {
  local node_modules="$DEST/node_modules"
  [ -d "$node_modules" ] || die "dependency install produced no node_modules"
  [ ! -L "$node_modules" ] || die "release node_modules must be a directory"
  local link resolved
  while IFS= read -r -d '' link; do
    resolved="$(realpath "$link" 2>/dev/null)" \
      || die "dependency symlink cannot be resolved"
    case "$resolved" in
      "$node_modules"|"$node_modules"/*) ;;
      *) die "dependency symlink escapes release node_modules" ;;
    esac
  done < <(find "$node_modules" -type l -print0)
}

dependency_digest() {
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
      else
        kind="file"
        target="-"
        content_hash="$(shasum -a 256 "$file" | awk '{print $1}')" || exit 1
        mode="$(printf '%o' $((8#$mode & 0555)))"
      fi
      printf '%s\t%s\t%s\t%s\t%s\n' "$kind" "$file" "$mode" "$content_hash" "$target"
    done
  ) | shasum -a 256 | awk '{print $1}'
}

verify_release_seal() {
  local item mode
  while IFS= read -r -d '' item; do
    case "$item" in
      "$DEST/state"|"$DEST/state"/*) continue ;;
    esac
    mode="$(stat -f '%Lp' "$item" 2>/dev/null || stat -c '%a' "$item" 2>/dev/null)" \
      || die "could not inspect sealed release permissions"
    case "$mode" in
      ''|*[!0-7]*) die "invalid sealed release permissions" ;;
    esac
    if [ $((8#$mode & 0222)) -ne 0 ]; then
      die "sealed release remains writable"
    fi
  done < <(find "$DEST" -mindepth 1 -print0)
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
  "ref": "$REF",
  "provenance": "$PROVENANCE",
  "cut_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "repo": "$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null)",
  "state_root": "${LOOPS_STATE_ROOT:-set per loop by its launchd job, not by this release}",
  "lockfile_sha256": "$LOCKFILE_SHA256",
  "dependency_manifest_sha256": "$DEPENDENCY_MANIFEST_SHA256",
  "dependency_sha256": "$DEPENDENCY_SHA256",
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

# One writable carve-out, created before the export is sealed. The CEO registry gate writes the
# cadence it just computed to state/effective-cron/<loop>.txt, resolved relative to the repo root --
# which is this release. A fully read-only export made every pass log a permission error before
# failing open. That file is derived from the registry on each pass, so it is scratch rather than
# state worth preserving, and one writable directory costs nothing while the code stays immutable.
mkdir -p "$DEST/state/effective-cron"

chmod -R a-w "$DEST" || die "could not seal release permissions"
chmod -R u+w "$DEST/state" || die "could not open intended state carveout"
verify_release_seal

# rename(2) over an existing symlink is atomic, so no pass can ever observe a missing `current`.
# -h is load-bearing: without it mv follows `current` into the directory it points at and creates
# the new link INSIDE the old release instead of replacing it.
ln -sfn "$DEST" "$CURRENT.swap" && mv -fh "$CURRENT.swap" "$CURRENT" || die "could not move the current symlink"

# Keep a few older releases so rollback is a symlink move rather than a rebuild.
ls -1dt "$RELEASES"/*/ 2>/dev/null | tail -n +$((KEEP + 1)) | while IFS= read -r old; do
  [ "$(readlink "$CURRENT")" = "${old%/}" ] && continue
  chmod -R u+w "$old" 2>/dev/null || true
  rm -rf "$old"
  echo "cut-loop-release: pruned $(basename "${old%/}")"
done

echo "current -> $(readlink "$CURRENT")  ($PROVENANCE)"
