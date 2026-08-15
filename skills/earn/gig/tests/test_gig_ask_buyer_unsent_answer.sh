#!/usr/bin/env bash
# A12 -- a composed question whose send failed must not read as a question that was asked.
#
# Order 91000001 (買い手A, 「ポケモン動画の企画・台本作成ができる方を募集します」), bought 2026-08-07
# 22:38, cancelled by Coconala at 2026-08-09 23:00 if we never speak. The pass composed the
# question at 00:54:29 into delivery/paid-answer.json, the browser send failed at 00:56:32
# with paid_answer_send_failed, and the file stayed. Every pass from 03:48 onward then read
# `[ -f "$answer" ]` in ask_buyer_when_blocked, concluded "the builder already wrote the
# buyer a message this pass", and logged "no question sent (nothing new to ask)" -- while
# ~/gig/ask-buyer.jsonl, the record written only after the browser verifies a send, had no
# row for talkroom 90000001 at all.
#
# The four things this pins, in the order they matter:
#   1. the stuck order composes and REACHES THE SEND CALL, with the question quoted;
#   2. a buyer already asked and verified is NEVER asked twice;
#   3. one pass still sends at most one message, which is what the old line was for;
#   4. a send that keeps failing stops being composed, and escalates exactly once.
#
# Nothing here touches a browser or a live path: HOME is a sandbox and the paid-progress
# browser is a fake that records the message it was handed.
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-ask-buyer-unsent.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

# ---------------------------------------------------------------------------
# The real order, as the queue actually carries it.
# ---------------------------------------------------------------------------
REQUEST_ID=91000001
TALKROOM_ID=90000001
FEEDBACK_SHA=8643236ef2c2b66bde6325dc10e22c006fc6355ba85766971fc1016fad72e7a8
# Verbatim from ~/gig/projects/91000001/requirements: the buyer's entire specification.
FEEDBACK_TEXT='よろしくお願いします。\n\n題材\n『パズルクエストX』\n納品はGoogleドキュメントでお願いします。'
# The question the ask lane composes. Long enough and interrogative enough to pass
# ask_buyer.check_question, which refuses another polite acknowledgement.
QUESTION='ご購入ありがとうございます。着手のために確認させてください。動画の本数と1本あたりの長さ、主な視聴者層、扱いたい切り口、ご希望の納期をまとめてご返信ください。'

setup_home() {
  # A whole sandbox per scenario. Paid state is cumulative by design (handled feedback,
  # material_event_outcome), so sharing one HOME would make each case depend on the last.
  local name="$1"
  HOME_DIR="$TMP/home-$name"
  G="$HOME_DIR/life-manager/skills/earn/gig"
  PROJECT="$HOME_DIR/gig/projects/$REQUEST_ID"
  mkdir -p "$HOME_DIR/gig" "$G/scripts" "$G/schemas" "$G/config/connectors" \
    "$HOME_DIR/life-manager/skills/agent-runner" "$HOME_DIR/life-manager/lib" \
    "$PROJECT/requirements" "$PROJECT/evidence" "$PROJECT/delivery"
  for file in gig_pass.sh passprep.py strategy.default.json; do cp "$SKILL_DIR/$file" "$G/$file"; done
  # The whole scripts/ and schemas/ tree, not a hand-maintained subset. The lane under test
  # here is the deepest one in the pass -- queue, project binding, context compiler, judge,
  # ask lane, composer, send path -- and a missing sibling turns into a lane isolated for an
  # unrelated reason, which reads exactly like the bug being tested.
  cp -R "$SKILL_DIR/scripts/." "$G/scripts/"
  cp -R "$SKILL_DIR/schemas/." "$G/schemas/"
  printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$G/scripts/gig_selfimprove_verify.sh"
  chmod +x "$G/scripts/gig_selfimprove_verify.sh" "$G/scripts/run_with_cdp_lock.sh"
  cp "$SKILL_DIR/../agent-runner/context_packet.py" "$HOME_DIR/life-manager/skills/agent-runner/context_packet.py"
  cp "$SKILL_DIR/../../lib/unit_economics_events.py" "$HOME_DIR/life-manager/lib/unit_economics_events.py"
  cp -R "$SKILL_DIR/config/." "$G/config/"
  cp "$TMP/agent_runner.py" "$HOME_DIR/life-manager/skills/agent-runner/agent_runner.py"
  chmod +x "$HOME_DIR/life-manager/skills/agent-runner/agent_runner.py"

  # The buyer's own words, and the file the BLOCKED record names.
  python3 - "$PROJECT/requirements/live-buyer-reply.json" "$FEEDBACK_SHA" "$FEEDBACK_TEXT" <<'PY'
import json, sys
path, sha, text = sys.argv[1:4]
open(path, "w", encoding="utf-8").write(json.dumps({
    "version": 1, "feedback_sha256": sha,
    "feedback_text": text.replace("\\n", "\n"),
}, ensure_ascii=False) + "\n")
PY
  # The compiler refuses to write a context read receipt without the live talkroom DOM the
  # collector captured for this order, so the fixture carries one.
  printf '%s\n' '{"talkroom_id":"'"$TALKROOM_ID"'","messages":[]}' > "$HOME_DIR/gig/live-talkroom.json"
  python3 - "$TMP/snapshot-$name.json" "$REQUEST_ID" "$TALKROOM_ID" "$FEEDBACK_SHA" \
    "$PROJECT/requirements/live-buyer-reply.json" "$HOME_DIR/gig/live-talkroom.json" <<'PY'
import json, sys
output, request_id, talkroom_id, sha, requirements, live_dom = sys.argv[1:7]
json.dump({
    "source": "authenticated_coconala_default_context_dom",
    "captured_at": "2026-08-08T00:53:00+00:00",
    "inbox": {"url": "https://coconala.com/message?fromMyPage=true", "not_found": False, "observed": True},
    "orders": [{
        "contract_id": "offer:92000015", "request_id": request_id, "talkroom_id": talkroom_id,
        "buyer": "買い手A", "title": "ポケモン動画の企画・台本作成ができる方を募集します",
        "status": "paid", "price_jpy": 5000, "delivery_date": "2026-08-20",
        "talkroom_state": "取引中",
        "buyer_feedback_pending_artifact": True, "buyer_visible_artifact_observed": False,
        "formal_delivery_observed": False,
        "buyer_feedback_sha256": sha, "buyer_feedback_requirements_path": requirements,
        "talkroom_evidence_file": live_dom,
        "talkroom_observed_at": "2026-08-08T00:53:00+00:00",
    }],
    "quotes": [], "inquiries": [],
}, open(output, "w", encoding="utf-8"))
PY
  SNAPSHOT="$TMP/snapshot-$name.json"
}

# ---------------------------------------------------------------------------
# The two fakes. Neither reaches a provider or a browser.
# ---------------------------------------------------------------------------
cat > "$TMP/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
label = args[args.index("--task-label") + 1]
evidence = Path(args[args.index("--evidence-dir") + 1]); evidence.mkdir(parents=True, exist_ok=True)
Path(os.environ["GIG_TEST_RUNNER_LOG"]).open("a", encoding="utf-8").write(label + "\n")

if label == "gig-PAID_WORK":
    workdir = Path(args[args.index("--workdir") + 1])
    for name in ("requirements", "evidence", "delivery"):
        (workdir / name).mkdir(parents=True, exist_ok=True)
    requirements = workdir / "requirements" / "live-buyer-reply.json"
    # The builder rewrites the packet-bound requirements file every pass; the BLOCKED
    # record is only honoured when its digest matches the feedback that is open now.
    (workdir / "evidence" / "acceptance-blocked.json").write_text(json.dumps({
        "version": 1, "status": "BLOCKED",
        "requirements_path": str(requirements),
        "feedback_sha256": os.environ["GIG_TEST_FEEDBACK_SHA"],
        "checks": [{"command": "find source artifacts -type f", "result": "制作の指定が見つかりませんでした。"}],
        "blocker": "何を作る注文かが記録に書かれていないため着手できません。",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    if os.environ.get("GIG_TEST_BUILDER_WRITES_ANSWER") == "1":
        # The other half of line 1520's original job: the builder itself spoke this pass.
        (workdir / "delivery" / "paid-answer.json").write_text(json.dumps({
            "version": 1, "status": "answer",
            "message": "ご確認ありがとうございます。ご指定の方向で進めますので、次の工程へ入ります。",
        }, ensure_ascii=False) + "\n", encoding="utf-8")
    (evidence / "summary.json").write_text(json.dumps({"status": "success", "task_label": label}) + "\n")
    raise SystemExit(0)

if label == "gig-ask-buyer-compose":
    result = evidence / "result.json"
    result.write_text(json.dumps({"reply_body": os.environ["GIG_TEST_QUESTION"]}, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    (evidence / "summary.json").write_text(json.dumps({
        "status": "success", "task_label": label, "result_path": str(result)}) + "\n")
    raise SystemExit(0)

(evidence / "summary.json").write_text(json.dumps({"status": "success", "task_label": label}) + "\n")
raise SystemExit(0)
PY

cat > "$TMP/fake-paid-progress" <<'PY'
#!/usr/bin/env python3
"""Stands exactly where coconala_paid_progress_browser.py stands, and never opens a page.

Records the message it was handed -- that recording is the proof that the question
"reaches the send call" -- and either succeeds or fails on GIG_TEST_SEND.
"""
import argparse, hashlib, json, os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--queue-item", required=True, type=Path)
parser.add_argument("--manifest", type=Path)
parser.add_argument("--answer-file", type=Path)
parser.add_argument("--evidence-dir", required=True, type=Path)
parser.add_argument("--default-tab-helper", required=True, type=Path)
args = parser.parse_args()

expected = json.loads(args.queue_item.read_text(encoding="utf-8"))
message = json.loads(args.answer_file.read_text(encoding="utf-8"))["message"] if args.answer_file else ""
with Path(os.environ["GIG_TEST_BROWSER_LOG"]).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps({"talkroom_id": expected.get("talkroom_id"), "message": message},
                            ensure_ascii=False) + "\n")
if os.environ.get("GIG_TEST_SEND") == "fail":
    # The measured shape: the browser reached the room and the message did not leave.
    raise SystemExit(1)
args.evidence_dir.mkdir(parents=True, exist_ok=True)
shot = args.evidence_dir / "post.png"; shot.write_bytes(b"png")
live = args.evidence_dir / "post.json"
tid = str(expected["talkroom_id"])
live.write_text(json.dumps({
    "url": f"https://coconala.com/talkrooms/{tid}", "sent": True, "mode": "answer",
    "send_performed": True, "formal_delivery_control_checked": False,
    "latest_seller_message": message}, ensure_ascii=False) + "\n")
(args.evidence_dir / "paid-queue-evidence.json").write_text(json.dumps({
    "sent": True, "mode": "answer", "send_performed": True, "deduplicated": False,
    "formal_delivery_checkbox": False, "captured_at": "2026-08-08T01:00:00Z",
    "talkroom_id": tid, "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
    "screenshot_path": str(shot), "live_dom_path": str(live)}, ensure_ascii=False) + "\n")
PY
chmod +x "$TMP/fake-paid-progress"

cat > "$TMP/fake-validation-docker" <<'SH'
#!/usr/bin/env bash
printf '%s\n' '{"status":"PASS"}'
SH
chmod +x "$TMP/fake-validation-docker"
export GIG_PAID_VALIDATOR_DOCKER="$TMP/fake-validation-docker"

run_pass() {
  # Returns the pass's exit code without failing the test: lanes other than PAID_WORK are
  # not fixtured here and are fail-isolated by design, so the exit code is not the subject.
  local name="$1"
  : > "$TMP/runner.log"; : > "$TMP/browser.log"
  set +e
  HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$SNAPSHOT" \
    GIG_TODAY=2026-08-08 GIG_LOCK_DIR="$TMP/lock-$name.d" GIG_EVIDENCE_DIR="$TMP/evidence-$name" \
    GIG_TEST_CDP_ALIVE=1 GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
    GIG_TEST_BROWSER_LOG="$TMP/browser.log" GIG_PAID_PROGRESS_BROWSER="$TMP/fake-paid-progress" \
    GIG_TEST_FEEDBACK_SHA="$FEEDBACK_SHA" GIG_TEST_QUESTION="$QUESTION" \
    GIG_TEST_SEND="${GIG_TEST_SEND:-ok}" \
    GIG_TEST_BUILDER_WRITES_ANSWER="${GIG_TEST_BUILDER_WRITES_ANSWER:-0}" \
    ANICCA_UNIT_ECONOMICS_LEDGER="$TMP/economics-$name.jsonl" \
    GIG_PASS_ID="$name" \
    bash "$G/gig_pass.sh" >"$TMP/out-$name" 2>"$TMP/err-$name"
  local rc=$?; set -e
  PASS_ERR="$TMP/err-$name"
  return "$rc"
}

sent_messages() { [ -s "$TMP/browser.log" ] && cat "$TMP/browser.log" || true; }
sent_count() {
  # grep -c prints 0 and exits 1 on no match, so `|| echo 0` would print a second zero.
  local count=0
  [ -f "$TMP/browser.log" ] && count=$(grep -c . "$TMP/browser.log" || true)
  printf '%s\n' "${count:-0}"
}

# ===========================================================================
# 1. THE STUCK ORDER. Exactly the state on disk right now: a question composed by a
#    previous pass whose send failed, and an ask ledger with no row for this talkroom.
# ===========================================================================
setup_home stuck
cat > "$PROJECT/delivery/paid-answer.json" <<'JSON'
{"version": 1, "status": "answer", "message": "前のパスが作成し、送信に失敗した質問です。"}
JSON
# Backdated, because that is the whole fact: this file belongs to an earlier pass.
touch -t 202608080054 "$PROJECT/delivery/paid-answer.json"
: > "$HOME_DIR/gig/ask-buyer.jsonl"
run_pass stuck || true
if [ "$(sent_count)" -ne 1 ]; then
  echo "RED: the stuck order did not reach the send call ($(sent_count) sends)"; tail -30 "$PASS_ERR"; exit 1
fi
grep -q 'STEP ASK_BUYER start' "$PASS_ERR" || { echo 'RED: the ask lane never started'; exit 1; }
grep -q 'nothing new to ask' "$PASS_ERR" && { echo 'RED: still refusing on the unsent draft'; exit 1; }
python3 - "$TMP/browser.log" "$TALKROOM_ID" "$QUESTION" <<'PY'
import json, sys
row = json.loads(open(sys.argv[1], encoding="utf-8").read().splitlines()[0])
assert str(row["talkroom_id"]) == sys.argv[2], row
assert row["message"] == sys.argv[3], row
assert "前のパス" not in row["message"], "the stale draft was resent instead of recomposed"
print("MESSAGE THAT WOULD GO OUT to talkroom %s:\n%s" % (row["talkroom_id"], row["message"]))
PY
# And the send being verified is what writes the ledger row -- the record the next pass reads.
grep -q "$TALKROOM_ID" "$HOME_DIR/gig/ask-buyer.jsonl" || { echo 'RED: verified send left no ask-buyer row'; exit 1; }
test ! -f "$PROJECT/delivery/paid-answer.json" || { echo 'RED: the draft survived a verified send'; exit 1; }

# ===========================================================================
# 2. THE REVERSE. A question that genuinely was sent and verified is never sent again.
#    This is the direction that annoys a paying customer, so it is proved from the ledger
#    the send path itself wrote, not from a hand-made row.
# ===========================================================================
LEDGER_AFTER_SEND=$(cat "$HOME_DIR/gig/ask-buyer.jsonl")
setup_home asked
printf '%s\n' "$LEDGER_AFTER_SEND" > "$HOME_DIR/gig/ask-buyer.jsonl"
run_pass asked || true
if [ "$(sent_count)" -ne 0 ]; then
  echo "RED: a buyer already asked was asked again: $(sent_messages)"; exit 1
fi
grep -q 'STEP ASK_BUYER start' "$PASS_ERR" && { echo 'RED: the ask lane ran for an answered buyer'; exit 1; }
# Same order, same blocked state, and the queue the send path reads is empty on purpose.
python3 - "$SKILL_DIR" "$PROJECT" "$TALKROOM_ID" "$HOME_DIR/gig/ask-buyer.jsonl" "$TMP/replan.json" <<'PY'
import argparse, json, sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import ask_buyer_pass
args = argparse.Namespace(project_root=sys.argv[2], talkroom_id=sys.argv[3],
                          ledger=sys.argv[4], output=sys.argv[5], send_attempts=None)
assert ask_buyer_pass.build(args) == 0
plan = json.load(open(sys.argv[5], encoding="utf-8"))
assert plan["items"] == [], plan
assert plan["already_asked"], plan
PY

# ===========================================================================
# 3. WHAT LINE 1520 WAS ACTUALLY FOR. The builder wrote the buyer a message during THIS
#    pass: the ask lane must not add a second one.
# ===========================================================================
setup_home same-pass
: > "$HOME_DIR/gig/ask-buyer.jsonl"
GIG_TEST_BUILDER_WRITES_ANSWER=1 run_pass same-pass || true
if [ "$(sent_count)" -ne 1 ]; then
  echo "RED: same pass produced $(sent_count) messages, expected exactly 1: $(sent_messages)"; exit 1
fi
python3 - "$TMP/browser.log" <<'PY'
import json, sys
row = json.loads(open(sys.argv[1], encoding="utf-8").read().splitlines()[0])
assert "次の工程へ入ります" in row["message"], row  # the builder's own message, not a question
PY
grep -q 'STEP ASK_BUYER start' "$PASS_ERR" && { echo 'RED: the ask lane spoke over the builder'; exit 1; }

# ===========================================================================
# 4. THE BOUND. A send that keeps failing must stop being composed, and must escalate once.
# ===========================================================================
#    Each attempt is its own sandbox and only the two ledgers travel between them. That is
#    the claim being tested: the counter has to survive the process boundary on its own,
#    without help from project state or from anything the previous pass left in memory.
ATTEMPTS="$TMP/carried-send-attempts.jsonl"
ESCALATIONS=0
: > "$ATTEMPTS"
for attempt in 1 2 3 4; do
  setup_home "bound-$attempt"
  : > "$HOME_DIR/gig/ask-buyer.jsonl"
  cp "$ATTEMPTS" "$HOME_DIR/gig/ask-buyer-send-attempts.jsonl"
  GIG_TEST_SEND=fail run_pass "bound-$attempt" || true
  cp "$HOME_DIR/gig/ask-buyer-send-attempts.jsonl" "$ATTEMPTS"
  if [ -f "$HOME_DIR/gig/pass-failures.jsonl" ]; then
    ESCALATIONS=$(( ESCALATIONS + $(grep -c 'ask_buyer_send_exhausted' "$HOME_DIR/gig/pass-failures.jsonl" || true) ))
  fi
  if [ "$attempt" -le 3 ]; then
    if [ "$(sent_count)" -ne 1 ]; then
      echo "RED: attempt $attempt did not reach the send call"; tail -30 "$PASS_ERR"; exit 1
    fi
  else
    # The fourth pass composes nothing and sends nothing -- and says so.
    if [ "$(sent_count)" -ne 0 ]; then
      echo "RED: the bound did not stop the send: $(sent_messages)"; exit 1
    fi
    grep -q 'send bound reached' "$PASS_ERR" || { echo 'RED: the bound was silent'; tail -30 "$PASS_ERR"; exit 1; }
    ! grep -q '^gig-ask-buyer-compose$' "$TMP/runner.log" \
      || { echo 'RED: the bound still paid for a composition'; exit 1; }
  fi
done
test "$(grep -c . "$ATTEMPTS")" -eq 3 || { echo "RED: failed sends were miscounted: $(cat "$ATTEMPTS")"; exit 1; }
test "$ESCALATIONS" -eq 1 || { echo "RED: expected exactly one escalation, got $ESCALATIONS"; exit 1; }

echo 'PASS: an unsent draft no longer silences the ask lane, a verified send still does, one pass still sends once, and a failing send is bounded'
