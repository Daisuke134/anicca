#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# bounty-cli.sh — launch the ALWAYS-ON bounty-loop claude-p session (clone of clip-cli.sh /
# affiliate-cli.sh pattern). Detached tmux headless claude that registers a daily cron: discover
# open Algora bounties → gate (top 48) → attempt (VSDD RED→GREEN PR if a survivor exists) →
# track (record earn on merge). Idles between; healthcheck restarts if it dies.
#
#   bash bounty-cli.sh            # start if not already running (idempotent)
#   bash bounty-cli.sh --restart  # kill the existing session then start fresh
#   bash bounty-cli.sh --status   # is the session alive?
set -uo pipefail
SOCK="/tmp/anicca-bounty-tmux.sock"
SESSION="anicca-bounty-core"
CLAUDE="$(command -v claude || echo /opt/homebrew/bin/claude)"

# the startup prompt the headless session runs once, then idles (cron drives the loop)
STARTUP='You are the Anicca bounty earn-core (claude-p, daily loop, Algora GitHub bounties). FIRST register the recurring driver if absent: CronList; if none mentions earn/bounty, CronCreate cron="29 9 * * *" (daily 09:29 JST), recurring=true, durable=true, prompt="Run ONE daily Algora bounty pass, no human in loop. set -a; . ~/.openclaw/.env; set +a. FIRST check if ~/.openclaw/state/.bounty-core-selfheal-request.json exists -- if so, this loop got stuck repeatedly and healthcheck gave up restarting it, so YOU must fix it yourself (no human, no other AI): read the file, diagnose the real root cause from logs, fix the underlying script if fixable and verify the fix, then rm that json file; if you cannot fix it after a real attempt, invoke self/issue-dev with a note, then rm the file anyway. THEN (1) DISCOVER: EARN_MODE=discover bash ~/anicca/skills/earn/bounty/run.sh. (2) GATE: EARN_MODE=gate BOUNTY_GATE_N=48 bash ~/anicca/skills/earn/bounty/run.sh. (3) ATTEMPT: check ~/anicca/skills/earn/bounty/state/gated.json; if survivors[] is nonempty: run EARN_MODE=attempt bash ~/anicca/skills/earn/bounty/run.sh (writes work-order entry to state/attempts.jsonl with status:claim) THEN ACTUALLY DO the bounty — read the survivor from state/attempts.jsonl (latest status:claim line), comment /attempt #N on that GitHub issue as Daisuke134, fork the repo, fix the issue via VSDD RED->GREEN (write one failing test, write minimal fix, run the repo tests until green), open a PR referencing the issue, then update that attempts.jsonl line setting pr to the PR number. If no survivor, report real-USD inventory empty and stop (do NOT force). (4) ALWAYS TRACK: EARN_MODE=track bash ~/anicca/skills/earn/bounty/run.sh (polls open PRs, calls record-earn on merge — real external USDC only, never fake). FINALLY touch ~/.openclaw/state/.bounty-core-last-pass (proves this pass completed; NEVER touch on mere startup, only after the pass genuinely finishes). Report slot one-line JSON. Honest rule: only a real merged PR with real USD payout earns; never claim, fake, or fabricate.". THEN run ONE pass now (same body as the cron prompt). THEN stop and stay idle — the cron will drive subsequent passes.'

status() { tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo "ALIVE" || echo "DEAD"; }

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true ;;
esac

# idempotent: do nothing if already alive (unless --restart already killed it)
if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "bounty-core already ALIVE"; exit 0
fi

tmux -S "$SOCK" new-session -d -s "$SESSION" \
  "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"
mkdir -p "$HOME/.openclaw/state" && touch "$HOME/.openclaw/state/.bounty-core-last-start"   # ported from gig-cli.sh: seeds the grace-window marker for healthcheck's stale-pass detection
sleep 2
echo "bounty-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
