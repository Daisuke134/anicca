#!/usr/bin/env bash
# DEPRECATED — donation skill v2 renamed execute → monthly.
#
# Migration:
#   v1: MODE=execute bash scripts/run.sh  →  v2: MODE=monthly bash scripts/run.sh
#
# This stub redirects to monthly.sh so any cached cron payload that still calls
# execute.sh produces the right behavior without exploding.
echo "⚠️  scripts/execute.sh is deprecated in donation skill v2 — redirecting to monthly.sh"
echo "    update your cron payload to MODE=monthly."
exec bash "$(dirname "$0")/monthly.sh" "$@"
