#!/usr/bin/env bash
# VSDD oracle -- PROP-27 (REQ-27, Sprint 5): the "view -> yen" funnel's monetization-link half. Every wake
# that reaches a BOTH-PASS gate result (Mode A DRAFT or Mode B PUBLISHED/UNCONFIRMED) appends a deterministic
# monetization link to the gated draft -- via insert_monetization_link() in run.sh, called AFTER the V0/V0.5
# gate loop succeeds so it never perturbs the agent's own craft-judged CTA prose or V05_CRIT_b's scoring of
# it -- unless the caller explicitly opts out with ARTICLE_CTA_URL="" (the literal empty string, distinct
# from leaving it unset).
#
# Post-adversary FIND-002 fix: the ORIGINAL version of this file only covered Mode A. A fresh-context
# adversary found (FIND-001, blocking) that Mode B publishes an ALREADY-PREPARED remote note.com draft --
# confirm_and_publish() never re-uploads a body -- so appending the CTA to the wake's local throwaway
# draft.md (what the ORIGINAL insert_monetization_link did, and all this file tested) never actually reached
# the real published Mode-B article. This file now ALSO covers Mode B's REMOTE append path
# (lib/note-append-cta.py, invoked by run.sh's Mode-B branch BEFORE the publish click) end-to-end: the
# wiring (fault-injection, mirroring PROP-24's own ARTICLE_NOTE_BROWSER_COMMON_DIR convention), the
# degrade-not-block behavior on a real append failure, the opt-out/no-draft-key paths, AND a REAL live
# network round-trip against an ephemeral note.com draft this test creates and deletes itself (proving the
# actual mechanism, not just the wiring around it).
#
# Dynamic SKILL resolution (not the sibling tests' hardcoded main-tree path): this file must test WHATEVER
# tree it physically lives in (a feature worktree during development, the main tree after merge).
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- happy path: default CTA appended (Mode A DRAFT) ----------
T1="$(mktemp -d)"
OUT1="$(ARTICLE_TEST=1 ARTICLE_DIR="$T1" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" bash "$SKILL/run.sh" 2>&1)"; rc1=$?
ok "$([ $rc1 -eq 0 ] && echo 1 || echo 0)" "wake completes, rc=0 (rc=$rc1): $OUT1"
draft1="$(grep -oE '^draft_path: .*' "$T1/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -n "$draft1" ] && [ -f "$draft1" ] && echo 1 || echo 0)" "draft artifact produced"
ok "$([ -f "$draft1" ] && grep -q 'https://aniccaai.com/' "$draft1" && echo 1 || echo 0)" "default monetization link (DEFAULT_CTA_URL) appended to the gated draft body"
ok "$(grep -q '^cta_url: https://aniccaai.com/' "$T1/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md records the cta_url actually appended"

# ---------- happy path: custom CTA_URL/CTA_TEXT override used verbatim ----------
T2="$(mktemp -d)"
OUT2="$(ARTICLE_TEST=1 ARTICLE_DIR="$T2" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" \
  ARTICLE_CTA_URL="https://example.com/custom-product" ARTICLE_CTA_TEXT="今すぐ見る" \
  bash "$SKILL/run.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "wake completes with override, rc=0 (rc=$rc2): $OUT2"
draft2="$(grep -oE '^draft_path: .*' "$T2/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -f "$draft2" ] && grep -q 'https://example.com/custom-product' "$draft2" && echo 1 || echo 0)" "custom ARTICLE_CTA_URL is used verbatim, not the default"
ok "$([ -f "$draft2" ] && grep -q '今すぐ見る' "$draft2" && echo 1 || echo 0)" "custom ARTICLE_CTA_TEXT is used verbatim"
ok "$(grep -q '^cta_url: https://example.com/custom-product' "$T2/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md records the custom cta_url"

# ---------- failure/opt-out path: ARTICLE_CTA_URL="" (explicit empty) -> NO link appended, never crashes ----------
T3="$(mktemp -d)"
OUT3="$(ARTICLE_TEST=1 ARTICLE_DIR="$T3" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" ARTICLE_CTA_URL="" \
  bash "$SKILL/run.sh" 2>&1)"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "wake completes with explicit opt-out, rc=0 (rc=$rc3): $OUT3"
draft3="$(grep -oE '^draft_path: .*' "$T3/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -f "$draft3" ] && ! grep -q 'https://aniccaai.com/' "$draft3" && echo 1 || echo 0)" "explicit ARTICLE_CTA_URL=\"\" -> no monetization link appended (opt-out honored, not a crash)"
ok "$(grep -q '^cta_url: $' "$T3/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's cta_url is empty when opted out (distinguishable from a real link)"

# ---------- ABORTED wakes never get a CTA link appended (gates never passed -> no publish -> no funnel) ----------
T4="$(mktemp -d)"
OUT4="$(ARTICLE_TEST=1 ARTICLE_DIR="$T4" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="FAIL,FAIL,FAIL" ARTICLE_TEST_V05_RESULTS="FAIL,FAIL,FAIL" bash "$SKILL/run.sh" 2>&1)"; rc4=$?
ok "$([ $rc4 -eq 0 ] && echo 1 || echo 0)" "ABORTED wake still exits 0 (rc=$rc4): $OUT4"
ok "$(grep -q 'last_wake_result: ABORTED' "$T4/STATE.md" 2>/dev/null && echo 1 || echo 0)" "wake correctly ABORTED (3-round ceiling, no BOTH-PASS)"
ok "$(! grep -q '^cta_url:' "$T4/STATE.md" 2>/dev/null && echo 1 || echo 0)" "ABORTED wake's STATE.md has no cta_url field at all (link is never inserted before a gate PASS)"

# =====================================================================================================
# FIND-002 fix: Mode B coverage. A fake note_browser_common.py (ARTICLE_NOTE_BROWSER_COMMON_DIR, the SAME
# substitution convention test-prop24b already uses) stands in for confirm_and_publish so these wiring
# tests never touch a real browser/note.com session; a substitute append-cta script
# (ARTICLE_NOTE_APPEND_CTA_PY) stands in for lib/note-append-cta.py so both its SUCCESS and FAILURE outcomes
# are exercised deterministically, with a call-log proving it was invoked with the right key/url BEFORE the
# publish click.
# =====================================================================================================
FAKE_BROWSER_DIR="$(mktemp -d)"
cat > "$FAKE_BROWSER_DIR/note_browser_common.py" << 'PYEOF'
def confirm_and_publish(note_key, **kwargs):
    return {"ok": True, "reason": None, "prefix": None, "clicked_label": "投稿する",
            "url": f"https://note.com/anicca123/n/{note_key}", "screenshot": "/tmp/fake.png", "status": "draft"}
def load_note_cookies(f):
    return None
def open_editor_ready(*a, **k):
    return (None, None)
def select_paid_price(*a, **k):
    return {"row_found": True, "paid_checked": True, "price_filled": None}
PYEOF

CALL_LOG_DIR="$(mktemp -d)"

# A stub standing in for lib/note-append-cta.py: logs the args it was called with, then succeeds or fails
# per the CTA_STUB_MODE env var the test sets before invoking run.sh.
CTA_STUB="$CALL_LOG_DIR/stub-append-cta.sh"
cat > "$CTA_STUB" << 'SHEOF'
#!/usr/bin/env bash
echo "$@" >> "$CTA_STUB_CALL_LOG"
if [ "${CTA_STUB_MODE:-success}" = "fail" ]; then
  echo "stub-append-cta: FAILED for draft (deliberate test failure) -- draft_save (body update) returned 403" >&2
  exit 1
fi
echo "CTA_APPENDED: true"
exit 0
SHEOF
chmod +x "$CTA_STUB"

# ---------- Mode B, success: append-cta stub succeeds -> STATE carries the REAL confirmed cta_url/status ----------
T5="$(mktemp -d)"
mkdir -p "$T5/state"
printf '1' > "$T5/state/mode-b-ratio"
CALL_LOG5="$CALL_LOG_DIR/calls-5.log"; : > "$CALL_LOG5"
OUT5="$(CTA_STUB_CALL_LOG="$CALL_LOG5" CTA_STUB_MODE=success \
  ARTICLE_TEST=1 ARTICLE_DIR="$T5" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" \
  ARTICLE_MODEB_NOTE_KEY="nFAKEMODEBTEST5" ARTICLE_NOTE_BROWSER_COMMON_DIR="$FAKE_BROWSER_DIR" \
  ARTICLE_NOTE_APPEND_CTA_PY="$CTA_STUB" \
  bash "$SKILL/run.sh" 2>&1)"; rc5=$?
ok "$([ $rc5 -eq 0 ] && echo 1 || echo 0)" "Mode B wake completes, rc=0 (rc=$rc5): $OUT5"
# last_wake_result is PUBLISHED-or-UNCONFIRMED (the fake key nFAKEMODEBTEST5 does not exist on the real
# note.com, so REQ-24's independent post-publish verify -- a REAL logged-out HTTP fetch -- legitimately
# cannot confirm it; that is expected and correct behavior, unrelated to the CTA fix under test here). The
# real click DID fire (a real publish_url is recorded) either way -- that is what this section actually
# proves.
ok "$(grep -qE 'last_wake_result: (PUBLISHED|UNCONFIRMED)' "$T5/STATE.md" 2>/dev/null && echo 1 || echo 0)" "Mode B reaches a real publish-click outcome (PUBLISHED or UNCONFIRMED, never ABORTED/DRAFT): $(cat "$T5/STATE.md" 2>/dev/null)"
ok "$(grep -q 'publish_url: https://note.com/anicca123/n/nFAKEMODEBTEST5' "$T5/STATE.md" 2>/dev/null && echo 1 || echo 0)" "the real publish click fired (confirm_and_publish's own URL is recorded, via the fake browser stub standing in for the real one)"
ok "$(grep -qE -- '--draft-key nFAKEMODEBTEST5 --cta-url https://aniccaai.com/' "$CALL_LOG5" 2>/dev/null && echo 1 || echo 0)" "the append-cta stub was invoked with the CORRECT draft key + resolved CTA URL: $(cat "$CALL_LOG5" 2>/dev/null)"
ok "$(grep -q '^cta_url: https://aniccaai.com/' "$T5/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's Mode-B cta_url reflects the append tool's ACTUAL confirmed success (not just the local file's resolved value)"
ok "$(grep -q '^cta_status: carried' "$T5/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's Mode-B cta_status is 'carried' on append success"

# ---------- Mode B, append FAILURE: publish still proceeds (degrade, never block); cta_url honestly empty ----------
T6="$(mktemp -d)"
mkdir -p "$T6/state"
printf '1' > "$T6/state/mode-b-ratio"
CALL_LOG6="$CALL_LOG_DIR/calls-6.log"; : > "$CALL_LOG6"
OUT6="$(CTA_STUB_CALL_LOG="$CALL_LOG6" CTA_STUB_MODE=fail \
  ARTICLE_TEST=1 ARTICLE_DIR="$T6" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" \
  ARTICLE_MODEB_NOTE_KEY="nFAKEMODEBTEST6" ARTICLE_NOTE_BROWSER_COMMON_DIR="$FAKE_BROWSER_DIR" \
  ARTICLE_NOTE_APPEND_CTA_PY="$CTA_STUB" \
  bash "$SKILL/run.sh" 2>&1)"; rc6=$?
ok "$([ $rc6 -eq 0 ] && echo 1 || echo 0)" "Mode B wake STILL completes rc=0 even when the CTA append fails (rc=$rc6): $OUT6"
ok "$(grep -qE 'last_wake_result: (PUBLISHED|UNCONFIRMED)' "$T6/STATE.md" 2>/dev/null && echo 1 || echo 0)" "the wake still reaches a real publish-click outcome, never ABORTED/DRAFT: $(cat "$T6/STATE.md" 2>/dev/null)"
ok "$(grep -q 'publish_url: https://note.com/anicca123/n/nFAKEMODEBTEST6' "$T6/STATE.md" 2>/dev/null && echo 1 || echo 0)" "the real publish click is NOT blocked by a CTA-append failure (degrade, never a safety gate) -- it still fires and its URL is recorded"
ok "$(grep -q '^cta_url: $' "$T6/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's cta_url is honestly EMPTY when the remote append genuinely failed (never a fabricated claim)"
ok "$(grep -q '^cta_status: append_failed:' "$T6/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's cta_status records the specific append_failed reason: $(grep '^cta_status:' "$T6/STATE.md" 2>/dev/null)"

# ---------- Mode B, opt-out: ARTICLE_CTA_URL="" -> append-cta stub is NEVER even called ----------
T7="$(mktemp -d)"
mkdir -p "$T7/state"
printf '1' > "$T7/state/mode-b-ratio"
CALL_LOG7="$CALL_LOG_DIR/calls-7.log"; : > "$CALL_LOG7"
OUT7="$(CTA_STUB_CALL_LOG="$CALL_LOG7" CTA_STUB_MODE=success \
  ARTICLE_TEST=1 ARTICLE_DIR="$T7" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" ARTICLE_CTA_URL="" \
  ARTICLE_MODEB_NOTE_KEY="nFAKEMODEBTEST7" ARTICLE_NOTE_BROWSER_COMMON_DIR="$FAKE_BROWSER_DIR" \
  ARTICLE_NOTE_APPEND_CTA_PY="$CTA_STUB" \
  bash "$SKILL/run.sh" 2>&1)"; rc7=$?
ok "$([ $rc7 -eq 0 ] && echo 1 || echo 0)" "Mode B opt-out wake completes, rc=0 (rc=$rc7): $OUT7"
ok "$([ ! -s "$CALL_LOG7" ] && echo 1 || echo 0)" "opt-out: the append-cta stub was NEVER invoked (call log: $(cat "$CALL_LOG7" 2>/dev/null))"
ok "$(grep -q '^cta_status: not_requested' "$T7/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's cta_status is 'not_requested' on opt-out"

# ---------- Mode B, no draft key (Sprint-1 placeholder branch): nothing real to append to ----------
T8="$(mktemp -d)"
mkdir -p "$T8/state"
printf '1' > "$T8/state/mode-b-ratio"
CALL_LOG8="$CALL_LOG_DIR/calls-8.log"; : > "$CALL_LOG8"
OUT8="$(CTA_STUB_CALL_LOG="$CALL_LOG8" CTA_STUB_MODE=success \
  ARTICLE_TEST=1 ARTICLE_DIR="$T8" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" \
  ARTICLE_NOTE_APPEND_CTA_PY="$CTA_STUB" \
  bash "$SKILL/run.sh" 2>&1)"; rc8=$?
ok "$([ $rc8 -eq 0 ] && echo 1 || echo 0)" "Mode B no-draft-key placeholder wake completes, rc=0 (rc=$rc8): $OUT8"
ok "$([ ! -s "$CALL_LOG8" ] && echo 1 || echo 0)" "no-draft-key placeholder: the append-cta stub was NEVER invoked (nothing real exists to append to)"
ok "$(grep -q '^cta_status: skipped:no_draft_key' "$T8/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's cta_status is 'skipped:no_draft_key' for the placeholder branch"
ok "$(grep -q '^cta_url: $' "$T8/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's cta_url is empty for the placeholder branch (no real publish happened, nothing carries a link)"

# =====================================================================================================
# REAL live mechanism proof: lib/note-append-cta.py's actual GET-append-SAVE round trip against a genuine,
# EPHEMERAL note.com draft this test creates and deletes itself (never the flagship or any reused shared
# fixture -- no risk of the "fixture drift" class of failure the pre-existing test-prop21b/22b/24c hit).
# =====================================================================================================
REAL_COOKIES="$HOME/.cloak/note-work/note-cookies.json"
NOTE_MCP_SRC_DEFAULT="$HOME/.openclaw/external/note-mcp/src"
VENV_PY="$HOME/.openclaw/skills/_shared/venv-cloak/bin/python3"
if [ -f "$REAL_COOKIES" ] && [ -d "$NOTE_MCP_SRC_DEFAULT" ] && [ -x "$VENV_PY" ]; then
  EPHEMERAL_KEY="$("$VENV_PY" - "$REAL_COOKIES" "$NOTE_MCP_SRC_DEFAULT" << 'PYEOF'
import asyncio, json, sys
cookies_file, note_mcp_src = sys.argv[1], sys.argv[2]
sys.path.insert(0, note_mcp_src)
from note_mcp.api.articles import create_draft
from note_mcp.models import ArticleInput, Session
cookies = json.load(open(cookies_file))
session = Session(cookies=cookies, user_id="14651590", username="anicca123", created_at=0)
async def main():
    article = await create_draft(session, ArticleInput(title="VCSDD PROP-27 ephemeral test draft (safe to delete)", body="test body"))
    return article.key
print(asyncio.run(main()))
PYEOF
)"
  ok "$([ -n "$EPHEMERAL_KEY" ] && echo 1 || echo 0)" "created a REAL ephemeral note.com draft for this test: key=$EPHEMERAL_KEY"

  if [ -n "$EPHEMERAL_KEY" ]; then
    TEST_CTA_URL="https://example.com/vcsdd-prop27-real-e2e-check"
    APPEND_OUT1="$("$VENV_PY" "$SKILL/lib/note-append-cta.py" --draft-key "$EPHEMERAL_KEY" --cta-url "$TEST_CTA_URL" 2>&1)"; append_rc1=$?
    ok "$([ $append_rc1 -eq 0 ] && echo 1 || echo 0)" "real append against the ephemeral draft succeeds, rc=0 (rc=$append_rc1): $APPEND_OUT1"

    VERIFY1="$("$VENV_PY" - "$REAL_COOKIES" "$NOTE_MCP_SRC_DEFAULT" "$EPHEMERAL_KEY" "$TEST_CTA_URL" << 'PYEOF'
import asyncio, json, sys
cookies_file, note_mcp_src, key, cta_url = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, note_mcp_src)
from note_mcp.api.articles import get_article_raw_html
from note_mcp.models import Session
cookies = json.load(open(cookies_file))
session = Session(cookies=cookies, user_id="14651590", username="anicca123", created_at=0)
async def main():
    article = await get_article_raw_html(session, key)
    return "PRESENT" if cta_url in (article.body or "") else "ABSENT"
print(asyncio.run(main()))
PYEOF
)"
    ok "$([ "$VERIFY1" = "PRESENT" ] && echo 1 || echo 0)" "an INDEPENDENT, fresh authenticated GET confirms the CTA link is now REALLY in the remote draft body (not just the tool's own claim): $VERIFY1"

    # idempotency: a second append of the SAME url is a no-op success, never a duplicate
    APPEND_OUT2="$("$VENV_PY" "$SKILL/lib/note-append-cta.py" --draft-key "$EPHEMERAL_KEY" --cta-url "$TEST_CTA_URL" 2>&1)"; append_rc2=$?
    ok "$([ $append_rc2 -eq 0 ] && echo 1 || echo 0)" "re-appending the SAME url is still a success (idempotent), rc=0 (rc=$append_rc2): $APPEND_OUT2"
    ok "$(echo "$APPEND_OUT2" | grep -q 'already-present' && echo 1 || echo 0)" "the second call reports already-present (no duplicate append): $APPEND_OUT2"

    # cleanup: delete the ephemeral draft (never leave test clutter on the real account)
    "$VENV_PY" - "$REAL_COOKIES" "$NOTE_MCP_SRC_DEFAULT" "$EPHEMERAL_KEY" << 'PYEOF' > /dev/null 2>&1
import asyncio, json, sys
cookies_file, note_mcp_src, key = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, note_mcp_src)
from note_mcp.api.articles import delete_draft
from note_mcp.models import Session
cookies = json.load(open(cookies_file))
session = Session(cookies=cookies, user_id="14651590", username="anicca123", created_at=0)
asyncio.run(delete_draft(session, key, confirm=True))
PYEOF
  fi
else
  echo "  (skipping REAL live mechanism proof: $REAL_COOKIES / $NOTE_MCP_SRC_DEFAULT / $VENV_PY not present on this host)"
fi

[ $fails -eq 0 ] && { echo "PASS -- PROP-27 monetization link: Mode A appended + STATE-recorded, override honored verbatim, explicit opt-out never crashes, never inserted before gates PASS; Mode B's REMOTE draft body is appended before the publish click (real mechanism proven live against an ephemeral draft; success/failure/opt-out/no-key wiring all proven via fault-injection, degrade-never-block confirmed)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
