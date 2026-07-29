#!/usr/bin/env bash
# X2: the productivity clock is fed from authoritative ledgers, never from model
# self-report JSON.
#
# The unit tests prove productive() moves only the productivity clock. These prove the
# counting layer reads the real ledgers correctly (status/state filters, since-epoch
# cutoffs, missing files -> 0, never a nonzero exit) and that gig_pass.sh actually calls
# the whole chain after every record_lane_closures call site. The regression this pins:
# record() was wired without --records, so every lane showed records_total 0 and
# last_productive_at 0.0 forever -- alive but visibly earning nothing was undetectable.
set -uo pipefail

G="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LH="$G/scripts/lane_health.py"
LP="$G/scripts/lane_productivity.py"
fails=0
check() {
  if [ "$2" = "$3" ]; then echo "PASS  $1"
  else echo "FAIL  $1  expected=$2 got=$3"; fails=$((fails+1)); fi
}

SINCE=1000000

fixture_state() {
  GIG_STATE_DIR="$(mktemp -d)"
  export GIG_STATE_DIR
  unset GIG_REPLY_OUTBOX_DB 2>/dev/null || true
}

count_of() { # lane <- stdin "lane N" lines
  awk -v lane="$1" '$1 == lane { print $2 }'
}

# --- missing ledgers count zero and never fail the pass -------------------------
fixture_state
out="$(python3 "$LP" --since "$SINCE" 2>/dev/null)"
rc=$?
check "empty state dir exits 0" 0 "$rc"
check "apply counts 0 with no ledger" 0 "$(printf '%s\n' "$out" | count_of apply)"
check "reply counts 0 with no ledger" 0 "$(printf '%s\n' "$out" | count_of reply)"
check "fulfill counts 0 with no ledger" 0 "$(printf '%s\n' "$out" | count_of fulfill)"
check "list counts 0 with no ledger" 0 "$(printf '%s\n' "$out" | count_of list)"

# --- each lane counts only real effects at or after the pass start --------------
fixture_state

# application: ~/gig/applied.jsonl, status=="applied", ts epoch seconds.
cat > "$GIG_STATE_DIR/applied.jsonl" <<'EOF'
{"requestId":"1","status":"applied","ts":999999}
{"requestId":"2","status":"applied","ts":1000010}
{"requestId":"3","status":"replied","ts":1000010}
{"requestId":"4","ts":1000010}
not json at all
EOF

# listing: ~/gig/shuppin.jsonl, action is the discriminator, not freeform status.
cat > "$GIG_STATE_DIR/shuppin.jsonl" <<'EOF'
{"action":"shuppin_created","service_id":"1","ts":1000010}
{"action":"shuppin_published","service_id":"2","ts":1000020}
{"action":"shuppin_published","ts":1000025}
{"action":"reviewed","service_id":"3","ts":1000020}
{"action":"shuppin_published","service_id":"4","ts":999000}
EOF

# reply: connector outbox sqlite, state='replied'; seller_sent_at is the send moment
# and nullable, so updated_at is the fallback.
sqlite3 "$GIG_STATE_DIR/connector-outbox.sqlite3" <<'EOF'
CREATE TABLE connector_actions (
  action_id INTEGER PRIMARY KEY,
  state TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  seller_sent_at INTEGER
);
INSERT INTO connector_actions VALUES (1,'replied',999000,1000005,1000020);
INSERT INTO connector_actions VALUES (2,'replied',998000,999900,999000);
INSERT INTO connector_actions VALUES (3,'blocked',999000,1000030,1000030);
INSERT INTO connector_actions VALUES (4,'replied',999000,1000030,NULL);
EOF

# delivery: one transaction ledger per pass evidence dir; only committed counts and
# finished_at is an ISO 8601 string, not an epoch.
iso() { python3 -c 'import datetime,sys; print(datetime.datetime.fromtimestamp(int(sys.argv[1]), tz=datetime.timezone.utc).isoformat())' "$1"; }
mkdir -p "$GIG_STATE_DIR/evidence/gig-pass-a" "$GIG_STATE_DIR/evidence/gig-pass-b" "$GIG_STATE_DIR/evidence/gig-pass-c"
printf '{"status":"committed","finished_at":"%s"}\n' "$(iso 1000040)" \
  > "$GIG_STATE_DIR/evidence/gig-pass-a/paid-work-transaction.json"
printf '{"status":"rolled_back","finished_at":"%s"}\n' "$(iso 1000040)" \
  > "$GIG_STATE_DIR/evidence/gig-pass-b/paid-work-transaction.json"
printf '{"status":"committed","finished_at":"%s"}\n' "$(iso 999000)" \
  > "$GIG_STATE_DIR/evidence/gig-pass-c/paid-work-transaction.json"
cat > "$GIG_STATE_DIR/paid-progress.jsonl" <<'EOF'
{"ts":1000050,"pass_id":"fixture-pass","status":"replied","action":"paid_progress","talkroom_id":"42"}
{"ts":999000,"pass_id":"old-pass","status":"replied","action":"paid_progress","talkroom_id":"41"}
EOF

out="$(python3 "$LP" --since "$SINCE" 2>/dev/null)"
check "apply counts only status=applied at/after pass start" 1 "$(printf '%s\n' "$out" | count_of apply)"
check "reply counts replied rows via seller_sent_at with updated_at fallback" 2 "$(printf '%s\n' "$out" | count_of reply)"
check "fulfill counts committed work and buyer-visible paid progress" 2 "$(printf '%s\n' "$out" | count_of fulfill)"
check "list counts only created/published actions" 2 "$(printf '%s\n' "$out" | count_of list)"

closures="$(python3 "$LP" --since "$SINCE" --closure-json 2>/dev/null)"
closure_field() {
  python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]][sys.argv[2]])' "$1" "$2"
}
check "application closure is a verified apply action" apply \
  "$(printf '%s' "$closures" | closure_field application action_kind)"
check "delivery closure prefers buyer-visible progress over internal build" progress \
  "$(printf '%s' "$closures" | closure_field delivery action_kind)"
check "listing closure is a verified publish action" publish \
  "$(printf '%s' "$closures" | closure_field listing action_kind)"
check "reply closure is a verified reply action" reply \
  "$(printf '%s' "$closures" | closure_field reply action_kind)"
for lane in application delivery listing reply; do
  check "$lane closure binds authoritative evidence" yes \
    "$([ -n "$(printf '%s' "$closures" | closure_field "$lane" evidence_hash)" ] && echo yes || echo no)"
done

# --- the chain gig_pass.sh runs: counts feed lane_health productive --------------
while read -r lane n; do
  [ -n "${lane:-}" ] || continue
  case "$n" in ''|*[!0-9]*) continue ;; esac
  [ "$n" -gt 0 ] || continue
  python3 "$LH" productive "$lane" --records "$n" --detail "wiring-test" >/dev/null
done <<EOF2
$out
EOF2
apply_json="$GIG_STATE_DIR/state/lanes/apply.json"
check "the productivity clock advances after the chain" 1 \
  "$(python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print(int(s["last_productive_at"]>0))' "$apply_json")"
check "records_total matches the ledger count" 1 \
  "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["records_total"])' "$apply_json")"
check "attempt totals are untouched by productivity" 0 \
  "$(python3 -c 'import json,sys; print(sum(json.load(open(sys.argv[1]))["totals"].values()))' "$apply_json")"

# --- a broken ledger degrades to zero, never to a pass failure -------------------
fixture_state
printf 'garbage' > "$GIG_STATE_DIR/connector-outbox.sqlite3"
out="$(python3 "$LP" --since "$SINCE" 2>/dev/null)"
rc=$?
check "a corrupt ledger still exits 0" 0 "$rc"
check "a corrupt ledger counts 0" 0 "$(printf '%s\n' "$out" | count_of reply)"
printf '%s\n' '{"requestId":"still-real","status":"applied","ts":1000090}' \
  > "$GIG_STATE_DIR/applied.jsonl"
closures="$(python3 "$LP" --since "$SINCE" --closure-json 2>/dev/null)"
check "one corrupt lane does not erase another lane action" apply \
  "$(printf '%s' "$closures" | closure_field application action_kind)"
check "the corrupt lane itself degrades to noop" verified_noop \
  "$(printf '%s' "$closures" | closure_field reply action_kind)"

# --- gig_pass.sh wiring -----------------------------------------------------------
bash -n "$G/gig_pass.sh"
check "gig_pass.sh parses" 0 "$?"

grep -c 'lane_productivity\.py' "$G/gig_pass.sh" >/dev/null
check "gig_pass.sh invokes the ledger counter" yes \
  "$([ "$(grep -c 'lane_productivity\.py' "$G/gig_pass.sh")" -ge 1 ] && echo yes || echo no)"

def_line="$(grep -n '^record_lane_productivity()' "$G/gig_pass.sh" | head -1 | cut -d: -f1)"
check "record_lane_productivity is defined" yes "$([ -n "$def_line" ] && echo yes || echo no)"

# Every record_lane_closures call site must be followed by record_lane_productivity
# within a couple of lines: the closure writer and the productivity writer close the
# same pass, and a call site that has one without the other silently rebuilds the
# frozen-clock outage on that path.
closure_calls="$(grep -n 'record_lane_closures$' "$G/gig_pass.sh" | grep -v '()' | cut -d: -f1)"
# Three since X18: poll-mode exit, normal completion, and the deferred lane-failure gate.
# The third is the one that used to be missing. Before X18 a lane failure exited the pass
# on the spot, and anything a LATER lane had produced went uncounted -- survivable only
# because nothing ran after a failure. The pass now keeps going, so the failure path has
# to close and count the lanes like any other terminating path. The count is a canary:
# adding a fourth exit without its productivity pair is the real regression.
check "record_lane_closures has three call sites" 3 "$(printf '%s\n' "$closure_calls" | grep -c .)"
paired=0
total=0
for line in $closure_calls; do
  total=$((total+1))
  window="$(sed -n "$((line+1)),$((line+3))p" "$G/gig_pass.sh")"
  case "$window" in
    *record_lane_productivity*) paired=$((paired+1)) ;;
  esac
done
check "every closure call site is followed by a productivity call" "$total" "$paired"

if [ -n "$def_line" ]; then
  first_call="$(grep -n 'record_lane_productivity' "$G/gig_pass.sh" \
    | grep -v '()' | head -1 | cut -d: -f1)"
  check "record_lane_productivity is defined before its first call" yes \
    "$([ -n "$first_call" ] && [ "$def_line" -lt "$first_call" ] && echo yes || echo "no(def=$def_line call=${first_call:-none})")"
fi

echo
[ "$fails" -gt 0 ] && { echo "$fails failed"; exit 1; }
echo "all lane productivity wiring tests passed"
