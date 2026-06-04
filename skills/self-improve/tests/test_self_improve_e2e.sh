#!/usr/bin/env bash
# Synthetic E2E for self-improve loop.
#  1. Build an isolated STATE_DIR with a fake eval-cost.jsonl row (pass:false within 24h).
#  2. meta-cognition.sh reads it → JSON with eval_fail_24h >= 1.
#  3. detect.sh on that JSON → JSONL containing a "slop-detected" line.
#  4. file-issue.sh in DRY_RUN mode → prints the issue title (no gh write).
# Asserts each step. Exit 0 = PASS.
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$SKILL_DIR/scripts"
JQ=/usr/bin/jq

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }

# ---- isolated state dir (never touch real ~/.hermes/state) ----
TEST_STATE="$(mktemp -d -t self_improve_e2e.XXXXXX)"
trap 'rm -rf "$TEST_STATE"' EXIT
export STATE_DIR="$TEST_STATE"

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# fake eval-cost: one pass:false within 24h
printf '%s\n' \
  "{\"ts\":\"$NOW\",\"backend\":\"heuristic\",\"model\":null,\"dim_count\":4,\"total\":0.4,\"pass\":false,\"cost_usd\":0.0,\"via\":null,\"elapsed_s\":0.0,\"rubric_task_class\":\"post-to-x\"}" \
  > "$TEST_STATE/eval-cost.jsonl"

# fake heartbeat (one ok row)
printf '%s\n' \
  "{\"ts\":\"$NOW\",\"ok\":true,\"fuel\":\"test\",\"model\":\"test\",\"constitution_sha\":\"deadbeef\",\"probe\":{\"cron_count\":6}}" \
  > "$TEST_STATE/heartbeat.jsonl"

# fake daily-report (fresh, so NOT report-broken)
printf '%s\n' "{\"ts\":\"$NOW\",\"ok\":true}" > "$TEST_STATE/daily-report.jsonl"

# fake wallet (so income rule has data; non-zero to avoid income-stalled noise)
printf '%s\n' "{\"usdc\":5.0,\"queried_at\":\"$NOW\"}" > "$TEST_STATE/wallet-balance.jsonl"

# no violations file → 0 violations

# ---- step 1: meta-cognition ----
META="$("$SCRIPTS/meta-cognition.sh")" || fail "meta-cognition.sh exited non-zero"
echo "$META" | "$JQ" -e '.health.eval_fail_24h >= 1' >/dev/null 2>&1 \
  || fail "meta-cognition did not count the fake eval failure: $META"
pass "meta-cognition counts eval_fail_24h>=1"

# ---- step 2: detect ----
DETECTED="$(printf '%s' "$META" | "$SCRIPTS/detect.sh")" || fail "detect.sh exited non-zero"
echo "$DETECTED" | "$JQ" -ec 'select(.issue_type=="slop-detected")' >/dev/null 2>&1 \
  || fail "detect.sh did not emit slop-detected: $DETECTED"
pass "detect.sh emits slop-detected"

# ---- step 3: file-issue DRY ----
SLOP_LINE="$(echo "$DETECTED" | "$JQ" -c 'select(.issue_type=="slop-detected")' | head -1)"
OUT="$(printf '%s\n' "$SLOP_LINE" | DRY_RUN=1 "$SCRIPTS/file-issue.sh")" || fail "file-issue.sh DRY exited non-zero"
echo "$OUT" | grep -q "self-improve: slop-detected" \
  || fail "file-issue.sh DRY did not print expected title: $OUT"
pass "file-issue.sh DRY prints issue title"

echo "ALL PASS"
