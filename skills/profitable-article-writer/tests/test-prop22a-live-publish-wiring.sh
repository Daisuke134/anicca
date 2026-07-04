#!/usr/bin/env bash
# VSDD oracle -- PROP-22a (REQ-21, Sprint 2.5): lib/note-publish-live.py is a STANDALONE, one-off tool,
# structurally excluded from run.sh's call graph, and fail-closed at every gate BEFORE any browser action:
#   (a) grep: run.sh NEVER references note-publish-live.py -- structural, always true.
#   (b) NOTE_LIVE_PUBLISH unset -> refuses immediately, ZERO browser action (proven by running under a
#       plain `python3` that has no cloakbrowser installed at all -- if the refusal path incorrectly
#       reached the browser layer, this would surface as a raw ModuleNotFoundError traceback, not this
#       tool's own clean refusal message).
#   (c) missing --draft-key -> refuses with a clear argparse error.
#   (d) NOTE_LIVE_PUBLISH=1 + a draft-key whose pre-publish state is UNCONFIRMED (stubbed note_mcp fixture
#       with no eyecatch set) -> refuses, no click, and -- again -- zero browser action (same
#       no-cloakbrowser-installed proof as (b): the eyecatch/visuals gate runs BEFORE note_browser_common
#       is ever imported).
# This is a T1 hermetic wiring test: no real creds, no real network, no real browser dependency at all.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
RUN_SH="$SKILL/run.sh"
TOOL="$SKILL/lib/note-publish-live.py"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# a plain, non-venv python3 that (per this environment) has NO cloakbrowser installed -- used deliberately
# for the refusal-path checks so any accidental browser-layer import surfaces as a traceback, not a clean
# refusal (proving the refusal genuinely happens before note_browser_common/cloakbrowser is ever touched).
PLAIN_PY="python3"
if $PLAIN_PY -c "import cloakbrowser" >/dev/null 2>&1; then
  echo "  - WARN: plain python3 unexpectedly has cloakbrowser importable; the no-browser-touched proof for (b)/(d) is weaker on this host" >&2
fi

# ---------- (a) run.sh never references note-publish-live.py (structural) ----------
ok "$([ -f "$TOOL" ] && echo 1 || echo 0)" "lib/note-publish-live.py exists"
ok "$([ -f "$RUN_SH" ] && echo 1 || echo 0)" "run.sh exists"
if [ -f "$RUN_SH" ]; then
  ok "$(! grep -q 'note-publish-live' "$RUN_SH" 2>/dev/null && echo 1 || echo 0)" "run.sh never references note-publish-live.py (grep 0 hits)"
fi
# also confirm no file in run.sh's own call graph (gates/, identity/, lib/note_publish.sh -- the Mode-A/
# AUTONOMY wiring run.sh actually sources) IMPORTS/SOURCES/EXECs note-publish-live.py. Doc-comment mentions
# in other lib/*.py files (e.g. note_browser_common.py's docstring explaining the shared helper, or
# note-verify-live.py's docstring explaining it is a SEPARATE process) are expected and fine -- this check
# looks for an actual invocation shape (import/source/exec/subprocess-call), not prose.
CALL_GRAPH_FILES="$SKILL/lib/note_publish.sh $SKILL/gates/v0.sh $SKILL/gates/v05.sh"
[ -d "$SKILL/identity" ] && CALL_GRAPH_FILES="$CALL_GRAPH_FILES $(find "$SKILL/identity" -type f 2>/dev/null)"
BAD_INVOCATION=0
for f in $CALL_GRAPH_FILES; do
  [ -f "$f" ] || continue
  if grep -qE 'source .*note-publish-live|import note.publish.live|note-publish-live\.py' "$f" 2>/dev/null; then
    BAD_INVOCATION=1
    echo "  - unexpected reference to note-publish-live.py in run.sh's call graph: $f" >&2
  fi
done
ok "$([ $BAD_INVOCATION -eq 0 ] && echo 1 || echo 0)" "no file in run.sh's own call graph (lib/note_publish.sh, gates/, identity/) invokes note-publish-live.py"

# ---------- (b) NOTE_LIVE_PUBLISH unset -> refuse immediately, zero browser action ----------
OUT_B="$(env -u NOTE_LIVE_PUBLISH $PLAIN_PY "$TOOL" --draft-key n39ef09f828f7 2>&1)"; RC_B=$?
ok "$([ $RC_B -ne 0 ] && echo 1 || echo 0)" "NOTE_LIVE_PUBLISH unset -> non-zero exit (rc=$RC_B)"
ok "$(echo "$OUT_B" | grep -q 'NOTE_LIVE_PUBLISH' && echo 1 || echo 0)" "NOTE_LIVE_PUBLISH unset -> stderr names the missing trigger: $OUT_B"
ok "$(! echo "$OUT_B" | grep -qi 'cloakbrowser\|ModuleNotFoundError\|Traceback' && echo 1 || echo 0)" "NOTE_LIVE_PUBLISH unset -> no browser/traceback surface (zero browser action): $OUT_B"

# ---------- (c) missing --draft-key -> clear error ----------
OUT_C="$(NOTE_LIVE_PUBLISH=1 $PLAIN_PY "$TOOL" 2>&1)"; RC_C=$?
ok "$([ $RC_C -ne 0 ] && echo 1 || echo 0)" "missing --draft-key -> non-zero exit (rc=$RC_C)"
ok "$(echo "$OUT_C" | grep -qi 'draft-key' && echo 1 || echo 0)" "missing --draft-key -> stderr names the missing argument: $OUT_C"

# ---------- (d) NOTE_LIVE_PUBLISH=1 + UNCONFIRMED pre-publish state (stubbed note_mcp) -> refuse, no click, no browser ----------
STUB="$(mktemp -d)"
mkdir -p "$STUB/note_mcp/api"
: > "$STUB/note_mcp/__init__.py"
: > "$STUB/note_mcp/api/__init__.py"
cat > "$STUB/note_mcp/models.py" << 'PYEOF'
class Session:
    def __init__(self, cookies, user_id, username, created_at):
        self.cookies = cookies
        self.user_id = user_id
        self.username = username
PYEOF
cat > "$STUB/note_mcp/api/client.py" << 'PYEOF'
class _StubClient:
    """UNCONFIRMED-state fixture (PROP-22a case d): eyecatch is None and the body has zero <img> tags, so
    lib/note-publish-live.py's gate-3a/3b check MUST refuse before ever importing note_browser_common."""
    def __init__(self, session):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def get(self, path):
        return {"data": {"status": "draft", "eyecatch": None, "note_draft": {"body": "<p>no images here, no price set either</p>"}}}

NoteAPIClient = _StubClient
PYEOF
echo '{}' > "$STUB/dummy-cookies.json"

OUT_D="$(NOTE_LIVE_PUBLISH=1 NOTE_MCP_SRC="$STUB" NOTE_COOKIES_FILE="$STUB/dummy-cookies.json" \
  $PLAIN_PY "$TOOL" --draft-key nUNCONFIRMEDTEST 2>&1)"; RC_D=$?
ok "$([ $RC_D -ne 0 ] && echo 1 || echo 0)" "unconfirmed pre-publish state -> non-zero exit (rc=$RC_D)"
ok "$(echo "$OUT_D" | grep -qi 'eyecatch' && echo 1 || echo 0)" "unconfirmed pre-publish state -> stderr names the exact missing piece (eyecatch): $OUT_D"
ok "$(echo "$OUT_D" | grep -qi 'no browser opened\|no click attempted' && echo 1 || echo 0)" "unconfirmed pre-publish state -> explicitly reports no click/browser attempted: $OUT_D"
ok "$(! echo "$OUT_D" | grep -qi 'cloakbrowser\|ModuleNotFoundError.*cloakbrowser\|Traceback' && echo 1 || echo 0)" "unconfirmed pre-publish state -> zero browser action (never imported note_browser_common): $OUT_D"
rm -rf "$STUB"

[ $fails -eq 0 ] && { echo "PASS -- PROP-22a wiring/fail-closed gates all confirmed, zero browser action on any refusal path"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
