#!/usr/bin/env bash
# audit-cli.sh — ALWAYS-ON audit earn-core (clone of clip/affiliate-cli). Detached tmux headless
# claude, daily cron: discover live contests → analyze ONE in-scope contract → draft a candidate
# finding. Real submission needs a code4rena/Cantina account (honest gap). Healthcheck restarts it.
set -uo pipefail
SOCK="/tmp/anicca-audit-tmux.sock"; SESSION="anicca-audit-core"
CLAUDE="$(command -v claude || echo /opt/homebrew/bin/claude)"
STARTUP='You are the Anicca audit earn-core (claude-p, every-day loop). Smart-contract audit contests (code4rena/Cantina) pay $60-500k USDC pools per VALID unique finding. FIRST register the recurring driver if absent: CronList; if none mentions earn/audit, CronCreate cron="53 7 * * *" (daily ~07:53), recurring=true, durable=true, prompt="Run ONE daily audit pass, no human. set -a; . ~/.openclaw/.env; set +a. (1) DISCOVER: EARN_MODE=discover bash ~/anicca/skills/earn/audit/run.sh (refreshes state/contests.json with live pools). (2) ANALYZE: pick the top in-scope contest whose scope is fetchable; read its scope/repo (firecrawl the audit URL + the GitHub repo), study ONE in-scope contract, and if you find a genuine candidate vulnerability, write a real finding (title, severity, impact, PoC, mitigation) to ~/anicca/skills/earn/audit/state/findings/<id>.md. NEVER invent a vuln — if none is found this pass, say so (earn 0); a drafted candidate is progress, not a fake. (3) SUBMIT is the honest gap: needs a code4rena/Cantina account — flag it, do NOT fake a submission or record-earn. Report one-line JSON {contests, analyzed, candidate_finding}. Blocker is not stop." THEN run ONE discover+analyze pass now. THEN idle.'
status(){ tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && echo ALIVE || echo DEAD; }
case "${1:-}" in --status) status; exit 0;; --restart) tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null||true;; esac
[ "${1:-}" != "--restart" ] && tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && { echo "audit-core already ALIVE"; exit 0; }
tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"
sleep 2; echo "audit-core started ($(status))"
