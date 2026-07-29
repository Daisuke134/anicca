#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-inquiry-evidence.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
GIG_DIR="$HOME_DIR/profitable-claude/skills/gig-work"
mkdir -p "$HOME_DIR/gig" "$GIG_DIR/scripts" "$GIG_DIR/schemas" "$GIG_DIR/config/connectors" "$HOME_DIR/profitable-claude/skills/agent-runner"
for file in gig_pass.sh passprep.py strategy.default.json; do cp "$SKILL_DIR/$file" "$GIG_DIR/$file"; done
for file in delivery_queue.py delivery_cadence.py delivery_project.py project_ledger.py reply_queue.py connector_outbox.py; do cp "$SKILL_DIR/scripts/$file" "$GIG_DIR/scripts/$file"; done
cp "$SKILL_DIR/scripts/delivery_identity.py" "$GIG_DIR/scripts/delivery_identity.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$GIG_DIR/config/connectors/coconala.json"
cat > "$GIG_DIR/scripts/reply_lane.py" <<'PY'
#!/usr/bin/env python3
# Fixture: the autonomous reply lane cannot produce machine post-send evidence.
raise SystemExit(1)
PY
chmod +x "$GIG_DIR/scripts/reply_lane.py"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$GIG_DIR/schemas/gig_step_result.schema.json"
cat > "$TMP/snapshot.json" <<'JSON'
{"captured_at":"2026-07-22T00:04:00Z","orders":[],"quotes":[],"inquiries":[{"talkroom_id":"4201","talkroom_url":"https://coconala.com/mypage/direct_message/4201","title":"buyer-last","last_message_side":"buyer","reply_required":true,"buyer_sent_at":"2026-07-22T00:00:00Z","message_id":"msg-7"}]}
JSON
cat > "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import json, os, sys
args=sys.argv[1:]
evidence=args[args.index("--evidence-dir")+1]
os.makedirs(evidence, exist_ok=True)
open(os.path.join(evidence,"summary.json"),"w").write(json.dumps({"status":"success"})+"\n")
PY
chmod +x "$GIG_DIR/gig_pass.sh" "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/snapshot.json" GIG_TODAY=2026-07-22 \
  GIG_LOCK_DIR="$TMP/lock.d" bash "$GIG_DIR/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?
set -e
test "$rc" -ne 0 || { echo 'missing inquiry evidence returned success'; exit 1; }
grep -q 'reply_lane_failed' "$HOME_DIR/gig/pass-failures.jsonl"
grep -q 'INQUIRY_REPLY' "$HOME_DIR/gig/pass-failures.jsonl"
echo 'PASS: autonomous reply lane failure is recorded without false success'
