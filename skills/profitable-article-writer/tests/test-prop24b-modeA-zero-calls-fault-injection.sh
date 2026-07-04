#!/usr/bin/env bash
# VSDD oracle -- PROP-24 (REQ-23, Sprint 4), DYNAMIC call-count fault-injection: Mode A's branch makes ZERO
# calls to the shared confirm_and_publish() function, INCLUDING when the branch-selection logic's own
# inputs (the ratio config, the wake counter) are deliberately corrupted trying to force a false-positive
# Mode-B resolution. Same pattern as test-prop6-modeA-draft.sh's no-publish assertion, but with a genuine
# DYNAMIC call-counter (via a fake note_browser_common substituted through
# ARTICLE_NOTE_BROWSER_COMMON_DIR) instead of a static artifact-absence check.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

FAKE_DIR="$(mktemp -d)"
CALL_LOG_DIR="$(mktemp -d)"
CALL_LOG="$CALL_LOG_DIR/confirm-and-publish-calls.log"
: > "$CALL_LOG"

cat > "$FAKE_DIR/note_browser_common.py" << PYEOF
def confirm_and_publish(note_key, **kwargs):
    with open("$CALL_LOG", "a") as f:
        f.write(note_key + "\n")
    return {"ok": True, "reason": None, "prefix": None, "clicked_label": "投稿する",
            "url": f"https://note.com/anicca123/n/{note_key}", "screenshot": "/tmp/fake.png", "status": "draft"}
def load_note_cookies(f):
    return None
def open_editor_ready(*a, **k):
    return (None, None)
def select_paid_price(*a, **k):
    return {"row_found": True, "paid_checked": True, "price_filled": None}
PYEOF

run_wake() {
  # args: autonomy, ratio-content(or empty to omit), counter-content(or empty to omit), draft-key
  local autonomy="$1" ratio="$2" counter="$3" draft_key="$4"
  local T; T="$(mktemp -d)"
  mkdir -p "$T/state"
  [ -n "$ratio" ] && printf '%s' "$ratio" > "$T/state/mode-b-ratio"
  [ -n "$counter" ] && printf '%s' "$counter" > "$T/state/mode-b-wake-count"
  ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY="$autonomy" ARTICLE_TEST_TOPIC="AI agents" \
    ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS=PASS ARTICLE_TEST_V05_RESULTS=PASS \
    ARTICLE_MODEB_NOTE_KEY="$draft_key" ARTICLE_NOTE_BROWSER_COMMON_DIR="$FAKE_DIR" \
    timeout 10 bash "$SKILL/run.sh" >"$T/out.log" 2>&1
  echo "$T"
}

# --- corruption 1: negative ratio -- bash modulo quirk: 1 % -1 == 0. A naive implementation reaching a raw
#     `wake_n % ratio_n` with ratio_n=-1 would wrongly resolve Mode B on the very first wake. ---
T1="$(run_wake on "-1" "" "nFAULTTEST1")"
# --- corruption 2: ratio=0 (division-by-zero attempt) ---
T2="$(run_wake on "0" "" "nFAULTTEST2")"
# --- corruption 3: non-integer ratio ---
T3="$(run_wake on "abc" "" "nFAULTTEST3")"
# --- corruption 4: ratio file entirely missing (never initialized), AUTONOMY=on ---
T4="$(run_wake on "" "" "nFAULTTEST4")"
# --- corruption 5: a VALID ratio (1-in-1, every wake is Mode B) but AUTONOMY left at its default (off) --
#     proves a "corrupted"/adversarial ratio value alone cannot bypass the AUTONOMY master-enable gate. ---
T5="$(run_wake off "1" "" "nFAULTTEST5")"
# --- corruption 6: a CORRUPTED (non-numeric garbage) wake-counter file alongside a valid ratio -- the
#     counter parser must reset safely to 0 (wake 1 of 5), never crash, never misresolve to Mode B. ---
T6="$(run_wake on "5" "garbage-not-a-number" "nFAULTTEST6")"

ok "$([ ! -s "$CALL_LOG" ] && echo 1 || echo 0)" "confirm_and_publish was NEVER called across all 6 deliberately-corrupted branch-selection scenarios (call log contents: $(cat "$CALL_LOG" 2>/dev/null | tr '\n' ' '))"

i=1
for t in "$T1" "$T2" "$T3" "$T4" "$T5" "$T6"; do
  ok "$(grep -q 'last_wake_result: DRAFT' "$t/STATE.md" 2>/dev/null && echo 1 || echo 0)" "corrupted scenario #$i resolves to Mode A (DRAFT), never PUBLISHED/UNCONFIRMED: $(cat "$t/STATE.md" 2>/dev/null)"
  i=$((i + 1))
done

[ $fails -eq 0 ] && { echo "PASS -- PROP-24 fault-injection: Mode A makes ZERO dynamic calls to the shared publish function under any corrupted branch-selection input"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
