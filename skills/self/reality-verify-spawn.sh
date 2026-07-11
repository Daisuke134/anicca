#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
# reality-verify-spawn.sh — AGENTIC verification layer spawn wrapper (TODO#5).
# Spec: .vcsdd/features/reality-verifier/specs/behavioral-spec.md REQ-008.
# Design: docs/loop-engineering/24-shared-ground-truth-verifier-design.md (v3),
#         docs/loop-engineering/27-ideal-earn-record-verify-architecture.md.
#
# Spawns a FRESH, detached claude process (zero context from the loop being verified — see
# reality-verifier.md's fresh-context requirement) that acts as reality-verifier against a
# given loop's report/artifact, and writes a binary verdict to a deterministic result path.
#
# This script does NOT wire itself into self-fix.sh, healthcheck, or cron — that is left to
# the parent to do after own-eyes review (behavioral-spec.md REQ-008 acceptance).
#
# Usage: reality-verify-spawn.sh <loop-name> <artifact-or-report-path> [claim-text]
set -uo pipefail

usage() { echo "Usage: reality-verify-spawn.sh <loop-name> <artifact-or-report-path> [claim-text]" >&2; }

LOOP_RAW="${1:-}"
ARTIFACT="${2:-}"
CLAIM="${3:-}"

if [ -z "$LOOP_RAW" ]; then
  echo "reality-verify-spawn.sh: missing <loop-name>" >&2
  usage
  exit 1
fi
if [ -z "$ARTIFACT" ]; then
  echo "reality-verify-spawn.sh: missing <artifact-or-report-path>" >&2
  usage
  exit 1
fi

# REQ-008 edge case: normalize "capafy" and "capafy-loop" to the same "capafy-loop" form
# (mirrors self-fix.sh's LOOP="${1:?loop name}"; LOOP="${LOOP%-loop}-loop").
LOOP="${LOOP_RAW%-loop}-loop"

STATE="$HOME/.openclaw/state"
mkdir -p "$STATE" 2>/dev/null || true
TS="$(date +%s%3N 2>/dev/null || date +%s000)"
RESULT="$STATE/.reality-verify-$LOOP-$TS.json"
LOG="$HOME/.openclaw/logs/reality-verify-$LOOP.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

# FIND-028-style test seam (mirrors self-fix.sh's SELF_FIX_DRYRUN): print the derived
# identity + result path and exit BEFORE any tmux/process side-effect, so path derivation is
# testable without spawning claude. See test-reality-verify-spawn.sh.
if [ "${REALITY_VERIFY_DRYRUN:-}" = "1" ]; then
  printf 'LOOP=%s RESULT=%s\n' "$LOOP" "$RESULT"
  exit 0
fi

SOCK="/tmp/anicca-realityverify-$LOOP-tmux.sock"
SESSION="anicca-realityverify-$LOOP-$TS"
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"

TASK="You are reality-verifier (see .claude/agents/reality-verifier.md in this repo for your full role definition — read it first if present). You have ZERO context from the ${LOOP} loop/session; do not trust anything below as fact, verify it independently with your own Read/Grep/Glob/Bash calls against ledger files, logs, and read-only on-chain state.

TARGET LOOP: ${LOOP}
ARTIFACT/REPORT TO CHECK: ${ARTIFACT}
CLAIM TO VERIFY (a hypothesis, not a fact): ${CLAIM}

Independently gather evidence, check for all 6 finding categories (report_ledger_mismatch, report_onchain_mismatch, internal_transfer_mislabeled, mock_marker_in_success_path, narrate_only_claim, unhealthy_strategy), then write your final verdict JSON (role/overallVerdict/findings, matching skills/self/lib/reality-verdict-schema.mjs's validateVerdictShape) to exactly this path using Bash: ${RESULT}
Do not write to any other file. A FAIL must include at least one evidenced finding; a PASS with zero findings must include evidenceReviewed. If ground truth (ledger/on-chain) is unreachable, fail-closed (FAIL), never silently PASS."

tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$TASK"
echo "$(date '+%F %T') reality-verify[$LOOP] SPAWNED (sonnet, fresh context): ${ARTIFACT}" >> "$LOG"
echo "reality-verify[$LOOP] spawned (sonnet, detached). result->$RESULT log->$LOG"
