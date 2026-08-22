#!/usr/bin/env bash
# Render Capafy LaunchAgent templates without changing the live launchd domain.
set -eu
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CANONICAL_REPO_ROOT="$(cd "$HERE/../../../.." && pwd -P)"
OUTPUT_DIR=""
REPO_ROOT=""
LIFE_MANAGER_HOME=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --repo-root) REPO_ROOT="${2:-}"; shift 2 ;;
    --life-manager-home) LIFE_MANAGER_HOME="${2:-}"; shift 2 ;;
    *) printf 'Capafy launchd renderer argument invalid\n' >&2; exit 2 ;;
  esac
done

case "$OUTPUT_DIR" in /*) ;; *) printf 'Capafy launchd output invalid\n' >&2; exit 2 ;; esac
case "$LIFE_MANAGER_HOME" in /*) ;; *) printf 'Capafy launchd home invalid\n' >&2; exit 2 ;; esac
[ "$REPO_ROOT" = "$CANONICAL_REPO_ROOT" ] || {
  printf 'Capafy launchd repository invalid\n' >&2
  exit 2
}
[ "$OUTPUT_DIR" != "$HOME/Library/LaunchAgents" ] || {
  printf 'Capafy renderer refuses live output\n' >&2
  exit 2
}

mkdir -p "$OUTPUT_DIR"
repo_escaped="$(printf '%s' "$REPO_ROOT" | sed 's/[&|\\]/\\&/g')"
home_escaped="$(printf '%s' "$LIFE_MANAGER_HOME" | sed 's/[&|\\]/\\&/g')"

render() {
  template="$1"
  output="$OUTPUT_DIR/$(basename "$template")"
  sed -e "s|__REPO_ROOT__|$repo_escaped|g" \
    -e "s|__LIFE_MANAGER_HOME__|$home_escaped|g" \
    "$template" > "$output"
  ! grep -Eq '__[A-Z][A-Z0-9_]*__' "$output"
  /usr/bin/plutil -lint "$output" >/dev/null
}

for template in "$HERE"/ai.anicca.capafy-*.plist \
  "$REPO_ROOT"/skills/self/capafy-loop/launchd/ai.anicca.capafy-*.plist; do
  render "$template"
done
