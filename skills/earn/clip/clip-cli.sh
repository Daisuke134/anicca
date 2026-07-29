#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"  # claude itself lives in ~/.local/bin (npm global install, not homebrew)
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
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"

# the startup prompt the headless session runs once, then idles (cron drives the loop)
STARTUP='You are the Anicca clip-loop core (Sutando proactive-loop style, claude-p). FIRST, register the recurring driver if absent: call CronList; if no job whose prompt mentions earn/clip exists, call CronCreate with cron="7 * * * *", recurring=true, durable=true, and prompt="Run ONE pass of the clip money loop: set -a; . $HOME/.local/state/life-manager/.env; set +a ; FIRST check if $HOME/.local/state/life-manager/state/.clip-core-selfheal-request.json exists -- if so, this loop got stuck repeatedly and the healthcheck monitor gave up restarting it, so YOU must fix it yourself now (no human, no other AI, will do this for you): read the file, diagnose the real root cause (read recent logs under $HOME/.local/state/life-manager/logs/clip-*.log and /tmp/clip-producer-*/pipe.log, run the failing command manually to see the actual error), fix the underlying script if the bug is fixable (edit it, re-run the failing command, confirm it now succeeds), then rm that json file once genuinely fixed; if you cannot fix it after a real attempt, invoke self/issue-dev with a note describing what failed and what you tried, then rm the file anyway so it does not repeat every wake. BEFORE deciding what to do this pass (REQ-LV-020/113), read your recent metrics ledger (CLIP_LEDGER), your lessons ledger (~/.cloak/clip-lessons.jsonl), and this week evaluator score (call evaluate_stage1(ledger_path) in $LIFE_MANAGER_REPO/skills/self/self-improve/clip/evaluator.py, compare against last week via beats_previous_week in .../lib/weekly_compare.py) so you make a better choice than last time -- this reading is your judgment call, nothing here is scripted. THEN EARN_MODE=discover bash $LIFE_MANAGER_REPO/skills/earn/clip/run.sh first. SELF-HEAL RULE (one loop = one acc, replace-on-cold): the loop runs ONE active account. If run.sh reports ready_account=none, OR if the current active account has gone COLD (posting repeatedly fails with login bloks / ChallengeRequired / flagged / suspended, i.e. automated login/post can no longer succeed), then FIRST retire the cold account by setting its status to poisoned_manual_backup in ~/.cloak/clip-accounts.json (it drops out of the auto loop, kept only as a manual backup), THEN SELF-PROVISION a brand-new account which BECOMES the new sole active account and where you post forever after. This is replacement, not addition -- 1-loop-1-acc still holds. Do NOT wait for a human. To provision: invoke the ig-account-create skill (~/.claude/skills/ig-account-create/SKILL.md, zero-human email-plus-address signup + Gmail OTP auto-read via gog gmail, exactly as already proven for @aiclipsvault) with a fresh Gmail plus-address tag, complete its profile (icon+bio per that skills COMPLETE-account bar), launch that accounts own isolated CloakBrowser instance (reuse $LIFE_MANAGER_REPO/.claude/skills/ig-reels-poster/scripts/launch_clip_browser.py as a pattern, on a NEW port that is neither 9222 nor 9223 nor any other port already bound -- check via lsof -i -P first), then write ONE new entry into ~/.cloak/clip-accounts.json with handle/profile/port/lang/status fields. CRITICAL: run.sh silently defaults a missing port field to 9222, which is Dais own daily-driver browser -- so BEFORE retrying run.sh, read the file back and verify the port field is present and is neither 9222 nor 9223; a malformed or missing port must NEVER be allowed through. THEN retry EARN_MODE=execute bash $LIFE_MANAGER_REPO/skills/earn/clip/run.sh (idempotent, fail-closed; NEVER post to aishigoto or any non-clip account); then bash $LIFE_MANAGER_REPO/skills/earn/clip/monitor.sh to observe posts/views/founder-wallet USDC. If ~/clips/queue is empty, report queue-empty. Report the slot one-line JSON + total USDC earned + any new reel URL + whether a new account was self-provisioned this pass. Before that, IF something did not go as intended this pass (REQ-LV-031, e.g. a post failed, self_heal could not resolve, an account got flagged) — append ONE line {ts, pass_id, mistake, lesson} to ~/.cloak/clip-lessons.jsonl describing what happened and what to do differently (deciding what counts as a mistake is your judgment, not scripted). THEN report by mail: run bash $LIFE_MANAGER_REPO/skills/report/loop-report.sh clip \"<one-line summary of what you did this pass>\" <success, failure, or queue-empty> <usdc earned this pass, or 0> \"<evidence: the actual URL of the reel/post you made this pass, or \"none: <reason>\" (a real reason, e.g. no source clip cleared self_heal this pass) if nothing was posted>\" (no-ops silently if AGENTMAIL_API_KEY is not set -- only report if you were given that credential). ALSO record this pass own approximate token/compute cost for the CEO budget tracker (REQ-CEO-020): run bash $LIFE_MANAGER_REPO/skills/self/founder-loop/ceo/record-cost-event.sh clip <your own best-effort USD cost estimate for this pass -- your judgment call, a rough estimate is fine, never blocks the pass>. FINALLY touch $HOME/.local/state/life-manager/state/.clip-core-last-pass (proves this pass completed; NEVER touch it on mere startup, only after the pass genuinely finishes). Blocker is not stop.". THEN run ONE pass now (the same body). THEN stop and stay idle — the cron will drive subsequent passes.'

status() { tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo "ALIVE" || echo "DEAD"; }

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true ;;
esac

# idempotent: do nothing if already alive (unless --restart already killed it)
if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "clip-core already ALIVE"; exit 0
fi

STARTUP="${STARTUP} 重要な結果（数字・IDを含む成果、realized P&L、致命的エラー）が出たら PushNotification ツールで Dais へ verbatim 送信してから終了する。narration・定常報告には使わない。"
STARTUP="${STARTUP} BROWSER DISCIPLINE (mandatory, every pass): the daily-driver Chromium is shared with the other money loops. FIRST run bash: bash $LIFE_MANAGER_REPO/skills/browser/ensure_browser.sh — it heals a dead browser and restores the logins from the cookie vault; if it prints FAILED, skip all browser work this pass and report honestly instead of hanging. THEN take your own isolated space: LEASE=$(python3 $LIFE_MANAGER_REPO/skills/browser/scripts/cdp_context_lease.py acquire clip) and drive ONLY the tab at the ws URL inside that JSON. NEVER navigate a tab you did not open — another loop may be halfway through a form in it. When the pass is done run: python3 $LIFE_MANAGER_REPO/skills/browser/scripts/cdp_context_lease.py release clip ."

PROMPT_FILE="$HOME/.cache/anicca-loops/clip-startup.txt"
mkdir -p "$(dirname "$PROMPT_FILE")"
printf %s "$STARTUP" > "$PROMPT_FILE"
bash "$LIFE_MANAGER_REPO/skills/browser/ensure_browser.sh" || echo "WARN: browser not recovered"

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
  "exec \"$CLAUDE\" --name \"$SESSION\" --model sonnet --dangerously-skip-permissions --add-dir \"$HOME\" -- \"\$(cat '$PROMPT_FILE')\""
mkdir -p "$HOME/.local/state/life-manager/state" && touch "$HOME/.local/state/life-manager/state/.clip-core-last-start"   # ported from gig-cli.sh: seeds the grace-window marker for healthcheck's stale-pass detection
sleep 2
echo "clip-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
