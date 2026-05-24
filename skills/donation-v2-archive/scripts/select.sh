#!/usr/bin/env bash
# DEPRECATED — donation skill v2 removed select-mode. The 25th selection cron is gone.
# Charity selection now happens during the one-shot install hook.
#
# Migration:
#   v1: MODE=select  bash scripts/run.sh  →  v2: MODE=install bash scripts/run.sh
#
# This stub redirects to install.sh so any cached cron payload that still calls
# select.sh produces the right behavior without exploding.
echo "⚠️  scripts/select.sh is deprecated in donation skill v2 — redirecting to install.sh"
echo "    update your cron payload to MODE=install."
exec bash "$(dirname "$0")/install.sh" "$@"
