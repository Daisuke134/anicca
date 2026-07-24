#!/usr/bin/env bash
# Canonical 10b bridge: turn privacy-safe feedback rows into D0-compatible issues,
# then hand control to the already-installed unattended developer loop.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
node "$HERE/feedback-to-issue.js" >&2 || {
  printf '%s\n' "feedback-to-issue failed; continuing D0 for already-open issues" >&2
}

exec /bin/bash "$HOME/profitable-claude/skills/life-manager-dev/dev-pass.sh"
