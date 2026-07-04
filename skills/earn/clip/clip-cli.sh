#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
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
STARTUP='You are the Anicca clip-loop core (Sutando proactive-loop style, claude-p). FIRST, register the recurring driver if absent: call CronList; if no job whose prompt mentions earn/clip exists, call CronCreate with cron="7 * * * *", recurring=true, durable=true, and prompt="Run ONE pass of the clip money loop: set -a; . ~/.openclaw/.env; set +a ; FIRST check if ~/.openclaw/state/.clip-core-selfheal-request.json exists -- if so, this loop got stuck repeatedly and the healthcheck monitor gave up restarting it, so YOU must fix it yourself now (no human, no other AI, will do this for you): read the file, diagnose the real root cause (read recent logs under ~/.openclaw/logs/clip-*.log and /tmp/clip-producer-*/pipe.log, run the failing command manually to see the actual error), fix the underlying script if the bug is fixable (edit it, re-run the failing command, confirm it now succeeds), then rm that json file once genuinely fixed; if you cannot fix it after a real attempt, invoke self/issue-dev with a note describing what failed and what you tried, then rm the file anyway so it does not repeat every wake. THEN EARN_MODE=discover bash ~/anicca/skills/earn/clip/run.sh first. If it reports ready_account=none (no ready account for your instance), SELF-PROVISION one yourself before anything else -- do NOT wait for a human: invoke the ig-account-create skill (~/.claude/skills/ig-account-create/SKILL.md, zero-human email-plus-address signup + Gmail OTP auto-read via gog gmail, exactly as already proven for @aiclipsvault) with a fresh Gmail plus-address tag, complete its profile (icon+bio per that skills COMPLETE-account bar), launch that accounts own isolated CloakBrowser instance (reuse ~/anicca-project/.claude/skills/ig-reels-poster/scripts/launch_clip_browser.py as a pattern, on a NEW port that is neither 9222 nor 9223 nor any other port already bound -- check via lsof -i -P first), then write ONE new entry into ~/.cloak/clip-accounts.json with handle/profile/port/lang/status fields. CRITICAL: run.sh silently defaults a missing port field to 9222, which is Dais own daily-driver browser -- so BEFORE retrying run.sh, read the file back and verify the port field is present and is neither 9222 nor 9223; a malformed or missing port must NEVER be allowed through. THEN retry EARN_MODE=execute bash ~/anicca/skills/earn/clip/run.sh (idempotent, fail-closed; NEVER post to aishigoto or any non-clip account); then bash ~/anicca/skills/earn/clip/monitor.sh to observe posts/views/founder-wallet USDC. If ~/clips/queue is empty, report queue-empty. Report the slot one-line JSON + total USDC earned + any new reel URL + whether a new account was self-provisioned this pass. FINALLY touch ~/.openclaw/state/.clip-core-last-pass (proves this pass completed; NEVER touch it on mere startup, only after the pass genuinely finishes). Blocker is not stop.". THEN run ONE pass now (the same body). THEN stop and stay idle — the cron will drive subsequent passes.'

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
  "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"
mkdir -p "$HOME/.openclaw/state" && touch "$HOME/.openclaw/state/.clip-core-last-start"   # ported from gig-cli.sh: seeds the grace-window marker for healthcheck's stale-pass detection
sleep 2
echo "clip-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
