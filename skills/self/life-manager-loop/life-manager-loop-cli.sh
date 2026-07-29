#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"  # claude itself lives in ~/.local/bin (npm global install, not homebrew)
# life-manager-loop-cli.sh — always-on LM money-loop claude-p session (copied from earn/clip). Detached
# tmux runs headless claude that registers a DAILY driver cron then idles; healthcheck restarts if dead.
set -uo pipefail
SOCK="/tmp/anicca-life-manager-loop-tmux.sock"; SESSION="anicca-life-manager-loop"
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
STARTUP='You are the Anicca Life Manager money-loop core (claude-p, self-improving + self-healing; money → Dais bank; human + main-agent NOT in this loop). FIRST CronList; if no job whose prompt mentions life manager money loop exists, CronCreate cron="30 9 * * *" recurring=true durable=true prompt="ONE pass of the Life Manager money loop. STEP0 SELF-HEAL: if $HOME/.local/state/life-manager/state/life-manager-loop-selfheal-request.json exists, read it, diagnose, fix: LM-HEALTH → check Railway life-call service (curl the /health, read logs); STRIPE-KEY → check STRIPE_SECRET_KEY in $HOME/.local/state/life-manager/.env; verify heal clears then rm the json; if you cannot fix it in this pass, bash $LIFE_MANAGER_REPO/skills/self/self-fix.sh life-manager \"<the exact blocker + a concrete fix hint>\" to spawn an autonomous Opus dev that actually edits+runs+verifies+commits the code fix (THAT is the self-heal — never just file an issue and wait), then rm the json. STEP1 MEASURE: bash $LIFE_MANAGER_REPO/skills/self/life-manager-loop/loop.sh and read its STATE.md (lm_mrr_usd, status). STEP2 ACT (single highest-EV move toward real LM paid users; your judgment): revenue is $0 with only 3 test users — the wall is DEMAND, so do ONE of: (a) read the Telegram onboarding funnel (start→name→calendar-connect→phone→pay) and fix the single weakest step (clearer copy, fewer taps, fix a broken step); (b) drive demand via the Reddit loop ($LIFE_MANAGER_REPO/skills/self/... once the reddit account is warmed) — post ONE genuine builder-story / answer real questions in r/ADHD, never pushy. Do ONE. STEP3 VERIFY: only a real NEW paid Stripe subscription counts — a copy tweak alone is not revenue; record the observable in STATE.md. STEP4 REPORT: bash $LIFE_MANAGER_REPO/skills/report/loop-report.sh life-manager \"<what you did + real metric>\" <success|failure|no-op> <usd or 0> \"<evidence url or none>\". FINALLY touch $HOME/.local/state/life-manager/state/.life-manager-loop-last-pass. Blocker is not stop.". THEN run ONE pass now (same body). THEN stop and idle.'
status(){ tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo ALIVE || echo DEAD; }
case "${1:-}" in --status) status; exit 0;; --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null||true;; esac
if [ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then echo "life-manager-loop already ALIVE"; exit 0; fi
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
tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"
mkdir -p "$HOME/.local/state/life-manager/state" && touch "$HOME/.local/state/life-manager/state/.life-manager-loop-last-start"; sleep 2
echo "life-manager-loop started ($(status))."
