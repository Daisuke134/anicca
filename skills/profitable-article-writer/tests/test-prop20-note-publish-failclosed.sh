#!/usr/bin/env bash
# VSDD oracle — PROP-20 (REQ-19, Sprint 2): Mode-A's REAL note.com DRAFT publish wiring (lib/note_publish.sh)
# is reachable and fail-closed:
#   (a) with no note-integration requested (ARTICLE_NOTE_TITLE unset) -> Mode A behaves EXACTLY like Sprint 1
#       (pending-human-review placeholder, zero regression).
#   (b) with note-integration requested and the (hermetic test-seam) note-publish call FORCED to fail ->
#       Mode A degrades to the safe placeholder, NEVER crashes the wake, NEVER fakes a URL.
#   (c) with note-integration requested and FORCED to succeed -> Mode A's notify.json carries the REAL url
#       + screenshot the wiring returned — proving the wiring is genuinely reachable end-to-end.
# NOTE_PUBLISH_TEST_FORCE is the hermetic seam (same convention as ARTICLE_TEST_FORCE_V0/V05): it never
# touches network/browser, so this suite stays offline; the REAL (non-forced) python/note_mcp/browser call
# path is exercised only by an actual live wake (Sprint-2 real-run evidence), never by this test file.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- (a) note-integration NOT requested -> unchanged Sprint-1 Mode A behavior ----------
T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "no note-integration requested: Mode A wake completes, rc=0 (rc=$rc)"
ok "$(grep -q '"url": "pending-human-review"' "$T/notify.json" 2>/dev/null && echo 1 || echo 0)" "no note-integration requested: notify.json keeps the Sprint-1 placeholder url (zero regression)"

# ---------- (b) note-integration requested, forced FAIL -> degrade to placeholder, never crash, never fake ----------
T2="$(mktemp -d)"
FAKE_DRAFT="$T2/fake.md"
printf '# fake\n\nbody\n' > "$FAKE_DRAFT"
OUT2="$(ARTICLE_TEST=1 ARTICLE_DIR="$T2" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" ARTICLE_NOTE_TITLE="test title" \
  NOTE_PUBLISH_TEST_FORCE=fail bash "$SKILL/run.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "note-publish FORCED to fail: wake still completes cleanly, rc=0 (rc=$rc2, harness error would be a real bug): $OUT2"
ok "$(grep -q 'last_wake_result: DRAFT' "$T2/STATE.md" 2>/dev/null && echo 1 || echo 0)" "note-publish FORCED to fail: STATE result is still DRAFT (never crashes the whole wake)"
ok "$([ -f "$T2/notify.json" ] && ! grep -q '"url": "NOTE_TEST_URL' "$T2/notify.json" && echo 1 || echo 0)" "note-publish FORCED to fail: notify.json never fakes a live URL"

# ---------- (c) note-integration requested, forced SUCCESS -> notify.json carries the REAL returned url/screenshot ----------
T3="$(mktemp -d)"
OUT3="$(ARTICLE_TEST=1 ARTICLE_DIR="$T3" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" ARTICLE_NOTE_TITLE="test title" \
  NOTE_PUBLISH_TEST_FORCE=success bash "$SKILL/run.sh" 2>&1)"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "note-publish FORCED to succeed: wake completes, rc=0 (rc=$rc3): $OUT3"
ok "$(grep -q 'NOTE_TEST_URL' "$T3/notify.json" 2>/dev/null && echo 1 || echo 0)" "note-publish FORCED to succeed: notify.json carries the wiring's REAL returned url (reachable end-to-end)"

[ $fails -eq 0 ] && { echo "PASS — PROP-20 Mode-A real note-publish wiring is reachable and fail-closed"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
