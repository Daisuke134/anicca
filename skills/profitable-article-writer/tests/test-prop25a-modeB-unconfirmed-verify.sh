#!/usr/bin/env bash
# VSDD oracle -- PROP-25 (REQ-24, Sprint 4): the Mode-B in-loop verify-failure/inconclusive path records
# UNCONFIRMED to state, never silently assumes success, and never retry-publishes the same draft within the
# same wake.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

FAKE_DIR="$(mktemp -d)"
CALL_LOG_DIR="$(mktemp -d)"
CALL_LOG="$CALL_LOG_DIR/calls.log"
: > "$CALL_LOG"

cat > "$FAKE_DIR/note_browser_common.py" << PYEOF
def confirm_and_publish(note_key, **kwargs):
    with open("$CALL_LOG", "a") as f:
        f.write(note_key + "\n")
    # the click ITSELF fires successfully (ok=True, per REQ-24's "the click confirmed success" wording) but
    # points at a note_key that does NOT actually resolve on note.com -- the independent, SEPARATE verify
    # step (a REAL, unmocked network fetch via lib/note-verify-live.py) must then legitimately fail, proving
    # run.sh records UNCONFIRMED rather than trusting the click's own optimistic success.
    return {"ok": True, "reason": None, "prefix": None, "clicked_label": "投稿する",
            "url": f"https://note.com/anicca123/n/{note_key}", "screenshot": "/tmp/fake.png", "status": "draft"}
def load_note_cookies(f):
    return None
def open_editor_ready(*a, **k):
    return (None, None)
def select_paid_price(*a, **k):
    return {"row_found": True, "paid_checked": True, "price_filled": None}
PYEOF

T="$(mktemp -d)"
mkdir -p "$T/state"
printf '1' > "$T/state/mode-b-ratio"

NONEXISTENT_KEY="nTHISKEYDOESNOTEXISTUNCONFIRMEDTEST00000"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" \
  ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS=PASS ARTICLE_TEST_V05_RESULTS=PASS \
  ARTICLE_MODEB_NOTE_KEY="$NONEXISTENT_KEY" ARTICLE_NOTE_BROWSER_COMMON_DIR="$FAKE_DIR" \
  bash "$SKILL/run.sh" 2>&1)"; rc=$?

ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "wake completes rc=0 even on a verify-inconclusive result (never crashes): $OUT"
ok "$(grep -q 'last_wake_result: UNCONFIRMED' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE records UNCONFIRMED (never silently PUBLISHED=success) on verify failure: $(cat "$T/STATE.md" 2>/dev/null)"
ok "$(grep -q 'publish_verify_result: UNCONFIRMED' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE carries publish_verify_result: UNCONFIRMED"
ok "$(grep -q 'publish_verified_at:' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE still carries a verification timestamp even on UNCONFIRMED"
ok "$([ "$(wc -l < "$CALL_LOG" | tr -d ' ')" = "1" ] && echo 1 || echo 0)" "confirm_and_publish was called EXACTLY ONCE (no blind retry-publish of the same draft within this wake): $(cat "$CALL_LOG")"

[ $fails -eq 0 ] && { echo "PASS -- PROP-25 (REQ-24) UNCONFIRMED path: verify failure recorded, never assumed success, never retried in the same wake"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
