#!/usr/bin/env bash
# economy/lending/run.sh — thin entrypoint (REQ-117, anicca-agent-lending sprint-3): loads
# per-instance env and hands off ALL real work to scripts/wake-gate.mjs, mirroring self/spawn/run.sh's
# own already-proven shape exactly. No eligibility/sizing/servicing decision logic of its own — that
# lives entirely in lending-gate.mjs/lending-orchestrator.mjs, invoked by scripts/wake-gate.mjs.
#
# Usage:
#   run.sh   real run; reads real citizen registry + loans.jsonl + gojo-log.jsonl, selects at most one
#            eligible (lenderId, borrowerId) pair this wake and attempts issuance, then unconditionally
#            runs the default-detection sweep. exit 0 for a clean no-op / routine per-pair refusal plus
#            a completed sweep; exit 1 only for a genuine, unexpected in-process error.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE="$(command -v node || true)"

for arg in "$@"; do
  case "$arg" in
    --help) sed -n '1,10p' "$0"; exit 0 ;;
  esac
done

[ -n "$NODE" ] || { echo "economy/lending: node missing" >&2; exit 64; }

# --- load env (per-instance identity, RPC overrides, etc.). Best-effort; absence is reported, never
# faked — scripts/wake-gate.mjs's own resolvers fail closed on genuinely missing config. Delegates to
# the shared helper (anicca-spawn-identity-resolution-fix FIND-001) so this file's own header claim
# of mirroring self/spawn/run.sh's shape stays true by construction, never by manual re-sync.
. "$SKILL_DIR/../../_shared/lib/load-instance-env.sh"

exec "$NODE" "$SKILL_DIR/scripts/wake-gate.mjs" "$@"
