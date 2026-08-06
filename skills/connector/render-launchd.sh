#!/usr/bin/env bash
# Render-only native launchd contract. It never loads or changes a live label.
set -eu
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CANONICAL_REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"
OUTPUT_DIR=""
REPO_ROOT=""
LIFE_MANAGER_HOME=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --repo-root) REPO_ROOT="${2:-}"; shift 2 ;;
    --life-manager-home) LIFE_MANAGER_HOME="${2:-}"; shift 2 ;;
    *) printf 'Connector native renderer argument invalid\n' >&2; exit 2 ;;
  esac
done

case "$OUTPUT_DIR" in /*) ;; *) printf 'Connector native renderer output invalid\n' >&2; exit 2 ;; esac
case "$LIFE_MANAGER_HOME" in /*) ;; *) printf 'Connector native renderer home invalid\n' >&2; exit 2 ;; esac
[ -n "$REPO_ROOT" ] && [ "$REPO_ROOT" = "$CANONICAL_REPO_ROOT" ] || {
  printf 'Connector native renderer repository invalid\n' >&2
  exit 2
}
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
[ -n "$NODE_BIN" ] && [ -x "$NODE_BIN" ] || {
  printf 'Connector native renderer unavailable\n' >&2
  exit 2
}
normalize_absolute() {
  "$NODE_BIN" -e '
const fs = require("node:fs");
const path = require("node:path");
const input = process.argv[1];
if (typeof input !== "string" || !path.isAbsolute(input)) process.exit(2);
const resolved = path.resolve(input);
let existing = resolved;
const suffix = [];
while (!fs.existsSync(existing)) {
  const parent = path.dirname(existing);
  if (parent === existing) process.exit(2);
  suffix.unshift(path.basename(existing));
  existing = parent;
}
process.stdout.write(path.join(fs.realpathSync.native(existing), ...suffix));
' "$1"
}
OUTPUT_DIR="$(normalize_absolute "$OUTPUT_DIR")" || {
  printf 'Connector native renderer output invalid\n' >&2
  exit 2
}
LIFE_MANAGER_HOME="$(normalize_absolute "$LIFE_MANAGER_HOME")" || {
  printf 'Connector native renderer home invalid\n' >&2
  exit 2
}
LIVE_OUTPUT="$(normalize_absolute "$HOME/Library/LaunchAgents")" || {
  printf 'Connector native renderer unavailable\n' >&2
  exit 2
}
[ "$OUTPUT_DIR" != "/" ] || {
  printf 'Connector native renderer output invalid\n' >&2
  exit 2
}
[ "$OUTPUT_DIR" != "$LIVE_OUTPUT" ] || {
  printf 'Connector native renderer refuses live output\n' >&2
  exit 2
}

mkdir -p "$OUTPUT_DIR"
render() {
  template="$1"
  output="$2"
  sed \
    -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
    -e "s|__LIFE_MANAGER_HOME__|$LIFE_MANAGER_HOME|g" \
    "$template" > "$output"
}

TEMPLATES="$REPO_ROOT/apps/life-manager/launchd"
render "$TEMPLATES/ai.anicca.life-manager-connector-native.plist.template" \
  "$OUTPUT_DIR/ai.anicca.life-manager-connector-native.plist"
