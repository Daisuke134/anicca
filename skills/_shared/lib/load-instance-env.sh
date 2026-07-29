#!/usr/bin/env bash
# _shared/lib/load-instance-env.sh — SOURCED (never executed directly) by skill run.sh wrappers to
# load shared per-user secrets ($HOME/.hermes/.env, $HOME/.local/state/life-manager/.env) WITHOUT letting either
# file's own ANICCA_HOME assignment clobber the caller's per-instance ANICCA_HOME.
#
# Root cause (anicca-spawn-identity-resolution-fix, 2026-07-09): $HOME is the real, SHARED macOS home
# — every instance on one machine sources the SAME two files — while ANICCA_HOME is per-instance
# identity. $HOME/.local/state/life-manager/.env always sets its OWN ANICCA_HOME (the OpenClaw automaton's home);
# sourcing it under `set -a` used to silently overwrite the caller's correct ANICCA_HOME wholesale,
# which broke self/spawn/run.sh's real identity resolution in production. Hand-copying the fix into
# each affected run.sh (self/spawn, self/spawn-child, economy/lending) let a 4th, unfixed instance
# slip through in review — this file is the single source of truth so that never recurs: any run.sh
# that needs these shared secrets sources THIS file instead of re-implementing the preamble.
#
# Usage (from a skill's run.sh):
#   . "$SKILL_DIR/../../_shared/lib/load-instance-env.sh"
# (or any equivalent path expression that resolves to this file — see call sites for examples).
set -a
_ANICCA_HOME_CALLER="${ANICCA_HOME:-}"
[ -f "$HOME/.hermes/.env" ]   && . "$HOME/.hermes/.env"
[ -f "$HOME/.local/state/life-manager/.env" ] && . "$HOME/.local/state/life-manager/.env"
[ -n "$_ANICCA_HOME_CALLER" ] && ANICCA_HOME="$_ANICCA_HOME_CALLER"
unset _ANICCA_HOME_CALLER
set +a
