#!/usr/bin/env bash
# self-update-skills.sh — the SAME repo→body skills sync anicca-daemon.sh runs at boot, callable
# per wake (child-proof-audit 2026-07-14): the daemon syncs once and then exec's node, so a healthy
# long-lived loop never re-syncs — parent fixes (guard exemptions, skill shims) reached children
# only on crash. Calling this each wake caps the fix-propagation delay at one wake interval.
# Same commands, same excludes as anicca-daemon.sh step 1/1b; safe no-op when REPO==ANICCA_HOME.
set -u
REPO="${ANICCA_REPO:-${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}}"
[ -n "$REPO" ] || { echo "Life Manager repository could not be resolved" >&2; exit 2; }
ANICCA_HOME="${ANICCA_HOME:-$HOME/.anicca}"
# rsync ONLY — no git fetch here. The observed staleness was local repo→body divergence; pulling
# the remote every wake would add a network call + seconds to EVERY wake (and flake time-sensitive
# tests). Remote self-update stays a boot-time concern (anicca-daemon.sh step 1).
if [ -d "$REPO/skills" ] && [ "$REPO" != "$ANICCA_HOME" ]; then
  command -v rsync >/dev/null 2>&1 \
    && rsync -a --exclude='state/' --exclude='__pycache__' --exclude='node_modules' \
         "$REPO/skills/" "$ANICCA_HOME/skills/" 2>/dev/null || true
fi
exit 0
