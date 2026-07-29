#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
# reality-verify-spawn.sh — GENERALIZED, BLOCKING verification spawn wrapper.
# Spec: .vcsdd/features/reality-gate/specs/behavioral-spec.md REQ-005/REQ-006/REQ-010/REQ-018
# (extends .vcsdd/features/reality-verifier/specs/behavioral-spec.md REQ-008).
#
# Spawns a FRESH, BLOCKING claude process (zero context from the loop being verified) that acts
# as reality-verifier against a given claim, then UNCONDITIONALLY runs the result through the
# shared enforceVerdict pure core (skills/self/lib/reality-verdict-schema.mjs, via the thin CLI
# adapter skills/self/scripts/reality-enforce-cli.mjs) before appending anything to the durable
# per-loop verdict trail (REQ-006) or routing to self-fix.sh / the human-review queue (REQ-010/018).
#
# `pass-id` is NEVER accepted from the caller (CLI argument, environment variable, or otherwise)
# — this script generates it INTERNALLY, CSPRNG-derived (>=128 bits), at spawn time (mirrors
# gig_reality_verify.sh:100-105's own precedent: generated inside the script itself).
#
# Usage: reality-verify-spawn.sh <loop-name> <artifact-or-public-url> [claim-text] [claim-type]
#          [required-artifact-count] [claimed-urls] [fixed-public-surface-url]
#          [content-fingerprint] [precommit-ts]
#   claim-type: "public-artifact" | "caller-per-invocation" | "none" (default when omitted/
#     unrecognized: "none" — backward compatible with the pre-reality-gate 3-arg caller; no
#     provenance backstop runs, enforceVerdict passes the raw verdict through unchanged).
#   claimed-urls: comma-separated. Defaults to [artifact-or-public-url] when that looks like a URL.
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || echo /opt/homebrew/bin/python3)"

usage() {
  echo "Usage: reality-verify-spawn.sh <loop-name> <artifact-or-public-url> [claim-text] [claim-type] [required-artifact-count] [claimed-urls] [fixed-public-surface-url] [content-fingerprint] [precommit-ts]" >&2
}

LOOP_RAW="${1:-}"
ARTIFACT="${2:-}"
CLAIM="${3:-}"
CLAIM_TYPE_ARG="${4:-}"
REQUIRED_COUNT_ARG="${5:-}"
CLAIMED_URLS_ARG="${6:-}"
FIXED_SURFACE_ARG="${7:-}"
CONTENT_FINGERPRINT_ARG="${8:-}"
PRECOMMIT_TS_ARG="${9:-}"

if [ -z "$LOOP_RAW" ]; then
  echo "reality-verify-spawn.sh: missing <loop-name>" >&2
  usage
  exit 1
fi
if [ -z "$ARTIFACT" ]; then
  echo "reality-verify-spawn.sh: missing <artifact-or-public-url>" >&2
  usage
  exit 1
fi

# Edge case (REQ-005): unrecognized/omitted claim-type -> "none" (generic, backward-compatible
# handling — no provenance backstop, enforceVerdict passes the raw verdict through unchanged).
case "$CLAIM_TYPE_ARG" in
  public-artifact|caller-per-invocation|none) CLAIM_TYPE="$CLAIM_TYPE_ARG" ;;
  *) CLAIM_TYPE="none" ;;
esac

REQUIRED_COUNT="${REQUIRED_COUNT_ARG:-1}"
case "$REQUIRED_COUNT" in ''|*[!0-9]*) REQUIRED_COUNT=1 ;; esac

# REQ-008 edge case: normalize "capafy" and "capafy-loop" to the same "capafy-loop" form.
LOOP="${LOOP_RAW%-loop}-loop"

STATE="$HOME/.local/state/life-manager/state"
mkdir -p "$STATE" 2>/dev/null || true
TS="$(date +%s%3N 2>/dev/null || date +%s000)"
RESULT="$STATE/.reality-verify-$LOOP-$TS.json"
LOG="$HOME/.local/state/life-manager/logs/reality-verify-$LOOP.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

# Default claimed-urls to the primary artifact-or-public-url when it looks like a real URL and
# no explicit list was supplied.
CLAIMED_URLS="$CLAIMED_URLS_ARG"
if [ -z "$CLAIMED_URLS" ]; then
  case "$ARTIFACT" in
    http://*|https://*) CLAIMED_URLS="$ARTIFACT" ;;
    *) CLAIMED_URLS="" ;;
  esac
fi

# FIND-028-style test seam (mirrors self-fix.sh's SELF_FIX_DRYRUN): print derived identity +
# resolved-defaults + result path and exit BEFORE any pass-id generation, capture, or process
# side-effect, so path/default derivation is testable without spawning claude or touching CSPRNG.
if [ "${REALITY_VERIFY_DRYRUN:-}" = "1" ]; then
  printf 'LOOP=%s RESULT=%s CLAIM_TYPE=%s REQUIRED_COUNT=%s CLAIMED_URLS=%s\n' \
    "$LOOP" "$RESULT" "$CLAIM_TYPE" "$REQUIRED_COUNT" "$CLAIMED_URLS"
  exit 0
fi

# Edge case (REQ-005): no URL at all for a public-artifact claim-type -> refuse to spawn.
if [ "$CLAIM_TYPE" = "public-artifact" ] && [ -z "$CLAIMED_URLS" ]; then
  echo "reality-verify-spawn.sh: claim-type=public-artifact but no URL to check (need <artifact-or-public-url> or <claimed-urls>) — refusing to spawn" >&2
  exit 1
fi

# ─── PROP-042/FIND-N/Q: internally-generated passId — NEVER accepted from any external channel ──
# (CLI argument, env var PASS_ID/passId, or otherwise). Any caller-supplied value in these
# channels is silently ignored; there is no code path below that reads one into PASS_ID.
# CSPRNG-derived, >=128 bits (openssl rand -hex 16 = 128 bits), never date+PID (guessable).
PASS_ID="realityverify-$(openssl rand -hex 16 2>/dev/null || "$PY" -c 'import secrets; print(secrets.token_hex(16))')"
unset PASS_ID_INJECTED_IGNORED 2>/dev/null || true

# PROP-042 debug seam: report the resolved PASS_ID (and the capture identity it drives) WITHOUT
# spawning claude, so a test can prove no external channel (env PASS_ID, a stray positional arg)
# is ever honored. Still generates a real CSPRNG passId (this is not the DRYRUN path).
if [ "${REALITY_VERIFY_PASSID_DEBUG:-}" = "1" ]; then
  printf 'PASS_ID=%s\n' "$PASS_ID"
  exit 0
fi

# ─── HMAC secret: CSPRNG-generated HERE, held only in this shell's memory, NEVER written to ────
# disk/env/argv — passed to public_artifact_snapshot.py exclusively via stdin (REQ-016/017).
HMAC_SECRET="$(openssl rand -hex 32 2>/dev/null || "$PY" -c 'import secrets; print(secrets.token_hex(32))')"

TRAIL_DIR="$STATE/.reality-artifacts-$LOOP-$PASS_ID"
ARTIFACTS_FILE=""
CAPTURE_START_TS="$(date +%s%3N 2>/dev/null || date +%s000)"

# Instagram post/reel URL -> (account, shortcode), for routing to the dedicated ig_public_check.py
# adapter instead of the generic plain-GET public_artifact_snapshot.py — Instagram's SPA shell
# commonly returns 200 regardless of whether the underlying post exists, so a plain HTTP status
# capture cannot distinguish a real removal from a normal page load; ig_public_check.py's
# fixed-public-surface membership check can. Prints "<account> <code>" on match, else returns 1.
parse_instagram_account_and_code() {
  if [[ "$1" =~ instagram\.com/([A-Za-z0-9._]+)/(p|reel)/([A-Za-z0-9_-]+) ]]; then
    printf '%s %s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[3]}"
    return 0
  fi
  return 1
}

if [ "$CLAIM_TYPE" = "public-artifact" ] || { [ "$CLAIM_TYPE" = "caller-per-invocation" ] && [ -n "$CLAIMED_URLS" ]; }; then
  # Deterministic, logged-out capture BEFORE the LLM verifier is spawned — the wrapper (not the
  # LLM) owns the trust decision of what got captured (public_artifact_snapshot.py's own doc
  # comment: "the wrapper that OWNS trust decisions is reality-verify-spawn.sh").
  IFS=',' read -r -a URL_ARR <<< "$CLAIMED_URLS"
  IG_ACCOUNT_AND_CODE=""
  if [ "${#URL_ARR[@]}" -eq 1 ] && [ -n "${URL_ARR[0]}" ]; then
    IG_ACCOUNT_AND_CODE="$(parse_instagram_account_and_code "${URL_ARR[0]}" || true)"
  fi
  if [ -n "$IG_ACCOUNT_AND_CODE" ]; then
    IG_ACCOUNT="${IG_ACCOUNT_AND_CODE%% *}"
    IG_CODE="${IG_ACCOUNT_AND_CODE#* }"
    CAPTURE_OUT=$(printf '%s' "$HMAC_SECRET" | "$PY" "$SELF_DIR/scripts/ig_public_check.py" --pass-id "$PASS_ID" --trail-dir "$TRAIL_DIR" --account "$IG_ACCOUNT" --claimed-code "$IG_CODE" 2>>"$LOG")
    CAPTURE_RC=$?
    if [ "$CAPTURE_RC" -eq 0 ]; then
      ARTIFACTS_FILE="$TRAIL_DIR/artifacts.jsonl"
      echo "$(date '+%F %T') reality-verify[$LOOP] ig captured: $CAPTURE_OUT" >> "$LOG"
    else
      echo "$(date '+%F %T') reality-verify[$LOOP] ig_public_check.py failed rc=$CAPTURE_RC (proceeding with zero captured artifacts -> enforceVerdict will CANNOT_VERIFY/no_citation on an unsupported PASS)" >> "$LOG"
    fi
  elif [ "${#URL_ARR[@]}" -gt 0 ] && [ -n "${URL_ARR[0]}" ]; then
    CAPTURE_OUT=$(printf '%s' "$HMAC_SECRET" | "$PY" "$SELF_DIR/scripts/public_artifact_snapshot.py" --pass-id "$PASS_ID" --trail-dir "$TRAIL_DIR" "${URL_ARR[@]}" 2>>"$LOG")
    CAPTURE_RC=$?
    if [ "$CAPTURE_RC" -eq 0 ]; then
      ARTIFACTS_FILE="$TRAIL_DIR/artifacts.jsonl"
      echo "$(date '+%F %T') reality-verify[$LOOP] captured: $CAPTURE_OUT" >> "$LOG"
    else
      echo "$(date '+%F %T') reality-verify[$LOOP] public_artifact_snapshot.py failed rc=$CAPTURE_RC (proceeding with zero captured artifacts -> enforceVerdict will CANNOT_VERIFY/no_citation on an unsupported PASS)" >> "$LOG"
    fi
  fi
fi

CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
TIMEOUT_SECS=600

TASK="You are reality-verifier (see .claude/agents/reality-verifier.md in this repo for your full role definition — read it first if present). You have ZERO context from the ${LOOP} loop/session; do not trust anything below as fact, verify it independently with your own Read/Grep/Glob/Bash calls against ledger files, logs, read-only on-chain state, and (for a public-artifact/caller-per-invocation claim) the deterministic capture trail at ${TRAIL_DIR}/artifacts.jsonl (if it exists).

TARGET LOOP: ${LOOP}
ARTIFACT/URL TO CHECK: ${ARTIFACT}
CLAIM TO VERIFY (a hypothesis, not a fact): ${CLAIM}
CLAIM TYPE: ${CLAIM_TYPE}
THIS PASS'S passId: ${PASS_ID}

Independently gather evidence, check for all 7 finding categories (report_ledger_mismatch, report_onchain_mismatch, internal_transfer_mislabeled, mock_marker_in_success_path, narrate_only_claim, unhealthy_strategy, post_not_publicly_visible), then write your final verdict JSON (role/overallVerdict/findings, and for a PASS with a public-artifact/caller-per-invocation claim, an evidenceReviewed array whose entries copy the EXACT tool/passId/ts/requestedUrl fields of a real row you read from ${TRAIL_DIR}/artifacts.jsonl — never invent these values) matching skills/self/lib/reality-verdict-schema.mjs's validateVerdictShape, to exactly this path using Bash: ${RESULT}
Do not write to any other file. A FAIL must include at least one evidenced finding; a PASS with zero findings must include evidenceReviewed. If ground truth (ledger/on-chain/the capture trail) is unreachable, say so explicitly rather than guessing — an inconclusive read is not a lie, but a fabricated one is."

echo "$(date '+%F %T') reality-verify[$LOOP] SPAWNING blocking sonnet fresh-context verifier (pass=$PASS_ID, timeout ${TIMEOUT_SECS}s)" >> "$LOG"
env -u ANTHROPIC_API_KEY timeout "$TIMEOUT_SECS" \
  "$CLAUDE" -p "$TASK" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" --output-format text \
  > /dev/null 2>>"$LOG"
CLAUDE_RC=$?
echo "$(date '+%F %T') reality-verify[$LOOP] verifier spawn returned rc=$CLAUDE_RC" >> "$LOG"

# ─── UNCONDITIONALLY run the (possibly missing/malformed) raw verdict through enforceVerdict ────
# via the thin node CLI adapter — this is the ONLY place either invocation path may treat a raw
# LLM verdict as accepted (REQ-014). A timeout/crash that left $RESULT unwritten is not
# special-cased here: reality-enforce-cli.mjs's malformed-file handling turns "missing/unparseable
# raw verdict" into CANNOT_VERIFY/malformed_verdict_shape automatically (fail-closed by construction).
ENFORCE_ARGS=(--loop "$LOOP" --state-dir "$STATE" --raw-verdict-file "$RESULT" --pass-id "$PASS_ID"
  --claim-type "$CLAIM_TYPE" --required-count "$REQUIRED_COUNT" --claimed-urls "$CLAIMED_URLS"
  --capture-start-ts "$CAPTURE_START_TS")
[ -n "$ARTIFACTS_FILE" ] && ENFORCE_ARGS+=(--artifacts-file "$ARTIFACTS_FILE")
[ -n "$FIXED_SURFACE_ARG" ] && ENFORCE_ARGS+=(--fixed-surface-url "$FIXED_SURFACE_ARG")
[ -n "$CONTENT_FINGERPRINT_ARG" ] && ENFORCE_ARGS+=(--content-fingerprint "$CONTENT_FINGERPRINT_ARG")
[ -n "$PRECOMMIT_TS_ARG" ] && ENFORCE_ARGS+=(--precommit-ts "$PRECOMMIT_TS_ARG")

DECISION=$(printf '%s' "$HMAC_SECRET" | node "$SELF_DIR/scripts/reality-enforce-cli.mjs" "${ENFORCE_ARGS[@]}")
ENFORCE_RC=$?
if [ "$ENFORCE_RC" -ne 0 ] || [ -z "$DECISION" ]; then
  echo "reality-verify-spawn.sh: reality-enforce-cli.mjs failed (rc=$ENFORCE_RC) — cannot determine an enforced verdict" >&2
  exit 1
fi
echo "$(date '+%F %T') reality-verify[$LOOP] enforced decision: $DECISION" >> "$LOG"

OVERALL_VERDICT=$("$PY" -c "import json,sys; print(json.loads(sys.argv[1]).get('overallVerdict',''))" "$DECISION" 2>/dev/null)
ESCALATE=$("$PY" -c "import json,sys; print('1' if json.loads(sys.argv[1]).get('escalateSelfFix') else '0')" "$DECISION" 2>/dev/null)

# ─── REQ-010/REQ-018 routing (distinct code path from the malformed/no-op branches above) ──────
# FAIL -> self-fix.sh always. CANNOT_VERIFY -> self-fix.sh ONLY on the second consecutive
# occurrence for this loop (escalateSelfFix, computed by the imported shouldEscalateCannotVerifyStreak
# inside reality-enforce-cli.mjs — never re-derived in this shell).
if [ "$ESCALATE" = "1" ]; then
  echo "$(date '+%F %T') reality-verify[$LOOP] verdict=$OVERALL_VERDICT -> invoking self-fix.sh" >> "$LOG"
  bash "$SELF_DIR/self-fix.sh" "$LOOP" "reality-verify verdict=$OVERALL_VERDICT (pass=$PASS_ID) — see $STATE/reality-verdict-$LOOP.jsonl" >> "$LOG" 2>&1 &
else
  echo "$(date '+%F %T') reality-verify[$LOOP] verdict=$OVERALL_VERDICT -> no self-fix.sh invocation this pass" >> "$LOG"
fi

echo "$DECISION"
exit 0
