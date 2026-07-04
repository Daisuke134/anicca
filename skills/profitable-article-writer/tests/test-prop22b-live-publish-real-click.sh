#!/usr/bin/env bash
# VSDD oracle -- PROP-22b (REQ-21, Sprint 2.5): the REAL success path of lib/note-publish-live.py. This is
# the ONLY test file in this suite permitted to fire a real 投稿する/更新する click, and it MUST target the
# TEST draft n39ef09f828f7 -- NEVER the flagship draft nfb2ace9f0ed8 (that one is reserved for the main
# agent to publish personally, as a deliberate one-off, after this sprint converges).
#
# Per Sprint-2 evidence (state/2026-07-04 exploration + note_mcp GET /v3/notes/n39ef09f828f7), this draft
# already carries: status=draft, eyecatch set (a real assets.st-note.com URL), and 3 <img> markers in its
# body -- i.e. it already satisfies PROP-22's eyecatch+visuals confirm gates. This test supplies
# NOTE_LIVE_PUBLISH=1 + the exact draft key and lets the tool's own price/type gate (browser-driven, since
# that state is not persisted) run for real, then asserts the tool ACTUALLY reached and fired the
# 投稿する/更新する click -- an always-refuse stub cannot pass this test.
#
# Requires the REAL cloakbrowser + note_mcp + a real note.com session (this skill's own venv-cloak python +
# ~/.cloak/note-work/note-cookies.json) -- this is a genuine T2 real-browser/real-network test, not a
# hermetic T1 stub. It is skipped (not failed) if that real environment is unavailable, so this suite still
# runs cleanly on a host with no note.com credentials provisioned.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
TOOL="$SKILL/lib/note-publish-live.py"

# ★★★ SAFETY: hardcoded, literal keys -- this test may NEVER touch the flagship draft. ★★★
TEST_DRAFT_KEY="n39ef09f828f7"
FLAGSHIP_DRAFT_KEY="nfb2ace9f0ed8"
if [ "$TEST_DRAFT_KEY" = "$FLAGSHIP_DRAFT_KEY" ]; then
  echo "SAFETY ABORT: TEST_DRAFT_KEY must never equal FLAGSHIP_DRAFT_KEY" >&2
  exit 3
fi

fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

VENV_PY="$HOME/.openclaw/skills/_shared/venv-cloak/bin/python3"
COOKIES_FILE="${NOTE_COOKIES_FILE:-$HOME/.cloak/note-work/note-cookies.json}"
NOTE_MCP_SRC_DEFAULT="$HOME/.openclaw/external/note-mcp/src"

if [ ! -x "$VENV_PY" ] || [ ! -f "$COOKIES_FILE" ] || [ ! -d "$NOTE_MCP_SRC_DEFAULT" ]; then
  echo "SKIP -- real cloakbrowser/note_mcp/note.com-cookies environment not available on this host " \
       "(venv_py=$([ -x "$VENV_PY" ] && echo present || echo MISSING), " \
       "cookies=$([ -f "$COOKIES_FILE" ] && echo present || echo MISSING), " \
       "note_mcp_src=$([ -d "$NOTE_MCP_SRC_DEFAULT" ] && echo present || echo MISSING)) -- " \
       "PROP-22b requires a genuine live browser session and cannot be hermetically stubbed for its own " \
       "real-success-path assertion."
  exit 0
fi

# ---------- an always-refuse stub CANNOT pass this test: verify note-publish-live.py's own confirm-gate
# code path (the thing that would make a stub refuse) is not what we are about to invoke unconditionally --
# i.e. confirm the draft's pre-publish state independently FIRST, via the real, authenticated note_mcp
# client, so a genuine PROP-22b failure (tool refuses on a draft that IS actually ready) is distinguishable
# from an environment problem. ----------
PRECHECK="$("$VENV_PY" -c "
import asyncio, json, sys
sys.path.insert(0, '$NOTE_MCP_SRC_DEFAULT')
from note_mcp.api.client import NoteAPIClient
from note_mcp.models import Session
cookies = json.load(open('$COOKIES_FILE'))
session = Session(cookies=cookies, user_id='14651590', username='anicca123', created_at=0)
async def main():
    async with NoteAPIClient(session) as client:
        r = await client.get('/v3/notes/$TEST_DRAFT_KEY')
        d = r.get('data', {})
        body = (d.get('note_draft') or {}).get('body') or d.get('body') or ''
        print(json.dumps({'status': d.get('status'), 'eyecatch': bool(d.get('eyecatch')), 'img_count': body.count('<img')}))
asyncio.run(main())
" 2>/dev/null)"
echo "  precheck (independent, real): $PRECHECK"
ok "$(echo "$PRECHECK" | grep -q '"eyecatch": true' && echo 1 || echo 0)" "TEST draft $TEST_DRAFT_KEY independently confirmed to have eyecatch set (precondition for this test to be meaningful)"
ok "$(echo "$PRECHECK" | grep -qE '"img_count": [1-9]' && echo 1 || echo 0)" "TEST draft $TEST_DRAFT_KEY independently confirmed to have >=1 <img> tag (precondition for this test to be meaningful)"

# ---------- THE REAL INVOCATION -- fires a genuine 投稿する/更新する click against the TEST draft ----------
OUT="$(NOTE_LIVE_PUBLISH=1 NOTE_PRICE=500 "$VENV_PY" "$TOOL" --draft-key "$TEST_DRAFT_KEY" 2>&1)"; RC=$?
echo "  tool output: $OUT"
ok "$([ $RC -eq 0 ] && echo 1 || echo 0)" "note-publish-live.py against the REAL, confirmed-ready TEST draft -> rc=0 (rc=$RC) -- an always-refuse stub would fail this"
ok "$(echo "$OUT" | grep -q "NOTE_LIVE_URL: https://note.com/anicca123/n/$TEST_DRAFT_KEY" && echo 1 || echo 0)" "stdout carries the REAL live URL for the TEST draft (not a fabricated/placeholder URL)"
ok "$(echo "$OUT" | grep -q 'NOTE_LIVE_SCREENSHOT:' && echo 1 || echo 0)" "stdout carries a screenshot path"
ok "$(echo "$OUT" | grep -qE 'NOTE_LIVE_CLICKED: (投稿する|更新する)' && echo 1 || echo 0)" "the tool's own log confirms it actually clicked 投稿する or 更新する (a real click occurred, not a refusal)"

# ---------- independent confirmation the click had a real effect: the draft's status flips away from
# plain 'draft' (note.com marks a just-published article 'published' via the same authenticated GET). ----------
POSTCHECK="$("$VENV_PY" -c "
import asyncio, json, sys
sys.path.insert(0, '$NOTE_MCP_SRC_DEFAULT')
from note_mcp.api.client import NoteAPIClient
from note_mcp.models import Session
cookies = json.load(open('$COOKIES_FILE'))
session = Session(cookies=cookies, user_id='14651590', username='anicca123', created_at=0)
async def main():
    async with NoteAPIClient(session) as client:
        r = await client.get('/v3/notes/$TEST_DRAFT_KEY')
        print(json.dumps({'status': r.get('data', {}).get('status')}))
asyncio.run(main())
" 2>/dev/null)"
echo "  postcheck (independent, real): $POSTCHECK"
ok "$(echo "$POSTCHECK" | grep -q '"status": "published"' && echo 1 || echo 0)" "draft $TEST_DRAFT_KEY's status independently confirmed flipped to 'published' after the real click"

# ---------- safety: the flagship draft was never touched by this run ----------
ok "$(! echo "$OUT" | grep -q "$FLAGSHIP_DRAFT_KEY" && echo 1 || echo 0)" "the flagship draft key never appears anywhere in this test's own tool output"

[ $fails -eq 0 ] && { echo "PASS -- PROP-22b: note-publish-live.py fired a REAL 投稿する/更新する click against TEST draft $TEST_DRAFT_KEY, independently confirmed live"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
