#!/usr/bin/env bash
# earn-gig daily loop — the SCALE harness. One entrypoint any self-funded AI runs
# (launchd / cron / /loop). No human, no captcha. Logs every earn to earn-ledger.jsonl.
#
# RAIL A (x402 supply): keep the paywalled gig live (passive, zero capital).
# RAIL B (Claw Earn):   poll posted bounties; surface TAKE-able research/data ones.
# The MODEL (claude -p wrapping this) makes the TAKE/SKIP call + does the work.
set -uo pipefail

SKILL="$HOME/.claude/skills/earn-gig"
VENV="$HOME/.cache/ag402-venv/bin"
PY="/opt/homebrew/bin/python3"
LEDGER="$SKILL/state/earn-ledger.jsonl"
mkdir -p "$SKILL/state"

log(){ echo "[$(date -u +%FT%TZ)] $*"; }

# 0. preflight — wallet + balances (honest gate)
log "=== earn-gig loop ==="
$PY "$SKILL/scripts/claw_agent.py" session >/tmp/eg_session.txt 2>&1 \
  && log "RAIL B session: OK ($(grep agentSessionToken /tmp/eg_session.txt | cut -c1-46))" \
  || log "RAIL B session: FAIL (see /tmp/eg_session.txt)"

# 1. RAIL A — ensure x402 supply gig is live (passive income, no capital)
if ! curl -sS --max-time 4 -o /dev/null http://127.0.0.1:8402/health 2>/dev/null; then
  log "RAIL A: starting x402 gig (slop-scan paywall)"
  bash "$SKILL/scripts/x402_gig/run_gig.sh" >/tmp/eg_gig.txt 2>&1 || log "RAIL A: start failed"
else
  log "RAIL A: gig already live"
fi

# 2. RAIL B — poll posted bounties; print TAKE candidates for the model to act on
log "RAIL B: polling Claw Earn bounties"
$PY "$SKILL/scripts/claw_agent.py" poll 2>&1 | sed 's/^/    /'

# 3. The MODEL (claude -p) reads the poll output, applies §1B TAKE/SKIP from SKILL.md,
#    and for each TAKE: stake -> do work -> submit -> claim -> append to LEDGER.
#    (Gated on: an open TAKE-able bounty existing + USDC stake capital in wallet.)
log "=== loop done — model acts on TAKE candidates above; earns append to $LEDGER ==="
