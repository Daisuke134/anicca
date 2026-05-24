#!/usr/bin/env bash
# Slack formatting helpers. DRY_RUN-safe: never POSTs anything; cron delivery handles it.
# These helpers ONLY print formatted text to stdout. The caller decides whether to write/send.
#
# NOTE: helpers shell out to ./_format_*.py because heredocs would otherwise consume
# python's stdin and clobber the piped rows.

_LIBDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

format_daily_table()   { python3 "$_LIBDIR/_format_daily.py"; }
format_zero_view_alert(){ python3 "$_LIBDIR/_format_zero_view.py"; }
format_rollup_leaderboard(){ python3 "$_LIBDIR/_format_rollup.py"; }
