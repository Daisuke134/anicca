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
CLAUDE="$(command -v claude || echo /opt/homebrew/bin/claude)"

# the startup prompt the headless session runs once, then idles (cron drives the daily loop)
STARTUP='You are the Anicca COCONALA gig earn-core (claude-p, self-improving multi-apply loop). Human-funded: ¥ settles to Dais MUFG via his KYC-d Coconala account "mtdc". A blocker is NOT a stop — try the autonomous path (captcha→CapSolver, OTP→gog gmail) and report. do NOT claim USDC / do NOT call record-earn. FIRST register the recurring driver if absent: call CronList; if no job whose prompt mentions earn/gig exists, call CronCreate with cron="27 * * * *" (hourly at :27), recurring=true, durable=true, and prompt="Run ONE full pass of the Coconala self-improving gig loop, no human in the daily operation. set -a; . ~/.openclaw/.env; set +a. mkdir -p ~/gig. STRATEGY BOOTSTRAP: if ~/gig/strategy.json does not exist, copy ~/anicca/skills/earn/gig/strategy.default.json to ~/gig/strategy.json. Read ~/gig/strategy.json; increment pass_count and write it back. Read APPLY_RUNBOOK: ~/anicca/skills/earn/gig/scripts/coconala/APPLY_RUNBOOK.md. Read ~/gig/applied.jsonl (create if absent). Derive APPLIED_IDS = all requestId values in applied.jsonl. Drive the running CloakBrowser daily-driver (CDP :9222) logged in as mtdc (re-login via Googleでログイン if needed). STEP 1 NURTURE ALL (highest priority — SWEEP EVERY ACTIVE TALK-ROOM): go to coconala.com/mypage/messages (トークルーム list); for EACH open talk-room in the list: if buyer sent a new message → reply helpfully; if a 仮払い contract arrived → build the real deliverable (pptx skill / doc / code) and 納品; if 検収 ready → ask buyer for 評価. Append each action as {requestId, title, status:replied|delivered|評価依頼, ts} to ~/gig/applied.jsonl. STEP 2 APPLY BROADLY: scan coconala.com/requests for AI-doable OPEN requests across the priority_categories in ~/gig/strategy.json. For each candidate whose requestId is NOT in APPLIED_IDS, up to strategy.max_apply_per_pass total applications this pass (default 5), and NOT in strategy.skip_categories: write a tailored proposal addressing the specific brief using the matching proposal_template from strategy.json + a real sample deliverable; apply per RUNBOOK (応募する → 納品予定日 datepicker REAL mouse-click → ファイル添付 real click + setFileInputFiles → 確認する → 投稿前にご確認ください modal 応募する); append {requestId,title,status:applied,price_jpy,deliverable,delivery_date,client,ts} to ~/gig/applied.jsonl. STEP 3 OBSERVE OUTCOMES: for any previously-applied request that now shows 採用/不採用/取り下げ/低評価/会話中に人間必要の兆候: append {ts,requestId,category,outcome,reason,lesson} to ~/gig/lessons.jsonl (outcome values: accepted|rejected|ignored_closed|low_rating|needs_human|unsustainable|delivered_no_収; lesson = concrete change for next time). STEP 4 EARNED CHECK (NO FAKE EARN): for any request showing 検収完了 or 支払 in the UI → ONLY THEN append {ts,requestId,jpy,status,evidence} to ~/gig/earnings.jsonl. NEVER write earnings.jsonl for an applied/in-progress gig. STEP 5 IMPROVE STEP (every strategy.improve_cadence_passes passes, i.e. when pass_count % improve_cadence_passes == 0): (a) read ~/gig/lessons.jsonl + ~/gig/applied.jsonl stats → compute per-category accept_rate; (b) run: gh issue list -R Daisuke134/anicca --label gig-lesson --limit 10 2>/dev/null and read any novel lessons; (c) update ~/gig/strategy.json: raise priority for high-accept categories, add to skip_categories if category repeatedly needs_human|unsustainable|0-accept after 3+ tries, improve proposal_templates if lessons reveal pattern, adjust price_defaults if price-rejection is a pattern; write valid JSON back; (d) BOT-TO-BOT SHARE: if there is a notable lesson (first accept, or a systemic block discovered) not already in ~/gig/shared-lessons.jsonl (check by requestId+outcome), then run: gh issue create -R Daisuke134/anicca --title [gig-lesson] <one-line summary> --body <category,outcome,reason,lesson> --label gig-lesson 2>/dev/null; on success append {ts,requestId,outcome,issue_url} to ~/gig/shared-lessons.jsonl. If gh fails, log a warning and continue — gh failure must never abort the pass. FINALLY, only after the complete pass above finished, touch ~/gig/.last-pass. NEVER touch it on mere startup. Report one-line JSON {nurture_actions,applied_this_pass,outcomes_recorded,lessons_total,improve_ran,jpy_settled,note}.". THEN run ONE full pass now (same body). THEN stop and stay idle — the cron drives subsequent passes.'

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
mkdir -p "$HOME/gig" && touch "$HOME/gig/.last-start"   # FIND-R2-001: seed start marker only (.last-pass = real completed pass only, never startup)
sleep 2
echo "gig-core started ($(status)). Attach: tmux -S $SOCK attach -t $SESSION"
