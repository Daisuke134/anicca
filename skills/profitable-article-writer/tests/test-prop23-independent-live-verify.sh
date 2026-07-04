#!/usr/bin/env bash
# VSDD oracle -- PROP-23 (REQ-22, Sprint 2.5): lib/note-verify-live.py is a SEPARATE process/invocation
# from lib/note-publish-live.py (never imports/calls it, never reads NOTE_COOKIES_FILE), does a LOGGED-OUT
# fetch of the public note.com URL, and PASSes only when BOTH:
#   1. HTTP status == 200
#   2. the response body contains the article's title OR note-ID (not just any 200 -- guards an SPA-shell
#      false-positive on a nonexistent path)
# ...and records the URL + timestamp + result to state for V4 tracking (REQ-22).
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
TOOL="$SKILL/lib/note-verify-live.py"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- structural: separate process, no cookie dependency ----------
ok "$([ -f "$TOOL" ] && echo 1 || echo 0)" "lib/note-verify-live.py exists"
ok "$(! grep -qE 'import.*note.publish.live|subprocess.*note-publish-live|exec.*note-publish-live' "$TOOL" 2>/dev/null && echo 1 || echo 0)" "note-verify-live.py never imports/execs/subprocess-calls note-publish-live.py (a docstring MENTION explaining the separation is fine; an actual invocation is not)"
ok "$(! grep -qE 'environ(\.get)?\(["'"'"']NOTE_COOKIES_FILE|environ\[["'"'"']NOTE_COOKIES_FILE' "$TOOL" 2>/dev/null && echo 1 || echo 0)" "note-verify-live.py never READS the NOTE_COOKIES_FILE env var (a docstring MENTION explaining the logged-out design is fine; an actual os.environ read is not)"
if command -v python3 >/dev/null 2>&1; then
  ok "$(python3 -m py_compile "$TOOL" 2>/dev/null && echo 1 || echo 0)" "note-verify-live.py is syntactically valid Python"
fi

# ---------- positive: a REAL, already-live note.com URL must PASS (200 AND key-or-title in body) ----------
# na3a631e63d1a is the pre-existing, long-live Automaton note (referenced throughout Sprint 1/2 as the
# DEFAULT_KEY in ai-entity-article-writer/scripts/note-publish/publish-to-note.sh) -- a stable, real,
# publicly live URL independent of anything this sprint's own test-prop22b run touches.
T="$(mktemp -d)"
STATE_FILE="$T/live-publishes.jsonl"
OUT_POS="$(NOTE_LIVE_STATE_FILE="$STATE_FILE" python3 "$TOOL" na3a631e63d1a 2>&1)"; RC_POS=$?
ok "$([ $RC_POS -eq 0 ] && echo 1 || echo 0)" "real live URL (na3a631e63d1a) -> PASS, rc=0 (rc=$RC_POS): $OUT_POS"
ok "$(echo "$OUT_POS" | grep -q '"http_status": 200' && echo 1 || echo 0)" "real live URL -> http_status recorded as 200: $OUT_POS"
ok "$(echo "$OUT_POS" | grep -q '"PASS": true' && echo 1 || echo 0)" "real live URL -> PASS: true (not just a bare 200 -- content-match also required): $OUT_POS"
ok "$(echo "$OUT_POS" | grep -q '"key_in_body": true' && echo 1 || echo 0)" "real live URL -> the note KEY itself is confirmed present in the response body: $OUT_POS"

# ---------- negative: a NONEXISTENT path must NOT report success ----------
OUT_NEG="$(NOTE_LIVE_STATE_FILE="$STATE_FILE" python3 "$TOOL" nTHISKEYDOESNOTEXIST00000 2>&1)"; RC_NEG=$?
ok "$([ $RC_NEG -ne 0 ] && echo 1 || echo 0)" "nonexistent path -> non-zero exit, rc=$RC_NEG"
ok "$(echo "$OUT_NEG" | grep -q '"PASS": false' && echo 1 || echo 0)" "nonexistent path -> PASS: false (never reports success on a dead path): $OUT_NEG"
ok "$(! echo "$OUT_NEG" | grep -q '"http_status": 200' && echo 1 || echo 0)" "nonexistent path -> http_status is NOT 200 (a real 404/error, not silently coerced to success): $OUT_NEG"

# ---------- state recording: URL + timestamp + result recorded (REQ-22) ----------
ok "$([ -f "$STATE_FILE" ] && echo 1 || echo 0)" "state file written at NOTE_LIVE_STATE_FILE"
if [ -f "$STATE_FILE" ]; then
  LINES=$(wc -l < "$STATE_FILE" | tr -d ' ')
  ok "$([ "$LINES" = "2" ] && echo 1 || echo 0)" "state file has exactly one recorded line per verify invocation (expected 2, got $LINES)"
  ok "$(grep -q '"key": "na3a631e63d1a"' "$STATE_FILE" && grep -q '"ts":' "$STATE_FILE" && grep -q '"url": "https://note.com' "$STATE_FILE" && echo 1 || echo 0)" "state line records key + timestamp + url"
fi

[ $fails -eq 0 ] && { echo "PASS -- PROP-23 independent logged-out verify (200 AND content-match) + state recording confirmed"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
