#!/bin/bash
# run_decision_loop.sh — launchd entrypoint for decision_loop.py (2026-07-25 decision-loop task).
# THIS FILE DECIDES NOTHING (same convention as run.sh). decision_loop.py is stdlib-only at its
# own top level (json/os/re/subprocess/datetime + pinnacle_edge/pinnacle_observe, both stdlib) —
# plain system python3 runs it; it internally resolves the agent's .venv for the child strategy
# scripts (bundle_arb.py/market_maker.py/pick.py/place_order.py) that DO need third-party deps.
#
# DRY BY DEFAULT: decision_loop.py itself forces PM_DRY_RUN=1 on every child unless BOTH
# PM_DRY_RUN=0 AND PM_LIVE_CONFIRM=I_UNDERSTAND_THE_RISK are already set in ITS OWN environment —
# this launchd job sets neither, so it can never go live no matter what changes elsewhere on the
# machine (see decision_loop.py's _live_confirmed() docstring).
set -u
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SKILL_DIR"
AGENT_HOME="${PM_TRADE_AGENT_HOME:-$HOME/.anicca-founder/agents/polymarket-agent}"
export PM_TRADE_AGENT_HOME="$AGENT_HOME"
# ROOT CAUSE FIX (2026-07-25, own-eyes verified via a real launchd run): under launchd's minimal
# PATH, bare `python3` resolved to the system/Xcode Python (3.9, no python-dotenv installed), so
# pinnacle_observe's in-process resolve_odds_api_key() silently fell through to
# "ODDS_API_KEY not configured" even though the agent's .env has it — the dotenv import inside
# resolve_odds_api_key() is wrapped in `except Exception: pass` (fail-soft by design) and ate the
# ModuleNotFoundError. Use the SAME venv every other strategy script in this skill already uses
# (has dotenv + requests + eth_account + the polymarket SDK) so decision_loop.py's in-process
# pinnacle_observe call and its subprocess children all get an identical, complete environment.
if [ -x "$AGENT_HOME/.venv/bin/python" ]; then
  exec "$AGENT_HOME/.venv/bin/python" decision_loop.py
else
  exec python3 decision_loop.py
fi
