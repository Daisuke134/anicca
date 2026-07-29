#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-reply-outbox-wiring.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
GIG_DIR="$HOME_DIR/profitable-claude/skills/gig-work"
mkdir -p "$HOME_DIR/gig" "$GIG_DIR/scripts" "$GIG_DIR/schemas" \
  "$GIG_DIR/config/connectors" "$HOME_DIR/profitable-claude/skills/agent-runner"
for file in gig_pass.sh passprep.py strategy.default.json; do
  cp "$SKILL_DIR/$file" "$GIG_DIR/$file"
done
for file in delivery_queue.py delivery_cadence.py delivery_project.py project_ledger.py \
  delivery_identity.py reply_queue.py connector_outbox.py; do
  cp "$SKILL_DIR/scripts/$file" "$GIG_DIR/scripts/$file"
done
cp "$SKILL_DIR/config/connectors/coconala.json" "$GIG_DIR/config/connectors/coconala.json"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$GIG_DIR/schemas/gig_step_result.schema.json"
cat > "$GIG_DIR/scripts/reply_lane.py" <<'PY'
#!/usr/bin/env python3
# Stop after reply queue/outbox wiring; no browser send belongs in this test.
raise SystemExit(1)
PY
cat > "$TMP/snapshot.json" <<'JSON'
{"captured_at":"2026-07-22T00:04:00+00:00","orders":[],"quotes":[],"inquiries":[{"talkroom_id":"4201","talkroom_url":"https://coconala.com/mypage/direct_message/4201","title":"purchase_preorder_message","last_message_side":"buyer","reply_required":true,"buyer_sent_at":"2026-07-22T00:00:00+00:00","message_id":"msg-7"}]}
JSON
chmod +x "$GIG_DIR/gig_pass.sh" "$GIG_DIR/scripts/reply_lane.py"

for pass_id in first second; do
  set +e
  HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/snapshot.json" \
    GIG_TODAY=2026-07-22 GIG_PASS_ID="$pass_id" GIG_LOCK_DIR="$TMP/$pass_id.lock.d" \
    bash "$GIG_DIR/gig_pass.sh" >"$TMP/$pass_id.out" 2>"$TMP/$pass_id.err"
  rc=$?
  set -e
  test "$rc" -ne 0 || { echo 'fixture unexpectedly passed browser-send gate'; exit 1; }
done

python3 - "$HOME_DIR/gig/connector-outbox.sqlite3" <<'PY'
import sqlite3, sys
with sqlite3.connect(sys.argv[1]) as connection:
    assert connection.execute("SELECT COUNT(*) FROM connector_actions").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM connector_events").fetchone()[0] == 1
PY
test -s "$HOME_DIR/gig/evidence/gig-pass-first/reply-queue.json"
test -s "$HOME_DIR/gig/evidence/gig-pass-second/reply-queue.json"
echo 'PASS: gig pass durably enqueues one typed reply event across repeated loops'
