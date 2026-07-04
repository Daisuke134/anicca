#!/usr/bin/env bash
# VSDD oracle -- FIND-003 fix (Sprint-3 contract review): lib/note-publish-live.py's 3 price/type-mismatch
# refusal branches (row_found=False / paid_checked=False / price_filled mismatch, main() gate 3c) each get
# DEDICATED, independent coverage -- one test per branch, each with exactly ONE precondition false and the
# others true, asserting a refusal that names THAT specific missing piece. Before this file, the ONLY test
# reaching this code was the live test-prop22b-live-publish-real-click.sh, which by design only exercises
# the ALL-CONFIRMED success path -- the price/type mismatch refusal, arguably the single most safety-
# critical branch (a price mismatch publishing at the wrong price is exactly what REQ-21 exists to prevent),
# was never actually verified to refuse correctly.
#
# Method: this is a T1 hermetic test. Gate 3a/3b (eyecatch/visuals) is satisfied via the same stubbed
# note_mcp fixture technique test-prop22a already uses. Gate 3c (the browser-driven price/type confirm) is
# exercised WITHOUT a real browser: Python's import machinery checks sys.modules BEFORE ever touching
# sys.path, so pre-populating sys.modules["note_browser_common"] with a fake module (before
# note-publish-live.py's own module is exec'd) intercepts its `from note_browser_common import ...` line
# regardless of the script's own `sys.path.insert(0, ...)` call -- no cloakbrowser/browser/network is
# touched at all.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
TOOL="$SKILL/lib/note-publish-live.py"
PY="python3"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

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
    """CONFIRMED pre-publish state (eyecatch set, >=1 <img> tag) so gate 3a/3b always PASS here -- this
    fixture exists only to let execution reach gate 3c (price/type), the thing FIND-003's 3 sub-tests below
    each exercise in isolation."""
    def __init__(self, session):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def get(self, path):
        return {"data": {"status": "draft", "eyecatch": "https://assets.st-note.com/fake.png",
                          "note_draft": {"body": "<p><img src=x.png></p>"}}}

NoteAPIClient = _StubClient
PYEOF
echo '{}' > "$STUB/dummy-cookies.json"

# run_case: injects a fake note_browser_common (via sys.modules, intercepted before sys.path is ever
# consulted) whose select_paid_price() returns exactly the caller-specified {row_found, paid_checked,
# price_filled}, then execs the REAL note-publish-live.py module and calls its real main().
run_case() {
  local row="$1" paid="$2" price_filled_json="$3" draft_key="$4"
  NOTE_LIVE_PUBLISH=1 NOTE_MCP_SRC="$STUB" NOTE_COOKIES_FILE="$STUB/dummy-cookies.json" NOTE_PRICE=500 \
  "$PY" - "$draft_key" "$row" "$paid" "$price_filled_json" "$TOOL" << 'PYEOF' 2>&1
import sys, types, importlib.util

draft_key, row_s, paid_s, price_s, tool_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
row_found = row_s == "true"
paid_checked = paid_s == "true"
price_filled = None if price_s == "__NONE__" else price_s

fake = types.ModuleType("note_browser_common")
fake.load_note_cookies = lambda f: [{"name": "x", "value": "y", "domain": ".note.com", "path": "/"}]

class _FakeCtx:
    def close(self):
        pass

class _FakePage:
    def evaluate(self, *a, **k):
        return ""

def _open_editor_ready(cookies, note_key, viewport, timeout_s=20):
    return _FakeCtx(), _FakePage()

def _select_paid_price(pg, price):
    return {"row_found": row_found, "paid_checked": paid_checked, "price_filled": price_filled}

fake.open_editor_ready = _open_editor_ready
fake.select_paid_price = _select_paid_price
sys.modules["note_browser_common"] = fake

spec = importlib.util.spec_from_file_location("note_publish_live_under_test_find003", tool_path)
mod = importlib.util.module_from_spec(spec)
sys.argv = ["note-publish-live.py", "--draft-key", draft_key]
spec.loader.exec_module(mod)
rc = mod.main()
print(f"__RC__={rc}")
PYEOF
}

# ---------- branch 1: row_found=False (the 有料 radio row itself could not be located) ----------
OUT1="$(run_case false false __NONE__ nROWFOUNDTEST)"
RC1="$(echo "$OUT1" | grep -oE '__RC__=[0-9]+' | cut -d= -f2)"
ok "$([ "${RC1:-0}" != "0" ] && echo 1 || echo 0)" "row_found=False -> non-zero exit (rc=$RC1)"
ok "$(echo "$OUT1" | grep -qi 'could not locate the 有料 radio row' && echo 1 || echo 0)" "row_found=False -> stderr names THIS specific missing piece (有料 radio row not located): $OUT1"
ok "$(! echo "$OUT1" | grep -qi 'Traceback' && echo 1 || echo 0)" "row_found=False -> no raw traceback"

# ---------- branch 2: row_found=True, paid_checked=False (row found/clicked but readback never confirmed 有料) ----------
OUT2="$(run_case true false __NONE__ nPAIDCHECKEDTEST)"
RC2="$(echo "$OUT2" | grep -oE '__RC__=[0-9]+' | cut -d= -f2)"
ok "$([ "${RC2:-0}" != "0" ] && echo 1 || echo 0)" "paid_checked=False -> non-zero exit (rc=$RC2)"
ok "$(echo "$OUT2" | grep -qi '記事タイプ could not be confirmed as' && echo 1 || echo 0)" "paid_checked=False -> stderr names THIS specific missing piece (記事タイプ not confirmed 有料): $OUT2"
ok "$(! echo "$OUT2" | grep -qi 'could not locate the 有料 radio row' && echo 1 || echo 0)" "paid_checked=False -> refusal message does NOT claim row_found failed (proves the row_found branch did not fire)"
ok "$(! echo "$OUT2" | grep -qi 'Traceback' && echo 1 || echo 0)" "paid_checked=False -> no raw traceback"

# ---------- branch 3: row_found=True, paid_checked=True, price_filled mismatch (999 filled, 500 expected) ----------
OUT3="$(run_case true true 999 nPRICEMISMATCHTEST)"
RC3="$(echo "$OUT3" | grep -oE '__RC__=[0-9]+' | cut -d= -f2)"
ok "$([ "${RC3:-0}" != "0" ] && echo 1 || echo 0)" "price_filled mismatch -> non-zero exit (rc=$RC3)"
ok "$(echo "$OUT3" | grep -q "price confirmed as '999', expected '500'" && echo 1 || echo 0)" "price_filled mismatch -> stderr names THIS specific missing piece (exact filled vs expected price): $OUT3"
ok "$(! echo "$OUT3" | grep -qi '記事タイプ could not be confirmed as\|could not locate the 有料 radio row' && echo 1 || echo 0)" "price_filled mismatch -> refusal message does NOT claim row_found/paid_checked failed (proves only the price branch fired)"
ok "$(! echo "$OUT3" | grep -qi 'Traceback' && echo 1 || echo 0)" "price_filled mismatch -> no raw traceback"

rm -rf "$STUB"

[ $fails -eq 0 ] && { echo "PASS -- FIND-003: all 3 price/type-mismatch refusal branches independently exercised, each naming its own specific missing piece"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
