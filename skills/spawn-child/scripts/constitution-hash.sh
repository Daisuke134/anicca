#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# constitution-hash.sh — boot-time integrity check for anicca-N instances.
#
# Anicca-002 (and any child) clones the anicca-oss CONSTITUTION.md at boot and
# computes its SHA-256. If the hash diverges from EXPECTED_CONSTITUTION_HASH
# (= the value baked at image build time OR fetched from anicca-001 peer-api),
# boot aborts with code 30 — a child cannot run a constitution it didn't accept.

set -euo pipefail

REPO_URL="${CONSTITUTION_REPO:-https://github.com/Daisuke134/anicca-oss.git}"
EXPECTED="${EXPECTED_CONSTITUTION_HASH:-}"
WORK="${TMPDIR:-/tmp}/constitution-check-$$"

mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

# Sparse-checkout single file to avoid pulling the whole repo on every boot.
git -C "$WORK" init --quiet
git -C "$WORK" remote add origin "$REPO_URL"
git -C "$WORK" config core.sparseCheckout true
echo "CONSTITUTION.md" > "$WORK/.git/info/sparse-checkout"
if ! git -C "$WORK" pull --quiet --depth 1 origin main >/dev/null 2>&1; then
  echo "constitution-hash: git pull failed from $REPO_URL" >&2
  exit 20
fi

if [[ ! -f "$WORK/CONSTITUTION.md" ]]; then
  echo "constitution-hash: CONSTITUTION.md not found in repo" >&2
  exit 21
fi

ACTUAL=$(shasum -a 256 "$WORK/CONSTITUTION.md" | awk '{print $1}')

if [[ -n "$EXPECTED" && "$ACTUAL" != "$EXPECTED" ]]; then
  echo "constitution-hash: MISMATCH" >&2
  echo "  expected: $EXPECTED" >&2
  echo "  actual:   $ACTUAL" >&2
  exit 30
fi

echo "constitution-hash: OK $ACTUAL"
exit 0
