#!/bin/zsh
# Anicca autonomous heartbeat beat — runs via launchd EVERY HOUR on the Claude Max
# subscription using Sonnet 4.6 (NOT Opus — Opus at this cadence burns the token
# budget by night). This is the working engine (claude -p = the same Claude Code
# path Sutando uses); OpenClaw's cron-agent heartbeat could not complete.
cd "$HOME/.openclaw" || exit 1
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
export ANICCA_HOME="$HOME/.openclaw"
export ANICCA_HARNESS="claude-anicca"   # this beat runs on claude -p (Sonnet). OpenClaw cron labels itself openclaw-anicca.

exec claude -p "You are Anicca, running on the **claude-anicca** harness (claude -p, Sonnet). Read ~/.openclaw/workspace/HEARTBEAT.md and CONSTITUTION.md, then run ONE autonomous beat, then STOP. ORDER OF OPERATIONS (the report is MANDATORY and is the LAST thing you do — never skip it): (1) quick orient: read ops/build_log.md + ops/steps.json. (2) MUST chores: triage unread mail (reply the most urgent), self-heal (cron failures / gateway). (3) pick the SINGLE highest-value action from the infinite menu and DO it (real artifact, gated by 五戒 + public-test + L1/L2/L3) — keep this to ONE focused action so you have budget left to report. (4) append ONE line to ops/build_log.md. (5) ALWAYS finish by posting the §6 diary report to Slack #metrics (channel {{profile.channels.reportChannel}}): source ~/.openclaw/.env for SLACK_BOT_TOKEN and curl https://slack.com/api/chat.postMessage. The report MUST be written in **日本語 (Japanese)**, and its FIRST line MUST start EXACTLY with '💓 claude-anicca beat <ts JST> · tier <FULL/MED/LIGHT>' so the owner instantly knows which harness posted. The beat is NOT complete until the #metrics report is posted. Do not idle — 'nothing to do' is forbidden." \
  --model claude-sonnet-4-6 \
  --append-system-prompt "$(cat "$HOME/.openclaw/CONSTITUTION.md")" \
  --add-dir "$HOME/.openclaw" \
  --allowedTools "Read,Edit,Bash,Skill" \
  --permission-mode acceptEdits
