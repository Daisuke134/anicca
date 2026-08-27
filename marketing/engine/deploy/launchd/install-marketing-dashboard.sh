#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
RUNTIME_ROOT="$HOME/Library/Application Support/AniccaMarketing"
DESTINATION="$HOME/Library/LaunchAgents/ai.anicca.marketing-dashboard.plist"
BOOTSTRAP=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root) REPO_ROOT="${2:?}"; shift 2 ;;
    --runtime-root) RUNTIME_ROOT="${2:?}"; shift 2 ;;
    --destination) DESTINATION="${2:?}"; shift 2 ;;
    --no-bootstrap) BOOTSTRAP=false; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

TEMPLATE="$SCRIPT_DIR/ai.anicca.marketing-dashboard.plist"
CLI="$REPO_ROOT/marketing/engine/bin/marketing"
[[ -x "$CLI" ]] || {
  echo "marketing CLI is not executable: $CLI" >&2
  exit 2
}

mkdir -p "$(dirname "$DESTINATION")" "$RUNTIME_ROOT/logs"
/usr/bin/python3 - "$TEMPLATE" "$DESTINATION" "$REPO_ROOT" "$RUNTIME_ROOT" <<'PY'
import plistlib
import sys
from pathlib import Path

source, destination, repo_root, runtime_root = sys.argv[1:]
with Path(source).open("rb") as handle:
    value = plistlib.load(handle)

def replace(item):
    if isinstance(item, str):
        return item.replace("__REPO_ROOT__", repo_root).replace(
            "__RUNTIME_ROOT__", runtime_root
        )
    if isinstance(item, list):
        return [replace(child) for child in item]
    if isinstance(item, dict):
        return {key: replace(child) for key, child in item.items()}
    return item

with Path(destination).open("wb") as handle:
    plistlib.dump(replace(value), handle, sort_keys=False)
PY
plutil -lint "$DESTINATION" >/dev/null

if [[ "$BOOTSTRAP" == true ]]; then
  DOMAIN="gui/$(id -u)"
  launchctl bootout "$DOMAIN/ai.anicca.marketing-dashboard" 2>/dev/null || true
  launchctl bootstrap "$DOMAIN" "$DESTINATION"
  launchctl kickstart -k "$DOMAIN/ai.anicca.marketing-dashboard"
fi

echo "$DESTINATION"
