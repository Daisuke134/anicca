#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"  # claude itself lives in ~/.local/bin (native installer, not homebrew)
# clip-promote-cli.sh — launch the ALWAYS-ON clip-promote-loop claude-p session (same pattern as
# clip-cli.sh / gig-cli.sh: a detached tmux session running headless `claude` with
# --dangerously-skip-permissions; the session registers a recurring internal cron that drives the
# promote.fun money loop, then idles while the cron fires it. Survives session-close; a launchd
# health-check (ai.anicca.clip-promote-core-healthcheck) restarts it if the tmux session dies).
#
# The judgment logic (SELECT/CLIP/POST/SUBMIT/MEASURE/WITHDRAW/RECORD state machine) already lives
# in decide.py + run.sh (Phase 2 GREEN, unit-tested). This script is ONLY the harness that calls
# run.sh on a schedule — it makes no earn/campaign/account decisions itself.
#
#   bash clip-promote-cli.sh            # start if not already running (idempotent)
#   bash clip-promote-cli.sh --restart  # kill the existing session then start fresh
#   bash clip-promote-cli.sh --status   # is the session alive?
set -uo pipefail
# RETIRED (Dais 2026-07-19, 掟3: retire from watchlists first — no revenue produced, no active
# cadence watchlist entry, explicit turn-off instruction). Refuse to (re)start until re-enabled.
echo "clip-promote-core: OFF (retired by Dais 2026-07-19) — refusing to start. Delete this guard to re-enable." >&2
exit 0
SOCK="/tmp/anicca-clip-promote-tmux.sock"
SESSION="anicca-clip-promote-core"
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"

# the startup prompt the headless session runs once, then idles (internal cron drives the loop
# thereafter). promote.fun campaigns move slower than the clip-rewards loop, so the internal cron
# is every 2 hours (not hourly) -- one bounded state-machine transition per wake is plenty.
STARTUP='You are the Anicca clip-promote-loop core (Sutando proactive-loop style, claude-p). FIRST, register the recurring driver if absent: call CronList; if no job whose prompt mentions earn/clip-promote exists, call CronCreate with cron="17 */2 * * *", recurring=true, durable=true, and prompt="Run ONE pass of the clip-promote money loop: set -a; . ~/.openclaw/.env; set +a ; FIRST check if ~/.openclaw/state/.clip-promote-core-selfheal-request.json exists -- if so, this loop got stuck repeatedly and the healthcheck monitor gave up restarting it, so YOU must fix it yourself now (no human, no other AI, will do this for you): read the file, diagnose the real root cause (read recent logs under ~/.openclaw/logs/clip-promote-core-healthcheck.log and any clip-promote related logs), fix the underlying script if the bug is fixable (edit it, re-run the failing command manually, confirm it now succeeds), then rm that json file once genuinely fixed; if you cannot fix it after a real attempt, invoke self/issue-dev with a note describing what failed and what you tried, then rm the file anyway so it does not repeat every wake. THEN run EARN_MODE=discover bash ~/anicca/skills/earn/clip-promote/run.sh to see which transition (SELECT, CLIP, POST, SUBMIT, MEASURE, WITHDRAW, or RECORD) this wake would run and against which campaign/state -- read this output carefully, it makes no side effect. THEN run EARN_MODE=execute bash ~/anicca/skills/earn/clip-promote/run.sh to actually perform that ONE bounded transition (idempotent, fail-closed; NEVER fabricate an earn -- only a RECORD transition backed by a real confirmed on-chain Solana withdrawal signature counts toward earned_usdc, per record-payout.mjs and the malice-guard). Read the single JSON line it prints (fields did, earned_usdc, cost_usdc). Form your own honest one-line natural-language summary of exactly what happened this pass: which transition ran, and what real artifact it produced -- for example the campaign slug or URL if SELECT picked one, the real Solana signature if WITHDRAW or RECORD produced one, or simply that nothing was eligible yet if that is what genuinely happened. Then report by mail: run bash ~/anicca/skills/report/loop-report.sh clip-promote \"<your one-line honest summary from the previous step>\" <pick the single word success, failure, blocked, or no-campaign that best matches what genuinely happened this pass> <the real earned_usdc number from the executed run.sh JSON output, or 0 if none> \"<the real campaign URL you selected this pass, OR the real Solana withdrawal/record signature you captured this pass, OR the literal string none if this pass produced no such verifiable artifact -- never invent one>\" (no-ops silently if AGENTMAIL_API_KEY is not set -- only report if you were given that credential). ALSO record this pass own approximate token/compute cost for the CEO budget tracker (REQ-CEO-020): run bash ~/anicca/skills/self/founder-loop/ceo/record-cost-event.sh clip-promote <your own best-effort USD cost estimate for this pass -- your judgment call, a rough estimate is fine, never blocks the pass>. FINALLY touch ~/.openclaw/state/.clip-promote-core-last-pass (proves this pass completed; NEVER touch it on mere startup, only after the pass genuinely finishes). Blocker is not stop.". THEN run ONE pass now (the same body). THEN stop and stay idle — the internal cron will drive subsequent passes.'

status() { tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo "ALIVE" || echo "DEAD"; }

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true ;;
esac

# idempotent: do nothing if already alive (unless --restart already killed it)
if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "clip-promote-core already ALIVE"; exit 0
fi

STARTUP="${STARTUP} 重要な結果（数字・IDを含む成果、realized P&L、致命的エラー）が出たら PushNotification ツールで Dais へ verbatim 送信してから終了する。narration・定常報告には使わない。"

# Auth: launchd/tmux cannot refresh the subscription OAuth token headlessly (keychain locked) —
# same fallback already proven live by gig-cli.sh / gig_reality_verify.sh — route through the
# local CLIProxyAPI (:8317) whose creds are plain files and refresh headlessly; fall back to
# subscription auth if the key file is absent.
CLIPROXY_KEY="$(cat "$HOME/.cli-proxy-api-key" 2>/dev/null || true)"
if [ -n "$CLIPROXY_KEY" ]; then
  export ANTHROPIC_BASE_URL="http://127.0.0.1:8317"
  export ANTHROPIC_AUTH_TOKEN="$CLIPROXY_KEY"
fi

tmux -S "$SOCK" new-session -d -s "$SESSION" \
  "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"
mkdir -p "$HOME/.openclaw/state" && touch "$HOME/.openclaw/state/.clip-promote-core-last-start"   # seeds the grace-window marker for healthcheck's stale-pass detection
sleep 2
echo "clip-promote-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
