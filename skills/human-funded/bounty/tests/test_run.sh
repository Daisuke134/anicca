#!/usr/bin/env bash
# Integration tests for the bounty run.sh fixes (docs/superpowers/specs/
# 2026-07-05-affiliate-bounty-state-machine-design.md §3/§5, VCSDD REQ-B1 items 1+2).
# Runs a COPY of run.sh in an isolated temp dir (run.sh's $STATE is $HERE/state, no env
# override exists) so this never touches the real ~/anicca/skills/human-funded/bounty/state/.
set -u
SRC="$HOME/anicca/skills/human-funded/bounty/run.sh"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3
PASS=0; FAIL=0
ok(){ echo "  ok  $1"; PASS=$((PASS+1)); }
no(){ echo "  FAIL $1: $2"; FAIL=$((FAIL+1)); }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cp "$SRC" "$TMP/run.sh"
mkdir -p "$TMP/state"

# (1) attempt(): survivors[0] already claimed -> survivors[1] gets picked (REQ-B1 item 1)
cat > "$TMP/state/gated.json" <<'JSON'
{"survivors": [
  {"repo": "o/r1", "issue": 1, "bounty_usd": 10},
  {"repo": "o/r2", "issue": 2, "bounty_usd": 20}
], "checked": 2}
JSON
echo '{"key":"o/r1#1","repo":"o/r1","issue":1,"bounty_usd":10,"pr":null,"status":"claim","wake":"1700000000"}' > "$TMP/state/attempts.jsonl"
OUT="$(cd "$TMP" && EARN_MODE=attempt bash run.sh 2>&1)"
if echo "$OUT" | grep -q "o/r2#2" && ! echo "$OUT" | grep -q "already claimed"; then
  ok "attempt() skips already-claimed survivors[0], picks survivors[1]"
else
  no "attempt-survivor-skip" "$OUT"
fi
LINES="$(wc -l < "$TMP/state/attempts.jsonl" | tr -d ' ')"
[ "$LINES" = "2" ] && ok "attempts.jsonl now has exactly 2 lines (no duplicate re-claim of r1)" || no "attempts-line-count" "got $LINES lines"

# (2) attempt(): all survivors already claimed -> honest "no unclaimed survivor" message, no crash
echo '{"key":"o/r2#2","repo":"o/r2","issue":2,"bounty_usd":20,"pr":null,"status":"claim","wake":"1700000000"}' >> "$TMP/state/attempts.jsonl"
OUT2="$(cd "$TMP" && EARN_MODE=attempt bash run.sh 2>&1)"
if echo "$OUT2" | grep -qi "no unclaimed gated survivor"; then
  ok "attempt() honestly reports no unclaimed survivor left (no crash, no fake claim)"
else
  no "attempt-all-claimed" "$OUT2"
fi

# (3) track(): BOUNTY_GH_OVERRIDE mock returns CLOSED -> exactly one stalled line appended
GH_MOCK="$TMP/fake-gh.sh"
cat > "$GH_MOCK" <<'SH'
#!/usr/bin/env bash
echo '{"state":"CLOSED","reviewDecision":""}'
SH
chmod +x "$GH_MOCK"
rm -f "$TMP/state/attempts.jsonl"
echo '{"key":"o/r3#3","repo":"o/r3","issue":3,"bounty_usd":15,"pr":99,"status":"claim","wake":"1700000000"}' > "$TMP/state/attempts.jsonl"
BEFORE_LINES="$(wc -l < "$TMP/state/attempts.jsonl" | tr -d ' ')"
(cd "$TMP" && BOUNTY_GH_OVERRIDE="$GH_MOCK" EARN_MODE=track bash run.sh >/dev/null 2>&1)
AFTER_LINES="$(wc -l < "$TMP/state/attempts.jsonl" | tr -d ' ')"
STALLED_COUNT="$(grep -c '"status": "stalled"' "$TMP/state/attempts.jsonl" 2>/dev/null || echo 0)"
if [ "$AFTER_LINES" -eq $((BEFORE_LINES + 1)) ] && [ "$STALLED_COUNT" -eq 1 ]; then
  ok "track() appends exactly ONE stalled line for a CLOSED (unmerged) PR"
else
  no "track-stalled-once" "before=$BEFORE_LINES after=$AFTER_LINES stalled=$STALLED_COUNT"
fi

# (4) track() run AGAIN (same state, stalled line now exists) -> must NOT append a second stalled line
(cd "$TMP" && BOUNTY_GH_OVERRIDE="$GH_MOCK" EARN_MODE=track bash run.sh >/dev/null 2>&1)
AFTER2_LINES="$(wc -l < "$TMP/state/attempts.jsonl" | tr -d ' ')"
STALLED_COUNT2="$(grep -c '"status": "stalled"' "$TMP/state/attempts.jsonl" 2>/dev/null || echo 0)"
if [ "$AFTER2_LINES" -eq "$AFTER_LINES" ] && [ "$STALLED_COUNT2" -eq 1 ]; then
  ok "track() run again: resolved-set skips the already-stalled key, no duplicate append (FIND-1/FIND-3 fix)"
else
  no "track-no-duplicate" "after1=$AFTER_LINES after2=$AFTER2_LINES stalled=$STALLED_COUNT2"
fi

echo
echo "$PASS/$((PASS+FAIL)) passed"
[ "$FAIL" -eq 0 ]
