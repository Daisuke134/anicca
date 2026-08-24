#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
/usr/bin/osascript - "$REPO_ROOT" <<'APPLESCRIPT'
on run argv
  set repoRoot to item 1 of argv
  tell application "Terminal"
    activate
    do script "cd " & quoted form of repoRoot & " && ./install.sh job-hunter"
  end tell
end run
APPLESCRIPT
printf '{"status":"started","surface":"terminal"}\n'
