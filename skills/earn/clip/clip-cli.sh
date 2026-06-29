#!/usr/bin/env bash
# clip-cli.sh — launch the ALWAYS-ON clip-loop claude-p session (copied from Sutando's
# scripts/start-cli.sh pattern: a detached tmux session running headless `claude` with
# --dangerously-skip-permissions; the session registers a recurring cron that drives the
# clip money loop, then idles while the cron fires it. Survives session-close; a launchd
# health-check (ai.anicca.clip-core-healthcheck) restarts it if the tmux session dies).
#
#   bash clip-cli.sh            # start if not already running (idempotent)
#   bash clip-cli.sh --restart  # kill the existing session then start fresh
#   bash clip-cli.sh --status   # is the session alive?
set -uo pipefail
SOCK="/tmp/anicca-clip-tmux.sock"
SESSION="anicca-clip-core"
CLAUDE="$(command -v claude || echo /opt/homebrew/bin/claude)"

# the startup prompt the headless session runs once, then idles (cron drives the loop)
STARTUP='You are the Anicca clip-loop core (Sutando proactive-loop style, claude-p). FIRST, register the recurring driver if absent: call CronList; if no job whose prompt mentions earn/clip exists, call CronCreate with cron="7 * * * *", recurring=true, durable=true, and prompt="Run ONE pass of the clip money loop: set -a; . ~/.openclaw/.env; set +a ; EARN_MODE=execute bash ~/anicca/skills/earn/clip/run.sh (idempotent, fail-closed, only posts when a queued clip AND a ready logged-in clip account in ~/.cloak/clip-accounts.json exist; NEVER post to aishigoto or any non-clip account); then bash ~/anicca/skills/earn/clip/monitor.sh to observe posts/views/founder-wallet USDC. If ~/clips/queue is empty, report queue-empty. Report the slot one-line JSON + total USDC earned + any new reel URL. Blocker is not stop.". THEN run ONE pass now (the same body). THEN stop and stay idle — the cron will drive subsequent passes.'

status() { tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo "ALIVE" || echo "DEAD"; }

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true ;;
esac

# idempotent: do nothing if already alive (unless --restart already killed it)
if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "clip-core already ALIVE"; exit 0
fi

tmux -S "$SOCK" new-session -d -s "$SESSION" \
  "$CLAUDE" --name "$SESSION" --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"
sleep 2
echo "clip-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
