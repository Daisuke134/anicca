#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-reply-paid-revalidation.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
G="$HOME_DIR/profitable-claude/skills/gig-work"
mkdir -p "$HOME_DIR/gig" "$G/scripts" "$G/schemas" "$G/config/connectors" \
  "$HOME_DIR/profitable-claude/skills/agent-runner"
for file in gig_pass.sh passprep.py strategy.default.json; do cp "$SKILL_DIR/$file" "$G/$file"; done
for file in delivery_queue.py delivery_cadence.py delivery_project.py project_ledger.py \
  delivery_identity.py reply_queue.py connector_outbox.py cdp_lock.sh run_with_cdp_lock.sh \
  gig_context_packet.py; do
  cp "$SKILL_DIR/scripts/$file" "$G/scripts/$file"
done
cp "$SKILL_DIR/../agent-runner/context_packet.py" "$HOME_DIR/profitable-claude/skills/agent-runner/context_packet.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$G/config/connectors/coconala.json"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$G/schemas/gig_step_result.schema.json"
chmod +x "$G/scripts/run_with_cdp_lock.sh"

cat > "$TMP/before.json" <<'JSON'
{
  "captured_at":"2026-07-22T08:00:00+00:00",
  "orders":[{
    "contract_id":"talkroom:4301","talkroom_id":"4301","status":"paid",
    "delivery_date":"2026-08-01","talkroom_state":"取引中",
    "buyer_feedback_pending_artifact":false,"buyer_visible_artifact_observed":true,
    "buyer_agreement_observed":true,"formal_delivery_observed":false
  }],
  "quotes":[],
  "inquiries":[{
    "talkroom_id":"9201","talkroom_url":"https://coconala.com/mypage/direct_message/9201",
    "last_message_side":"buyer","reply_required":true,
    "buyer_sent_at":"2026-07-22T07:59:00+00:00","message_id":"msg-revalidate"
  }]
}
JSON
cat > "$TMP/after.json" <<'JSON'
{
  "captured_at":"2026-07-22T08:01:00+00:00",
  "orders":[{
    "contract_id":"talkroom:4301","talkroom_id":"4301","status":"paid",
    "delivery_date":"2026-08-01","talkroom_state":"納品確認待ち",
    "buyer_feedback_pending_artifact":false,"buyer_visible_artifact_observed":true,
    "buyer_agreement_observed":true,"formal_delivery_observed":true
  }],
  "quotes":[],"inquiries":[]
}
JSON

cat > "$G/scripts/reply_lane.py" <<'PY'
#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
output = Path(args[args.index("--output") + 1])
output.write_text(json.dumps({"status":"completed","model_calls":0,"events":[]}) + "\n")
raise SystemExit(0)
PY
cat > "$G/scripts/telegram_report.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
cat > "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
expected = Path(os.environ["GIG_EVIDENCE_DIR"]) / "paid-queue-expected.json"
row = json.loads(expected.read_text(encoding="utf-8"))
Path(os.environ["PAID_EXPECTED_COPY"]).write_text(json.dumps(row) + "\n")
raise SystemExit(55)
PY
chmod +x "$G/scripts/reply_lane.py" "$G/scripts/telegram_report.py" \
  "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py"

set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/before.json" \
  GIG_POST_REPLY_QUEUE_FIXTURE="$TMP/after.json" GIG_TODAY=2026-07-22 \
  GIG_TEST_CDP_ALIVE=1 GIG_LOCK_DIR="$TMP/lock.d" GIG_EVIDENCE_DIR="$TMP/evidence" \
  PAID_EXPECTED_COPY="$TMP/paid-expected.json" \
  bash "$G/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?
set -e
test "$rc" -ne 0 || { echo 'paid browser fixture unexpectedly succeeded'; exit 1; }
if [ ! -s "$TMP/paid-expected.json" ]; then
  tail -80 "$TMP/out" >&2 || true
  tail -120 "$TMP/err" >&2 || true
  echo 'paid dispatch did not receive the revalidated queue item' >&2
  exit 1
fi
python3 - "$TMP/paid-expected.json" <<'PY'
import json, sys
row = json.load(open(sys.argv[1], encoding="utf-8"))
assert row["talkroom_id"] == "4301", row
assert row["talkroom_state"] == "納品確認待ち", row
assert row["delivery_action"] == "none", row
PY
grep -q 'paid queue recollected after reply.*id=4301.*action=none' "$TMP/err"
grep -q 'paid_queue_delivery_failed' "$HOME_DIR/gig/pass-failures.jsonl"
echo 'PASS: simultaneous speedy reply recollects paid state before delivery dispatch'
