#!/usr/bin/env bash
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
CLAUDE="$(command -v claude || echo /opt/homebrew/bin/claude)"

# the startup prompt the headless session runs once, then idles (cron drives the daily loop)
STARTUP='You are the Anicca COCONALA gig earn-core (claude-p, every-day loop). Human-funded: ¥ settles to Dais MUFG via his KYC-d Coconala account "mtdc". FIRST register the recurring driver if absent: call CronList; if no job whose prompt mentions earn/gig exists, call CronCreate with cron="27 * * * *" (hourly at :27), recurring=true, durable=true, and prompt="Run ONE pass of the Coconala gig loop, no human in the daily operation. set -a; . ~/.openclaw/.env; set +a. Read ~/anicca/skills/earn/gig/scripts/coconala/APPLY_RUNBOOK.md and ~/gig/applied.jsonl (create if absent). Drive the running CloakBrowser daily-driver (CDP :9222) logged in as mtdc (re-login via Googleでログイン if logged out). Do the FIRST that applies, ONE bounded action: (1) INBOX: coconala.com トークルーム — new buyer message on an applied request → reply helpfully; any 仮払い contract → build the real deliverable (pptx skill / doc / code) and 納品; on 検収 → ask for 評価. (2) APPLY: scan coconala.com/requests for an AI-doable OPEN request (記事/資料/文字起こし/データ/コード/PowerPoint) NOT in applied.jsonl → tailored proposal + a real sample deliverable → 応募する per RUNBOOK (応募する → 納品予定日 datepicker REAL mouse-click → ファイル添付 real click + setFileInputFiles → 確認する → 投稿前にご確認ください modal 応募する). Append {requestId,title,status:applied,ts} to ~/gig/applied.jsonl. (3) TRACK #5121769 (our submitted PPTX) specifically — status + any message. EARNED CONDITION (no fake earn): a ¥ is earned ONLY when Coconala UI actually shows 検収完了/支払 for a contract — ONLY then append {ts,requestId,jpy,status,evidence:<screenshot or UI text>} to ~/gig/earnings.jsonl. NEVER write earnings.jsonl for an applied/in-progress gig. ¥ payout = Dais MUFG (human-funded); do NOT claim USDC / do NOT call record-earn. Append every applied/replied/delivered action to ~/gig/applied.jsonl. NEVER touch non-Coconala accounts. Report one-line JSON {applied,replied,delivered,jpy_settled,note}. A blocker is NOT a stop — try the autonomous path (captcha→CapSolver, OTP→gog gmail) and report.". THEN run ONE pass now (the same body). THEN stop and stay idle — the cron drives subsequent passes.'

status() { tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo "ALIVE" || echo "DEAD"; }

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true ;;
esac

if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "gig-core already ALIVE"; exit 0
fi

tmux -S "$SOCK" new-session -d -s "$SESSION" -c "$HOME" \
  "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"
sleep 2
echo "gig-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
