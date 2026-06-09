#!/usr/bin/env bash
# Shared helpers for anicca-swarm-exec (#337 P14, spec 18 §3 EXECUTION).
# Sourced by swarm-exec.sh. No top-level side effects beyond mkdir of the state dir.
# shellcheck shell=bash

JQ=/usr/bin/jq
STATE_DIR="${STATE_DIR:-$HOME/.hermes/state}"
LEDGER="$STATE_DIR/swarm-exec.jsonl"
LOG_DIR="$STATE_DIR/swarm-exec"
# Clone cache is overridable for tests; production = ~/.cache/anicca-clones (NEVER /tmp — HARD RULE).
SWARM_CLONE_ROOT="${SWARM_CLONE_ROOT:-$HOME/.cache/anicca-clones}"

mkdir -p "$STATE_DIR" "$LOG_DIR" "$SWARM_CLONE_ROOT"
touch "$LEDGER"

# se_id <string> → deterministic 16-hex id.
se_id() { printf '%s' "$1" | /usr/bin/shasum -a 256 | cut -c1-16; }

# se_parse_owner_repo <url> → echoes "owner/repo" (strips proto, host, .git, trailing slash).
# Handles https://github.com/o/r(.git) and file:///abs/path (→ basename as repo, parent as owner).
se_parse_owner_repo() {
  local url="$1"
  case "$url" in
    file://*)
      local p="${url#file://}"
      p="${p%/}"; p="${p%.git}"
      local repo owner
      repo="$(basename "$p")"
      owner="$(basename "$(dirname "$p")")"
      printf '%s/%s\n' "$owner" "$repo"
      ;;
    *)
      local rest="${url#*://}"        # drop scheme
      rest="${rest#*/}"              # drop host
      rest="${rest%/}"; rest="${rest%.git}"
      printf '%s\n' "$rest"
      ;;
  esac
}

# swarm_runner_for <task_id> → echoes the shell command to run INSIDE the isolated shell.
# Fail-closed: an unrecognized task_id emits a command that exits 65.
swarm_runner_for() {
  local tid="$1"
  case "$tid" in
    echo:*)   printf 'echo %q\n' "${tid#echo:}" ;;
    selftest) printf 'ls -la && git rev-parse HEAD\n' ;;
    *)        printf 'echo "no runner for task_id=%s" >&2; exit 65\n' "$tid" ;;
  esac
}

# se_log <json-line> → append one row to the ledger.
se_log() { printf '%s\n' "$1" >> "$LEDGER"; }
