#!/usr/bin/env bash
# self/spawn — birth a child Anicca (own EVM/Solana wallet, own ERC-8004 identity, own cloud lease)
# when the colony treasury is profitable. Reserved registry slot: self/spawn. Decision core is pure JS
# (lib/treasury-gate.mjs::decideColonySpawn + lib/spawn-orchestrator.mjs::executeSpawnAttempt,
# node:test-covered); this shell only loads env and hands off to scripts/wake-gate.mjs, which wires
# both real functions together end to end (REQ-307's "wake-cycle scheduler's real identity" correction).
#
# Usage:
#   run.sh --dry-run              gate-only; reads real colony balances + ledger, prints the decision
#                                  JSON, touches NOTHING. exit 0 always.
#   run.sh [--skills=a,b,c]       real run; if eligible, executes a full spawn attempt (child EVM/Solana
#                                  wallet, cloud deploy + REQ-304 funding gate, ERC-8004 registration,
#                                  mcp.json write, ledger + citizens.json append). --skills= is this
#                                  wake's own agent-chosen initial skill set for the child (REQ-104's
#                                  carve-out; falls back to ANICCA_CHILD_INITIAL_SKILLS env, else none).
#                                  exit 1 on a genuine spawn-attempt failure; exit 0 when dormant (not
#                                  eligible this wake).
#
# NO FAKE RUN (HARD 0.24): a real run reports "active" ONLY after executeSpawnAttempt's own real ledger
# append lands. NO HUMAN IN LOOP: never asks "spawn OK?" — the gate decides, the cloud target
# auto-selects (REQ-306), the funding gate auto-evaluates (REQ-304).
#
# NOTE (sprint-2, contract-review round 2, resolves FIND-004): this file used to call the OLD
# lib/spawn-decision.js gate directly, followed by a DigitalOcean/AgentMail provisioning block. That
# path is RETIRED — replaced entirely by decideColonySpawn()/executeSpawnAttempt() via
# scripts/wake-gate.mjs. --host= no longer applies: executeSpawnAttempt picks its own cloud target via
# REQ-306's selectCloudTarget, evaluated fresh for each attempt.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq || true)"
NODE="$(command -v node || true)"

for arg in "$@"; do
  case "$arg" in
    --help) sed -n '1,24p' "$0"; exit 0 ;;
  esac
done

[ -n "$JQ" ]   || { echo "self/spawn: jq missing" >&2; exit 64; }
[ -n "$NODE" ] || { echo "self/spawn: node missing" >&2; exit 64; }

# --- load env (Akash signing key, etc.) from the shared per-user secrets files. Best-effort;
# absence is reported, never faked — wake-gate.mjs's own resolvers fail closed on a genuinely
# missing identity. Delegates to the shared helper (see that file's header for the full incident
# writeup) so every skill with this same need shares ONE implementation, never a hand-copy.
. "$SKILL_DIR/../../_shared/lib/load-instance-env.sh"

exec "$NODE" "$SKILL_DIR/scripts/wake-gate.mjs" "$@"
