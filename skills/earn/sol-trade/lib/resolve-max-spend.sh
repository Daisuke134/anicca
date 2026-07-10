#!/bin/bash
# resolve-max-spend.sh — REQ-017 (HARD, money-safety) hard-override choke point for the SOL rail's
# --max-spend value. Positioned in run.sh immediately AFTER the SOL pre-gate's genome eval and
# BEFORE `franklin-trading start` is invoked. Ignores SOL_TRADE_MAX_SPEND (and every other env
# var) ENTIRELY -- this is the single hard-coded money-safety cap for the SOL rail, so nothing
# above it (genome-derived or otherwise attacker-preset) can ever win. Mirrors
# polymarket-trade/run.sh's single choke-point hard-override pattern (export MAX_BET_SIZE=2, etc.,
# unconditionally, after genome eval).
set -u
echo "0.25"
