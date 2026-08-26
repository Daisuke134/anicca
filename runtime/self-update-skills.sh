#!/usr/bin/env bash
# self-update-skills.sh — the SAME repo→body skills sync anicca-daemon.sh runs at boot, callable
# per wake (child-proof-audit 2026-07-14): the daemon syncs once and then exec's node, so a healthy
# long-lived loop never re-syncs — parent fixes (guard exemptions, skill shims) reached children
# only on crash. Calling this each wake caps the fix-propagation delay at one wake interval.
# Same commands, same excludes as anicca-daemon.sh step 1/1b; safe no-op when REPO==ANICCA_HOME.
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)"
CODE_ROOT="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd -P)"
if [ -n "${ANICCA_CODE_ROOT:-}" ] || [ "$(basename "$(dirname "$CODE_ROOT")")" = "releases" ]; then
  # A pinned immutable release must never fetch, rsync, or create a dependency link. Its skill code
  # is already selected by the exact release path and its mutable state belongs to ANICCA_HOME.
  if [ -n "${ANICCA_CODE_ROOT:-}" ]; then
    CONFIGURED_CODE_ROOT="$(cd "$ANICCA_CODE_ROOT" 2>/dev/null && pwd -P)" || exit 2
    [ "$CONFIGURED_CODE_ROOT" = "$CODE_ROOT" ] || exit 2
  fi
  exit 0
fi
REPO="${ANICCA_REPO:-${LIFE_MANAGER_REPO:-$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)}}"
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
