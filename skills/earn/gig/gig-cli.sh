#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# gig-cli.sh — launch the ALWAYS-ON gig earn-core (cloned from clip-cli.sh / Sutando pattern):
# a detached tmux session running headless `claude` that registers a recurring cron driving the
# COCONALA freelance gig money loop EVERY day (scan 公開依頼 → 応募 → トーク返信 → 納品 → 評価),
# then idles. Survives session-close; the launchd gig-healthcheck restarts it if the tmux session
# dies. HUMAN-FUNDED: ¥ settles to Dais's KYC'd Coconala account → MUFG. The daily operation is
# autonomous via the daily-driver browser; the only human element is Dais's account/KYC (one-time).
# (Pivoted from dealwork 2026-06-30: dealwork pays an internal balance an AI account can NEVER
#  withdraw — "Only human accounts can withdraw" — so it can't actually pay; Coconala pays real ¥.)
#
#   bash gig-cli.sh            # start if not already running (idempotent)
#   bash gig-cli.sh --restart  # kill the existing session then start fresh
#   bash gig-cli.sh --status   # is the session alive?
set -uo pipefail
SOCK="/tmp/anicca-gig-tmux.sock"
SESSION="anicca-gig-core"
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"

# the startup prompt the headless session runs once, then idles (cron drives the daily loop)
STARTUP='You are the Anicca COCONALA gig earn-core (claude-p, self-improving multi-apply loop). Human-funded: ¥ settles to Dais MUFG via his KYC-d Coconala account "mtdc". A blocker is NOT a stop — try the autonomous path (captcha→CapSolver, OTP→gog gmail) and report. do NOT claim USDC / do NOT call record-earn. FEASIBILITY GATE (agent judgment, not hardcoded — apply every pass to both B0 出品 and B2 応募): 可=browser+computerで完結する仕事のみ対象(文章/コード/デザイン下書き/資料作成/チャット対応/翻訳/文字起こし・要約)。不可=電話対応・電話/SMSログインが必要な作業・SMS認証必須の広告アカウント運用・実地訪問・国家資格必須の業務・音声録音・顔出し・物理制作。NEVER-REFUSE: 合法かつ実行可能な顧客依頼は絶対に断らない・軽視しない。断ってよいのはfeasibility不可 or 違法/scamの場合のみ。 FIRST refresh the recurring driver so the LATEST prompt always wins: call CronList; for EVERY existing job whose prompt mentions earn/gig, call CronDelete on it; THEN call CronCreate with cron="27 * * * *" (hourly at :27), recurring=true, durable=true, and prompt="Run ONE full pass of the Coconala gig loop by executing the deterministic driver: run bash ~/anicca/skills/earn/gig/gig_pass.sh . It runs every step (LEARN scout+playbook, B0 listing iterate, PROFILE, B1 nurture+follow-up, B2 apply, FUNNEL, verify) as its own bounded sub-call so no step is skipped. After it finishes, tail -3 ~/gig/pass-report.jsonl and report the last line. Do NOT redo the steps yourself; just run the driver.". THEN run ONE full pass now: bash ~/anicca/skills/earn/gig/gig_pass.sh THEN stop and stay idle — the cron drives subsequent passes.'

status() { tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo "ALIVE" || echo "DEAD"; }

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true ;;
esac

if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "gig-core already ALIVE"; exit 0
fi

# The loop is blind without the browser, so open its eyes before it starts rather than leaving that
# to an external guard that only fires once.
bash "$HOME/anicca/skills/browser/ensure_browser.sh" || echo "WARN: browser could not be recovered; the pass will run file-only"

# The startup prompt is ~10KB. Passing it straight to tmux blows past the length limit tmux
# accepts for a command, so new-session failed with "command too long" and the healthcheck
# restarted forever without ever bringing the core back. Hand tmux a short command and let the
# shell read the prompt from disk.
PROMPT_FILE="$HOME/gig/.startup-prompt.txt"
mkdir -p "$HOME/gig"
printf '%s' "$STARTUP" > "$PROMPT_FILE"
unset ANTHROPIC_API_KEY   # 2026-07-13 fix: a custom key in this launcher's env makes `claude` block on an interactive "use this API key?" prompt with no human to answer it, hanging the core forever
tmux -S "$SOCK" new-session -d -s "$SESSION" -c "$HOME" \
  "exec \"$CLAUDE\" --name \"$SESSION\" --model sonnet --dangerously-skip-permissions --add-dir \"$HOME\" -- \"\$(cat '$PROMPT_FILE')\""
mkdir -p "$HOME/gig" && touch "$HOME/gig/.last-start"   # FIND-R2-001: seed start marker only (.last-pass = real completed pass only, never startup)
sleep 2
echo "gig-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
