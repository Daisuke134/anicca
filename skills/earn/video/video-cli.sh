#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# video-cli.sh — launch the ALWAYS-ON video-loop claude-p session (clone of clip-cli.sh /
# affiliate-cli.sh pattern, canonicalising the ad-hoc launch that originally had no --model).
# Detached tmux headless claude --model sonnet that registers a cron every 4h: one faceless-video
# transition per wake (create→warmup→affiliate@day7→post→record). Idles; healthcheck restarts.
#
#   bash video-cli.sh            # start if not already running (idempotent)
#   bash video-cli.sh --restart  # kill the existing session then start fresh
#   bash video-cli.sh --status   # is the session alive?
set -uo pipefail
SOCK="/tmp/anicca-video-tmux.sock"
SESSION="anicca-video-core"
CLAUDE="$(command -v claude || echo /Users/anicca/.local/bin/claude)"

# startup prompt — matches the original ad-hoc launch (reconstructed from session history)
STARTUP='You are the Anicca video-loop core (Sutando proactive-loop style, claude-p). FIRST, register the recurring driver if absent: call CronList; if no job whose prompt mentions earn/video exists, call CronCreate with cron="23 */12 * * *", recurring=true, durable=true, and prompt="Run ONE pass of the faceless-video money loop: set -a; . ~/.openclaw/.env; set +a ; FIRST check if ~/.openclaw/state/.video-core-selfheal-request.json exists -- if so, this loop got stuck repeatedly and healthcheck gave up restarting it, so YOU must fix it yourself (no human, no other AI): read the file, diagnose the real root cause from logs, fix the underlying script if fixable and verify the fix, then rm that json file; if you cannot fix it after a real attempt, invoke self/issue-dev with a note, then rm the file anyway. BEFORE deciding what to do this pass (REQ-LV-020/113), read your recent metrics ledger (~/.cloak/earn-video-metrics-money_blueprintdaily.jsonl), your lessons ledger (~/.cloak/video-lessons-money_blueprintdaily.jsonl), and this week evaluator score (evaluate_stage1(ledger_path) in ~/anicca/skills/self/self-improve/video/evaluator.py, compare via beats_previous_week in .../lib/weekly_compare.py) so you iterate toward a better script than last time -- this reading is your judgment call, nothing here is scripted. THEN EARN_VIDEO_HANDLE=money_blueprintdaily SKILL_TIMEOUT_S=220 bash ~/anicca/skills/earn/video/run.sh (idempotent, fail-closed; warmup uses the DEDICATED anti-throttle CloakBrowser on its own port+profile = NEVER the daily-driver; posts LIVE+verified only = published+post_url; records earnings ONLY for on-chain-confirmed USDC). Before that, IF something did not go as intended this pass (REQ-LV-031, e.g. warmup stalled, post failed, affiliate link rejected) — append ONE line {ts, pass_id, mistake, lesson} to ~/.cloak/video-lessons-money_blueprintdaily.jsonl describing what happened and what to do differently (your judgment, not scripted). THEN report by mail: run bash ~/anicca/skills/report/loop-report.sh video \"<one-line summary of what you did this pass>\" <success, failure, or queue-empty> <usdc earned this pass, or 0> \"<evidence: the actual URL of the reel/post you made this pass, or \"none: <reason>\" (a real reason, e.g. warmup not done yet this pass) if nothing was posted>\" (no-ops silently if AGENTMAIL_API_KEY is not set -- only report if you were given that credential). ALSO record this pass own approximate token/compute cost for the CEO budget tracker (REQ-CEO-020): run bash ~/anicca/skills/self/founder-loop/ceo/record-cost-event.sh video <your own best-effort USD cost estimate for this pass -- your judgment call, a rough estimate is fine, never blocks the pass>. FINALLY touch ~/.openclaw/state/.video-core-last-pass (proves this pass completed; NEVER touch on mere startup, only after the pass genuinely finishes). Report the slot one-line JSON + warmup_day + any new reel URL. Blocker is not stop.". THEN run ONE pass now (the same body). THEN stop and stay idle — the cron will drive subsequent passes. Do NOT touch the daily-driver browser (:9222) or any non-money_blueprintdaily account.'

status() { tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo "ALIVE" || echo "DEAD"; }

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true ;;
esac

# idempotent: do nothing if already alive (unless --restart already killed it)
if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "video-core already ALIVE"; exit 0
fi

STARTUP="${STARTUP} 重要な結果（数字・IDを含む成果、realized P&L、致命的エラー）が出たら PushNotification ツールで Dais へ verbatim 送信してから終了する。narration・定常報告には使わない。"
STARTUP="${STARTUP} BROWSER DISCIPLINE (mandatory, every pass): the daily-driver Chromium is shared with the other money loops. FIRST run bash: bash ~/anicca/skills/browser/ensure_browser.sh — it heals a dead browser and restores the logins from the cookie vault; if it prints FAILED, skip all browser work this pass and report honestly instead of hanging. THEN take your own isolated space: LEASE=$(python3 ~/anicca/skills/browser/scripts/cdp_context_lease.py acquire video) and drive ONLY the tab at the ws URL inside that JSON. NEVER navigate a tab you did not open — another loop may be halfway through a form in it. When the pass is done run: python3 ~/anicca/skills/browser/scripts/cdp_context_lease.py release video ."

PROMPT_FILE="$HOME/.cache/anicca-loops/video-startup.txt"
mkdir -p "$(dirname "$PROMPT_FILE")"
printf %s "$STARTUP" > "$PROMPT_FILE"
bash "$HOME/anicca/skills/browser/ensure_browser.sh" || echo "WARN: browser not recovered"

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
mkdir -p "$HOME/.openclaw/state" && touch "$HOME/.openclaw/state/.video-core-last-start"   # ported from gig-cli.sh: seeds the grace-window marker for healthcheck's stale-pass detection
sleep 2
echo "video-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
