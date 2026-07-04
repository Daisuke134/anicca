#!/usr/bin/env bash
# VSDD oracle -- FIND-003 fix (Sprint-3 contract review), UPDATED Sprint 4: lib/note-publish-live.py's 3
# price/type-mismatch refusal branches (row_found=False / paid_checked=False / price_filled mismatch) each
# get DEDICATED, independent coverage -- one test per branch, each with exactly ONE precondition false and
# the others true, asserting a refusal that names THAT specific missing piece.
#
# Sprint-4 update: this branching logic now lives in the SHARED lib/note_browser_common.confirm_and_publish()
# (PROP-24 moved it out of note-publish-live.py's own main() so run.sh's Mode-B branch can reuse it too).
# This test therefore now exercises confirm_and_publish DIRECTLY (unit-level), monkeypatching its own
# module-level open_editor_ready/select_paid_price helpers AFTER a normal import -- confirm_and_publish
# looks those names up in its own module's globals at call time, so replacing them on the imported module
# object intercepts every call, with ZERO cloakbrowser/browser/network dependency (note_browser_common.py
# imports cloakbrowser LAZILY, only inside the real open_editor_ready, which is never reached once we've
# replaced it).
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
LIB="$SKILL/lib"
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
    """CONFIRMED pre-publish state (eyecatch set, >=1 <img> tag) so gates (a)/(b) always PASS here -- this
    fixture exists only to let execution reach gate (c) (price/type), the thing FIND-003's 3 sub-tests below
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

# run_case: monkeypatches note_browser_common.open_editor_ready/select_paid_price (module-global
# replacement -- confirm_and_publish resolves these names from its OWN module's globals at call time, so
# this intercepts it without touching cloakbrowser at all), then calls the REAL confirm_and_publish directly.
run_case() {
  local row="$1" paid="$2" price_filled_json="$3" draft_key="$4"
  "$PY" - "$draft_key" "$row" "$paid" "$price_filled_json" "$LIB" "$STUB" << 'PYEOF' 2>&1
import sys

draft_key, row_s, paid_s, price_s, lib_dir, stub_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
row_found = row_s == "true"
paid_checked = paid_s == "true"
price_filled = None if price_s == "__NONE__" else price_s

sys.path.insert(0, lib_dir)
import note_browser_common  # succeeds with ZERO cloakbrowser dependency (lazy import inside the real open_editor_ready)

class _FakeCtx:
    def close(self):
        pass

class _FakePage:
    def evaluate(self, *a, **k):
        return ""

def _fake_open_editor_ready(cookies, note_key, viewport, timeout_s=20):
    return _FakeCtx(), _FakePage()

def _fake_select_paid_price(pg, price):
    return {"row_found": row_found, "paid_checked": paid_checked, "price_filled": price_filled}

# module-global monkeypatch: confirm_and_publish (defined in this SAME module) resolves bare names
# open_editor_ready/select_paid_price from note_browser_common's own globals dict at call time.
note_browser_common.open_editor_ready = _fake_open_editor_ready
note_browser_common.select_paid_price = _fake_select_paid_price

result = note_browser_common.confirm_and_publish(
    draft_key, price=500, cookies_file=stub_dir + "/dummy-cookies.json",
    note_mcp_src=stub_dir, user_id="14651590", username="anicca123", work_dir="/tmp",
)
print(f"__OK__={result['ok']}")
print(f"__REASON__={result['reason']}")
PYEOF
}

# ---------- branch 1: row_found=False (the 有料 radio row itself could not be located) ----------
OUT1="$(run_case false false __NONE__ nROWFOUNDTEST)"
ok "$(echo "$OUT1" | grep -q '__OK__=False' && echo 1 || echo 0)" "row_found=False -> ok=False"
ok "$(echo "$OUT1" | grep -qi 'could not locate the 有料 radio row' && echo 1 || echo 0)" "row_found=False -> reason names THIS specific missing piece (有料 radio row not located): $OUT1"
ok "$(! echo "$OUT1" | grep -qi 'Traceback' && echo 1 || echo 0)" "row_found=False -> no raw traceback"

# ---------- branch 2: row_found=True, paid_checked=False (row found/clicked but readback never confirmed 有料) ----------
OUT2="$(run_case true false __NONE__ nPAIDCHECKEDTEST)"
ok "$(echo "$OUT2" | grep -q '__OK__=False' && echo 1 || echo 0)" "paid_checked=False -> ok=False"
ok "$(echo "$OUT2" | grep -qi '記事タイプ could not be confirmed as' && echo 1 || echo 0)" "paid_checked=False -> reason names THIS specific missing piece (記事タイプ not confirmed 有料): $OUT2"
ok "$(! echo "$OUT2" | grep -qi 'could not locate the 有料 radio row' && echo 1 || echo 0)" "paid_checked=False -> reason does NOT claim row_found failed (proves the row_found branch did not fire)"
ok "$(! echo "$OUT2" | grep -qi 'Traceback' && echo 1 || echo 0)" "paid_checked=False -> no raw traceback"

# ---------- branch 3: row_found=True, paid_checked=True, price_filled mismatch (999 filled, 500 expected) ----------
OUT3="$(run_case true true 999 nPRICEMISMATCHTEST)"
ok "$(echo "$OUT3" | grep -q '__OK__=False' && echo 1 || echo 0)" "price_filled mismatch -> ok=False"
ok "$(echo "$OUT3" | grep -q "price confirmed as '999', expected '500'" && echo 1 || echo 0)" "price_filled mismatch -> reason names THIS specific missing piece (exact filled vs expected price): $OUT3"
ok "$(! echo "$OUT3" | grep -qi '記事タイプ could not be confirmed as\|could not locate the 有料 radio row' && echo 1 || echo 0)" "price_filled mismatch -> reason does NOT claim row_found/paid_checked failed (proves only the price branch fired)"
ok "$(! echo "$OUT3" | grep -qi 'Traceback' && echo 1 || echo 0)" "price_filled mismatch -> no raw traceback"

rm -rf "$STUB"

[ $fails -eq 0 ] && { echo "PASS -- FIND-003 (Sprint-4 update): all 3 price/type-mismatch refusal branches, now in the SHARED confirm_and_publish, independently exercised, each naming its own specific missing piece"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
