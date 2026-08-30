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
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOOPS_ROOT="${LOOPS_ROOT:-$HOME/loops}"
RELEASES="$LOOPS_ROOT/releases"
CURRENT="$LOOPS_ROOT/current"
# state root is intentionally not resolved here (see RELEASE.json note below)
KEEP="${LOOPS_KEEP_RELEASES:-5}"
REF="${1:-HEAD}"

die() { echo "cut-loop-release: $*" >&2; exit 1; }

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

cat >"$DEST/RELEASE.json" <<EOF
{
  "sha": "$SHA",
  "ref": "$REF",
  "provenance": "$PROVENANCE",
  "cut_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "repo": "$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null)",
  "state_root": "${LOOPS_STATE_ROOT:-set per loop by its launchd job, not by this release}"
}
EOF

# One writable carve-out, created before the export is sealed. The CEO registry gate writes the
# cadence it just computed to state/effective-cron/<loop>.txt, resolved relative to the repo root --
# which is this release. A fully read-only export made every pass log a permission error before
# failing open. That file is derived from the registry on each pass, so it is scratch rather than
# state worth preserving, and one writable directory costs nothing while the code stays immutable.
mkdir -p "$DEST/state/effective-cron"

chmod -R a-w "$DEST" 2>/dev/null || true
chmod -R u+w "$DEST/state" 2>/dev/null || true

# rename(2) over an existing symlink is atomic, so no pass can ever observe a missing `current`.
# -h is load-bearing: without it mv follows `current` into the directory it points at and creates
# the new link INSIDE the old release instead of replacing it.
ln -sfn "$DEST" "$CURRENT.swap" && mv -fh "$CURRENT.swap" "$CURRENT" || die "could not move the current symlink"

# Keep a few older releases so rollback is a symlink move rather than a rebuild.
ls -1dt "$RELEASES"/*/ 2>/dev/null | tail -n +$((KEEP + 1)) | while IFS= read -r old; do
  [ "$(readlink "$CURRENT")" = "${old%/}" ] && continue
  # An installed launchd job pins its release by absolute path, so deleting one still referenced
  # turns every one of its lanes into exit 78 EX_CONFIG. Measured 2026-08-31: pruning stranded 132
  # of 182 agents, including all seven Coconala lanes. Keep the release; `lm-loop apply` is what
  # moves the pins forward, and until it runs the pin is the only thing keeping the lane runnable.
  if grep -qls -- "${old%/}/" "$HOME/Library/LaunchAgents"/*.plist 2>/dev/null; then
    echo "cut-loop-release: kept $(basename "${old%/}") (an installed launchd job still pins it)"
    continue
  fi
  chmod -R u+w "$old" 2>/dev/null || true
  rm -rf "$old"
  echo "cut-loop-release: pruned $(basename "${old%/}")"
done

echo "current -> $(readlink "$CURRENT")  ($PROVENANCE)"
