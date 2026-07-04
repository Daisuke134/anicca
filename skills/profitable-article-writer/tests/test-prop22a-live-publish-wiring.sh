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
# also confirm no file ANYWHERE in the skill's own tree IMPORTS/SOURCES/EXECs note-publish-live.py.
# FIND-001 fix (Sprint-3 contract review): the prior version of this check enumerated a manually-curated
# CALL_GRAPH_FILES list (lib/note_publish.sh, gates/v0.sh, gates/v05.sh, identity/*) which silently OMITTED
# gates/publish-gate.sh -- the actual Mode-B publish gate run.sh invokes directly, and the single most
# safety-relevant file to guard here. A curated list can always omit a future file the same way. This is
# now a STRUCTURAL, WHOLE-TREE scan (every .sh/.py file under the skill root, excluding tests/ -- which
# legitimately reference the tool by name as the file-under-test) instead of a curated list, so
# gates/publish-gate.sh, run.sh, and any file added to this skill in the future are all automatically
# covered. The match itself stays an INVOCATION-SHAPE grep (source/import/exec/subprocess/direct-python-or-
# bash-call preceding the filename on the same line) -- NOT a bare filename substring -- because several
# sibling lib/*.py files legitimately MENTION "lib/note-publish-live.py" in their own doc-comments/
# docstrings (note_browser_common.py explaining the shared select_paid_price() helper, note-verify-live.py
# explaining it is a separate process, note-set-single-price.py explaining the shared selection sequence);
# those are prose, not a call-graph edge, and must not false-positive this check.
INVOKE_RE='\bimport[[:space:]]+note[-_]publish[-_]live\b'
INVOKE_RE="$INVOKE_RE"'|\bfrom[[:space:]]+note[-_]publish[-_]live[[:space:]]+import\b'
INVOKE_RE="$INVOKE_RE"'|\bimportlib\.import_module\([^)]*note[-_]publish[-_]live'
INVOKE_RE="$INVOKE_RE"'|\bspec_from_file_location\([^)]*note-publish-live'
INVOKE_RE="$INVOKE_RE"'|\bsubprocess\.[A-Za-z_]+\([^)]*note-publish-live'
INVOKE_RE="$INVOKE_RE"'|\bos\.(system|popen)\([^)]*note-publish-live'
INVOKE_RE="$INVOKE_RE"'|\bPopen\([^)]*note-publish-live'
INVOKE_RE="$INVOKE_RE"'|\bsource[[:space:]]+[^#]*note-publish-live'
INVOKE_RE="$INVOKE_RE"'|(^|[[:space:]])\.[[:space:]]+[^#]*note-publish-live'
INVOKE_RE="$INVOKE_RE"'|\b(python3?|bash|sh)[[:space:]]+[^#]*note-publish-live\.py'
ALL_SRC_FILES="$(find "$SKILL" -type f \( -name '*.sh' -o -name '*.py' \) ! -path '*/tests/*' 2>/dev/null | sort)"
INVOKING_FILES="$(printf '%s\n' "$ALL_SRC_FILES" | xargs grep -lE "$INVOKE_RE" 2>/dev/null | grep -v '/lib/note-publish-live\.py$' | sort)"
ok "$([ -z "$INVOKING_FILES" ] && echo 1 || echo 0)" "whole-tree structural scan (excluding tests/): no .sh/.py file anywhere under $SKILL other than lib/note-publish-live.py itself has an invocation-shaped reference to it (found: $(echo "$INVOKING_FILES" | tr '\n' ' '))"
# sanity: the scan itself must actually be exercised (not silently vacuous) -- confirm it correctly flags a
# deliberately-injected invocation-shaped line as a control, then clean it up.
CANARY="$(mktemp "$SKILL/lib/.canary-XXXXXX.sh")"
printf '#!/usr/bin/env bash\npython3 "$SKILL/lib/note-publish-live.py" --draft-key test\n' > "$CANARY"
CANARY_HIT="$(grep -lE "$INVOKE_RE" "$CANARY" 2>/dev/null)"
ok "$([ -n "$CANARY_HIT" ] && echo 1 || echo 0)" "sanity: the invocation-shape regex genuinely detects a deliberately-injected 'python3 .../note-publish-live.py' line (proves the scan is not vacuously passing)"
rm -f "$CANARY"

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

# ---------- (e) NOTE_LIVE_PUBLISH=1 + eyecatch PRESENT but ZERO <img> tags -> refuse citing the MISSING
# VISUALS piece specifically, not eyecatch [FIND-002 fix, Sprint-3 contract review]. Case (d) above zeroes
# BOTH eyecatch AND img_count together, so the eyecatch check (gate 3a) always short-circuits first and the
# img_count<1 refusal branch (gate 3b, lib/note-publish-live.py lines ~120-126) was never independently
# exercised by any test. This fixture isolates it: eyecatch is set, body has zero <img> tags.
STUB2="$(mktemp -d)"
mkdir -p "$STUB2/note_mcp/api"
: > "$STUB2/note_mcp/__init__.py"
: > "$STUB2/note_mcp/api/__init__.py"
cat > "$STUB2/note_mcp/models.py" << 'PYEOF'
class Session:
    def __init__(self, cookies, user_id, username, created_at):
        self.cookies = cookies
        self.user_id = user_id
        self.username = username
PYEOF
cat > "$STUB2/note_mcp/api/client.py" << 'PYEOF'
class _StubClient:
    """eyecatch-PRESENT / zero-<img>-tags fixture (PROP-22a case e, FIND-002 fix): proves the img_count<1
    refusal branch (lib/note-publish-live.py's gate-3b check) is independently exercised -- distinct from
    case (d), where eyecatch=None makes the eyecatch check (gate-3a) short-circuit first."""
    def __init__(self, session):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def get(self, path):
        return {"data": {"status": "draft", "eyecatch": "https://assets.st-note.com/fake-eyecatch.png",
                          "note_draft": {"body": "<p>no images at all in this body, price set separately</p>"}}}

NoteAPIClient = _StubClient
PYEOF
echo '{}' > "$STUB2/dummy-cookies.json"

OUT_E="$(NOTE_LIVE_PUBLISH=1 NOTE_MCP_SRC="$STUB2" NOTE_COOKIES_FILE="$STUB2/dummy-cookies.json" \
  $PLAIN_PY "$TOOL" --draft-key nZEROIMGTEST 2>&1)"; RC_E=$?
ok "$([ $RC_E -ne 0 ] && echo 1 || echo 0)" "eyecatch present + zero <img> tags -> non-zero exit (rc=$RC_E)"
ok "$(echo "$OUT_E" | grep -qi 'ZERO <img> tags' && echo 1 || echo 0)" "eyecatch present + zero <img> tags -> stderr names the MISSING VISUALS piece specifically (img_count gate): $OUT_E"
ok "$(! echo "$OUT_E" | grep -qi 'eyecatch NOT set' && echo 1 || echo 0)" "eyecatch present + zero <img> tags -> refusal message does NOT claim eyecatch is missing (proves gate-3a did not short-circuit): $OUT_E"
ok "$(echo "$OUT_E" | grep -qi 'no browser opened\|no click attempted' && echo 1 || echo 0)" "eyecatch present + zero <img> tags -> explicitly reports no click/browser attempted: $OUT_E"
ok "$(! echo "$OUT_E" | grep -qi 'cloakbrowser\|ModuleNotFoundError.*cloakbrowser\|Traceback' && echo 1 || echo 0)" "eyecatch present + zero <img> tags -> zero browser action (never imported note_browser_common): $OUT_E"
rm -rf "$STUB2"

[ $fails -eq 0 ] && { echo "PASS -- PROP-22a wiring/fail-closed gates all confirmed, zero browser action on any refusal path"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
