#!/usr/bin/env bash
# VSDD oracle -- PROP-24 (REQ-23, Sprint 4), REAL success path: run.sh's Mode-B branch, given a
# confirmed-ready TEST draft and a ratio config resolving THIS wake to Mode B, actually fires a REAL
# 投稿する/更新する click via run.sh ITSELF (never by calling lib/note-publish-live.py or
# lib/note-mode-b-publish.py directly) and the in-loop independent verify (REQ-24) records SUCCESS with
# url+timestamp+result.
#
# ★★★ SAFETY: hardcoded, literal keys -- this test may NEVER touch the flagship draft. ★★★
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"

TEST_DRAFT_KEY="ne94efe526c9a"
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
       "PROP-24's real success path requires a genuine live browser session and cannot be hermetically stubbed."
  exit 0
fi

T="$(mktemp -d)"
mkdir -p "$T/state"
printf '1' > "$T/state/mode-b-ratio"   # 1-in-1: this wake resolves to Mode B

OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" \
  ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS=PASS ARTICLE_TEST_V05_RESULTS=PASS \
  ARTICLE_MODEB_NOTE_KEY="$TEST_DRAFT_KEY" NOTE_MCP_PY="$VENV_PY" \
  bash "$SKILL/run.sh" 2>&1)"; rc=$?
echo "  run.sh output: $OUT"

ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "run.sh's Mode-B branch completes rc=0 firing a REAL click via the shared function (rc=$rc)"
ok "$(grep -q 'last_wake_result: PUBLISHED' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE records PUBLISHED (real click + verify SUCCESS), via run.sh -- never note-publish-live.py directly: $(cat "$T/STATE.md" 2>/dev/null)"
ok "$(grep -q "publish_url: https://note.com/anicca123/n/$TEST_DRAFT_KEY" "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE carries the real publish_url for the TEST draft"
ok "$(grep -q 'publish_verify_result: SUCCESS' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE carries publish_verify_result: SUCCESS (independent in-loop verify, REQ-24)"
ok "$(grep -q 'publish_verified_at:' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE carries a verification timestamp"

# independent, separate confirmation the click had a real effect
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
ok "$(echo "$POSTCHECK" | grep -q '"status": "published"' && echo 1 || echo 0)" "TEST draft $TEST_DRAFT_KEY independently confirmed status=published after run.sh's Mode-B in-loop click"

# safety: the flagship draft was never touched by this run
ok "$(! echo "$OUT" | grep -q "$FLAGSHIP_DRAFT_KEY" && echo 1 || echo 0)" "flagship draft key never appears anywhere in this run's output"
ok "$(! grep -q "$FLAGSHIP_DRAFT_KEY" "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "flagship draft key never appears in STATE.md"

[ $fails -eq 0 ] && { echo "PASS -- PROP-24 real success path: run.sh's Mode-B branch fired a REAL click via the shared function against TEST draft $TEST_DRAFT_KEY"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
