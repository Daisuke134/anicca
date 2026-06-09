#!/usr/bin/env bash
# Shared helpers for anicca-resurrection (#337 P14, spec 18 §3 RESURRECTION / sutando-style).
# Sourced by checkpoint.sh / restart.sh. No top-level side effects beyond mkdir of the state dir.
# shellcheck shell=bash

JQ=/usr/bin/jq
STATE_DIR="${STATE_DIR:-$HOME/.hermes/state}"
CHECKPOINTS_DIR="$STATE_DIR/checkpoints"
LEDGER="$STATE_DIR/resurrection.jsonl"
# Live Hermes home (read-only source for checkpoints); overridable for tests.
HERMES_LIVE_HOME="${HERMES_LIVE_HOME:-$HOME/.hermes}"

# Resolve the anicca-oss repo root from this skill (worktree- or merged-tree-safe).
RS_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RS_REPO_ROOT="$(cd "$RS_SKILL_DIR/../.." && pwd)"          # .../anicca-oss(.worktrees/...)

mkdir -p "$STATE_DIR" "$CHECKPOINTS_DIR"
touch "$LEDGER"

# rs_id <string> → deterministic 16-hex id.
rs_id() { printf '%s' "$1" | /usr/bin/shasum -a 256 | cut -c1-16; }

# rs_log <json-line> → append one row to the ledger.
rs_log() { printf '%s\n' "$1" >> "$LEDGER"; }

# rs_sha_file <path> → sha256 of a file, or "none" if missing.
rs_sha_file() {
  [ -f "$1" ] && /usr/bin/shasum -a 256 "$1" | cut -d' ' -f1 || echo "none"
}
