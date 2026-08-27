#!/bin/bash
# wrapper: load secrets + run the NL daily report (Dais 2026-06-22)
set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
export ANICCA_HOME="$HOME/.anicca"
export REPORT_TO="contact@aniccaai.com,keiodaisuke@gmail.com"
NODE=$(command -v node || echo /opt/homebrew/bin/node)
"$NODE" "$HOME/.anicca/skills/report/daily-nl-report.mjs" >> "$HOME/.anicca/logs/daily-nl-report.log" 2>&1
