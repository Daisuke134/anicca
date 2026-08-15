#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
# gig_outcome_tracker.sh — M1 durable outcome ledger runner (gig loop spec §FH' blind spot:
# docs/loop-engineering/26-gig-loop-asis-tobe-plan.md). Revisits already-applied Coconala
# request pages on a slow, capped cadence and appends each request's terminal-state
# observation to ~/gig/applied-outcomes.jsonl (open -> someone_contracted / closed_unfilled
# / expired / we_won). Called by auditor.sh on its own interval marker, exactly like
# gig_reality_verify.sh — this script is NOT a gig_pass.sh lane: it runs far less often
# than the per-pass loop and needs no lease, only the same read-only CDP mutex
# gig_reality_verify.sh already uses.
#
# Deterministic end to end: no model call, no judge. All parsing lives in
# scripts/outcome_tracker.py (unit tested without a browser) and scripts/market_snapshot.py
# (already the loop's own 応募人数/契約人数 extractor).
#
# stdout-JSON-only discipline (memory: feedback_loop_scripts_must_emit_clean_json_stdout):
# diagnostic/progress text goes to stderr; the ONLY thing on stdout is the final summary line
# outcome_tracker.py itself prints (or nothing, on an early defer -- auditor.sh discards
# stdout either way and only reads the error log).
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SELF_DIR/scripts/gig_paths.sh"
G="$GIG_STATE_DIR"
PY="$(command -v python3 || echo /opt/homebrew/bin/python3)"
LEDGER="$G/applied-outcomes.jsonl"
APPLIED="$G/applied.jsonl"
PROJECTS_ROOT="$G/projects"
BATCH_LIMIT="${GIG_OUTCOME_BATCH_LIMIT:-40}"
COOLDOWN_SECS="${GIG_OUTCOME_COOLDOWN_SECS:-72000}"  # 20h

echo "$(date '+%F %T') gig_outcome_tracker: starting" >&2

# ─── CDP mutex (same shared lock gig_reality_verify.sh uses) — defer, never fight the core ──
# shellcheck disable=SC1091
source "$SELF_DIR/scripts/cdp_lock.sh"
if ! cdp_lock_acquire "outcome-tracker" 60; then
  echo "$(date '+%F %T') gig_outcome_tracker: Gig CDP busy — deferring this round (exit 75)" >&2
  exit 75
fi
trap 'cdp_lock_release' EXIT

# ─── browser health guard — same pattern as gig_reality_verify.sh §3.6 ──────────────────────
# shellcheck disable=SC1091
source "$SELF_DIR/scripts/cdp_daily_driver_guard.sh"
if ! cdp_guard_ensure_healthy 6 45; then
  echo "$(date '+%F %T') gig_outcome_tracker: Gig CDP unreachable after guard relaunch — deferring this round (exit 75)" >&2
  exit 75
fi

# ─── session restore + logged-out defer — same pattern as gig_reality_verify.sh §3.7 ────────
VAULT="$GIG_BROWSER_DIR/scripts/session_vault.py"
"$PY" "$VAULT" restore >/dev/null 2>&1 || true
KA=$("$PY" "$SELF_DIR/scripts/cdp_nav_snapshot.py" probe-session \
  --url "https://coconala.com/mypage/dashboard" 2>/dev/null || echo '{}')
LOGGED_OUT=$("$PY" -c "import json,sys; print('1' if json.loads(sys.argv[1]).get('logged_out') else '0')" "$KA" 2>/dev/null || echo 0)
if [ "$LOGGED_OUT" = "1" ]; then
  echo "$(date '+%F %T') gig_outcome_tracker: logged out after vault restore — deferring (exit 75; not a failure)" >&2
  exit 75
fi

# ─── the actual work: deterministic, no LLM ─────────────────────────────────────────────────
"$PY" "$SELF_DIR/scripts/outcome_tracker.py" run \
  --applied "$APPLIED" \
  --ledger "$LEDGER" \
  --projects-root "$PROJECTS_ROOT" \
  --batch-limit "$BATCH_LIMIT" \
  --cooldown-secs "$COOLDOWN_SECS"
