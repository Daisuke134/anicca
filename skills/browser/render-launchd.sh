#!/usr/bin/env bash
set -eu
umask 077
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CANONICAL_REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"
OUTPUT_DIR="" REPO_ROOT="" MR_BOT_HOME="" CLOAK_PYTHON="" DAILY_DRIVER_PROFILE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --repo-root) REPO_ROOT="${2:-}"; shift 2 ;;
    --mr-bot-home) MR_BOT_HOME="${2:-}"; shift 2 ;;
    --cloak-python) CLOAK_PYTHON="${2:-}"; shift 2 ;;
    --profile) DAILY_DRIVER_PROFILE="${2:-}"; shift 2 ;;
    *) printf 'Daily-driver renderer argument invalid\n' >&2; exit 2 ;;
  esac
done
for value in "$OUTPUT_DIR" "$REPO_ROOT" "$MR_BOT_HOME" "$CLOAK_PYTHON" "$DAILY_DRIVER_PROFILE"; do
  case "$value" in /*) ;; *) printf 'Daily-driver renderer path invalid\n' >&2; exit 2 ;; esac
done
[ "$REPO_ROOT" = "$CANONICAL_REPO_ROOT" ] || { printf 'Daily-driver renderer repository invalid\n' >&2; exit 2; }
[ -x "$CLOAK_PYTHON" ] || { printf 'Daily-driver renderer Python unavailable\n' >&2; exit 2; }
[ -d "$DAILY_DRIVER_PROFILE" ] || { printf 'Daily-driver renderer profile unavailable\n' >&2; exit 2; }
[ "$OUTPUT_DIR" != "/" ] && [ "$OUTPUT_DIR" != "$HOME/Library/LaunchAgents" ] || { printf 'Daily-driver renderer refuses live output\n' >&2; exit 2; }
escape() { printf '%s' "$1" | sed 's/[&|\\]/\\&/g'; }
mkdir -p "$OUTPUT_DIR"
output="$OUTPUT_DIR/ai.anicca.mr-bot-daily-driver.plist"
sed -e "s|__REPO_ROOT__|$(escape "$REPO_ROOT")|g" \
  -e "s|__MR_BOT_HOME__|$(escape "$MR_BOT_HOME")|g" \
  -e "s|__CLOAK_PYTHON__|$(escape "$CLOAK_PYTHON")|g" \
  -e "s|__DAILY_DRIVER_PROFILE__|$(escape "$DAILY_DRIVER_PROFILE")|g" \
  -e "s|__HOME__|$(escape "$HOME")|g" \
  "$REPO_ROOT/skills/browser/launchd/ai.anicca.mr-bot-daily-driver.plist.template" > "$output"
grep -Eq '__[A-Z][A-Z0-9_]*__' "$output" && { printf 'Daily-driver renderer placeholder unresolved\n' >&2; exit 2; }
plutil -lint "$output" >/dev/null || { printf 'Daily-driver renderer plist invalid\n' >&2; exit 2; }
