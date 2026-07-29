#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-pass-failure.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
GIG_DIR="$HOME_DIR/profitable-claude/skills/gig-work"
mkdir -p "$GIG_DIR/scripts" "$GIG_DIR/schemas" "$GIG_DIR/config/connectors" "$HOME_DIR/profitable-claude/skills/agent-runner" "$HOME_DIR/gig"
cp "$SKILL_DIR/gig_pass.sh" "$GIG_DIR/gig_pass.sh"
cp "$SKILL_DIR/passprep.py" "$GIG_DIR/passprep.py"
cp "$SKILL_DIR/strategy.default.json" "$GIG_DIR/strategy.default.json"
cp "$SKILL_DIR/scripts/delivery_queue.py" "$GIG_DIR/scripts/delivery_queue.py"
cp "$SKILL_DIR/scripts/delivery_cadence.py" "$GIG_DIR/scripts/delivery_cadence.py"
cp "$SKILL_DIR/scripts/delivery_identity.py" "$GIG_DIR/scripts/delivery_identity.py"
cp "$SKILL_DIR/scripts/reply_queue.py" "$GIG_DIR/scripts/reply_queue.py"
cp "$SKILL_DIR/scripts/connector_outbox.py" "$GIG_DIR/scripts/connector_outbox.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$GIG_DIR/config/connectors/coconala.json"
cp "$SKILL_DIR/scripts/b1_conversation_gate.py" "$GIG_DIR/scripts/b1_conversation_gate.py"
cp "$SKILL_DIR/scripts/b2_result_gate.py" "$GIG_DIR/scripts/b2_result_gate.py"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$GIG_DIR/schemas/gig_step_result.schema.json"
printf '%s\n' '{"captured_at":"2026-07-21T00:00:00Z","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false},"orders":[],"quotes":[],"inquiries":[]}' > "$TMP/empty-snapshot.json"
cat > "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(42)
PY
chmod +x "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" "$GIG_DIR/gig_pass.sh"

set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
  GIG_LOCK_DIR="$TMP/lock.d" GIG_LEGACY_MAINTENANCE_ENABLED=1 GIG_MODEL_CALL_LIMIT=0 \
  bash "$GIG_DIR/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?
set -e
test "$rc" -ne 0 || { echo 'failed runner returned success'; exit 1; }
test ! -e "$HOME_DIR/gig/.last-pass" || { echo 'failed pass updated .last-pass'; exit 1; }
test -s "$HOME_DIR/gig/pass-failures.jsonl" || { echo 'failed pass has no failure ledger'; exit 1; }
grep -q '"failed_step":"LEARN"' "$HOME_DIR/gig/pass-failures.jsonl"
grep -q 'agent_step_failed' "$HOME_DIR/gig/pass-failures.jsonl"
test ! -d "$TMP/lock.d" || { echo 'failed pass leaked lock'; exit 1; }
grep -q 'pass failed' "$TMP/err"

echo 'PASS: failed common-runner step returns nonzero without success heartbeat'
