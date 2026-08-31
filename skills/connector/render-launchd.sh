#!/usr/bin/env bash
# Render-only native launchd contract. It never loads or changes a live label.
set -eu
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CANONICAL_REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"
OUTPUT_DIR=""
REPO_ROOT=""
MR_BOT_HOME=""
CONNECTOR_ENV_FILE=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --repo-root) REPO_ROOT="${2:-}"; shift 2 ;;
    --mr-bot-home) MR_BOT_HOME="${2:-}"; shift 2 ;;
    --connector-env-file) CONNECTOR_ENV_FILE="${2:-}"; shift 2 ;;
    *) printf 'Connector native renderer argument invalid\n' >&2; exit 2 ;;
  esac
done

case "$OUTPUT_DIR" in /*) ;; *) printf 'Connector native renderer output invalid\n' >&2; exit 2 ;; esac
case "$MR_BOT_HOME" in /*) ;; *) printf 'Connector native renderer home invalid\n' >&2; exit 2 ;; esac
case "$CONNECTOR_ENV_FILE" in /*) ;; *) printf 'Connector native renderer env file invalid\n' >&2; exit 2 ;; esac
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
MR_BOT_HOME="$(normalize_absolute "$MR_BOT_HOME")" || {
  printf 'Connector native renderer home invalid\n' >&2
  exit 2
}
CONNECTOR_ENV_FILE="$(normalize_absolute "$CONNECTOR_ENV_FILE")" || {
  printf 'Connector native renderer env file invalid\n' >&2
  exit 2
}
[ -f "$CONNECTOR_ENV_FILE" ] || {
  printf 'Connector native renderer env file unavailable\n' >&2
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
  repo_root_escaped="$(printf '%s' "$REPO_ROOT" | sed 's/[&|\\]/\\&/g')"
  mr_bot_home_escaped="$(printf '%s' "$MR_BOT_HOME" | sed 's/[&|\\]/\\&/g')"
  connector_env_file_escaped="$(printf '%s' "$CONNECTOR_ENV_FILE" | sed 's/[&|\\]/\\&/g')"
  sed \
    -e "s|__REPO_ROOT__|$repo_root_escaped|g" \
    -e "s|__MR_BOT_HOME__|$mr_bot_home_escaped|g" \
    -e "s|__CONNECTOR_ENV_FILE__|$connector_env_file_escaped|g" \
    "$template" > "$output"
  if grep -Eq '__[A-Z][A-Z0-9_]*__' "$output"; then
    printf 'Connector native renderer placeholder unresolved\n' >&2
    exit 2
  fi
  plutil -lint "$output" >/dev/null || {
    printf 'Connector native renderer plist invalid\n' >&2
    exit 2
  }
}

TEMPLATES="$REPO_ROOT/apps/mr-bot/launchd"
render "$TEMPLATES/ai.anicca.mr-bot-connector-native.plist.template" \
  "$OUTPUT_DIR/ai.anicca.mr-bot-connector-native.plist"
