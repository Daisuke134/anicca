#!/usr/bin/env bash
# Keep the deterministic Gig core supervisor alive. The OS-owned LaunchAgent is
# the only production scheduler; work itself runs through launch_gig_worker.sh.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
SOCK="/tmp/anicca-gig-tmux.sock"
SESSION="anicca-gig-core"

set -a
# shellcheck source=/dev/null
. "$HOME/.openclaw/.env" 2>/dev/null
set +a

status() { tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo "ALIVE" || echo "DEAD"; }

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true ;;
esac
if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "gig-core already ALIVE"
  exit 0
fi

if [ "${GIG_KYC_CONFIRMED:-0}" != "1" ]; then
  echo "gig-core: NOT starting -- set GIG_KYC_CONFIRMED=1 after Coconala KYC" >&2
  exit 0
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "$REPO_ROOT/lib/registry-enforce.sh"
registry_enforce_or_exit gig

bash "$HOME/anicca/skills/browser/ensure_browser.sh" || echo "WARN: browser could not be recovered"
tmux -S "$SOCK" new-session -d -s "$SESSION" -c "$HOME" \
  "exec /bin/bash '$HOME/profitable-claude/skills/gig-work/scripts/gig_core_supervisor.sh'"
mkdir -p "$HOME/gig"
touch "$HOME/gig/.last-start"
sleep 2
echo "gig-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
