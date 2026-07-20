#!/usr/bin/env bash
set -euo pipefail

PROJECT_REPO=${ANICCA_PROJECT_REPO:-"$HOME/anicca-project"}
COLONY_STATUS=${COLONY_STATUS_SCRIPT:-"$HOME/anicca/skills/self/colony-status.sh"}
OUTPUT="$PROJECT_REPO/docs/STATUS-live.md"

if [[ ! -f "$COLONY_STATUS" ]]; then
  printf 'colony status script missing: %s\n' "$COLONY_STATUS" >&2
  exit 1
fi

tmp=$(mktemp "${TMPDIR:-/tmp}/anicca-status.XXXXXX")
trap 'rm -f "$tmp"' EXIT

if ! status_output=$(bash "$COLONY_STATUS"); then
  printf 'colony status command failed: %s\n' "$COLONY_STATUS" >&2
  exit 1
fi

{
  printf '# Anicca Colony — Live Status\n\n'
  # Markdown backticks are literals in these printf format strings.
  # shellcheck disable=SC2016
  printf '> Generated from `%s` at `%s`. This is measured output, not a self-report.\n\n' \
    "$COLONY_STATUS" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  # shellcheck disable=SC2016
  printf '```text\n%s\n```\n' "$status_output"
} >"$tmp"

mkdir -p "$(dirname "$OUTPUT")"
mv "$tmp" "$OUTPUT"
trap - EXIT
