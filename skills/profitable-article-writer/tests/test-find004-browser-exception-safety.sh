#!/usr/bin/env bash
# VSDD oracle -- FIND-004 fix (Sprint-3 contract review), UPDATED Sprint 4: a realistic browser-session
# exception (launch flake, malformed-cookie error, navigation timeout, mid-session DOM error) must NEVER
# surface as a raw traceback and must NEVER leak an already-created browser context -- it must always
# resolve to a clean refusal via the SAME refusal-reporting shape, with the browser context closed.
#
# Sprint-4 update: the try/except/finally exception-safety wrapper now lives in the SHARED
# lib/note_browser_common.confirm_and_publish() (PROP-24 moved it out of note-publish-live.py's own main()
# so run.sh's Mode-B branch can reuse it too). Cases 2/3 below therefore now call confirm_and_publish
# DIRECTLY (unit-level), monkeypatching its module-level open_editor_ready/select_paid_price helpers AFTER a
# normal import -- same technique as test-prop22c's Sprint-4 update.
#
# 3 hermetic (T1, no real cloakbrowser/browser/network) sub-cases:
#   1. note_browser_common.open_editor_ready() itself: launch_context() succeeds (a real context object is
#      created) but ctx.add_cookies() then raises -- proves the LEAK-PREVENTION fix directly at its source
#      (the partially-created context is closed, via a counter/mock, BEFORE the exception re-raises).
#   2. note_browser_common.confirm_and_publish(): open_editor_ready() itself raises (simulating any
#      browser-session launch failure) -- proves confirm_and_publish's own try/except/finally catches it as
#      a clean refusal (ok=False), not a raw traceback.
#   3. note_browser_common.confirm_and_publish(): open_editor_ready() succeeds (returns a real ctx handle)
#      but select_paid_price() then raises mid-session -- proves the finally block still closes the ctx it
#      DOES hold a handle to (via a counter/mock), and still reports a clean refusal, not a raw traceback.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
LIB="$SKILL/lib"
BROWSER_COMMON="$SKILL/lib/note_browser_common.py"
PY="python3"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- case 1: note_browser_common.open_editor_ready()'s OWN leak-prevention (a real add_cookies
# failure on an already-launched context) ----------
OUT1="$("$PY" - "$BROWSER_COMMON" << 'PYEOF' 2>&1
import sys, types, importlib.util

browser_common_path = sys.argv[1]

close_calls = {"n": 0}

class _FakeCtx:
    def add_cookies(self, cookies):
        raise RuntimeError("simulated add_cookies failure (malformed cookie / launch flake)")
    def close(self):
        close_calls["n"] += 1

fake_cloakbrowser = types.ModuleType("cloakbrowser")
fake_cloakbrowser.launch_context = lambda **kw: _FakeCtx()
sys.modules["cloakbrowser"] = fake_cloakbrowser

spec = importlib.util.spec_from_file_location("note_browser_common_under_test", browser_common_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

raised = False
msg = ""
try:
    mod.open_editor_ready([], "nXXXXFIND004", {"width": 1280, "height": 1400})
except RuntimeError as e:
    raised = True
    msg = str(e)

print(f"__RAISED__={raised}")
print(f"__MSG__={msg}")
print(f"__CLOSE_CALLS__={close_calls['n']}")
PYEOF
)"
echo "  case 1 output: $OUT1"
ok "$(echo "$OUT1" | grep -q '__RAISED__=True' && echo 1 || echo 0)" "case 1: open_editor_ready() re-raises the underlying exception (does not swallow it silently)"
ok "$(echo "$OUT1" | grep -q '__MSG__=simulated add_cookies failure' && echo 1 || echo 0)" "case 1: the re-raised exception carries the ORIGINAL message (not replaced/obscured)"
ok "$(echo "$OUT1" | grep -q '__CLOSE_CALLS__=1' && echo 1 || echo 0)" "case 1: the partially-created context's close() was called EXACTLY ONCE before the exception propagated (no leak, no double-close)"

# ---------- shared: a stubbed note_mcp fixture confirming gates (a)/(b) so execution reaches the browser
# session lifecycle inside confirm_and_publish (cases 2 and 3) ----------
STUB="$(mktemp -d)"
mkdir -p "$STUB/note_mcp/api"
: > "$STUB/note_mcp/__init__.py"
: > "$STUB/note_mcp/api/__init__.py"
cat > "$STUB/note_mcp/models.py" << 'PYEOF'
class Session:
    def __init__(self, cookies, user_id, username, created_at):
        self.cookies = cookies
PYEOF
cat > "$STUB/note_mcp/api/client.py" << 'PYEOF'
class _StubClient:
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

# ---------- case 2: confirm_and_publish's open_editor_ready() call itself raises (browser launch never even
# produces a ctx handle) -- proves confirm_and_publish's own try/except/finally converts this to a clean
# refusal (ok=False) ----------
OUT2="$("$PY" - "$LIB" "$STUB" << 'PYEOF' 2>&1
import sys

lib_dir, stub_dir = sys.argv[1], sys.argv[2]
sys.path.insert(0, lib_dir)
import note_browser_common

def _open_editor_ready(cookies, note_key, viewport, timeout_s=20):
    raise RuntimeError("simulated cloakbrowser launch failure")

note_browser_common.open_editor_ready = _open_editor_ready
note_browser_common.select_paid_price = lambda pg, price: {"row_found": True, "paid_checked": True, "price_filled": str(price)}

result = note_browser_common.confirm_and_publish(
    "nLAUNCHFAILTEST", price=500, cookies_file=stub_dir + "/dummy-cookies.json",
    note_mcp_src=stub_dir, user_id="14651590", username="anicca123", work_dir="/tmp",
)
print(f"__OK__={result['ok']}")
print(f"__REASON__={result['reason']}")
PYEOF
)"
echo "  case 2 output: $OUT2"
ok "$(echo "$OUT2" | grep -q '__OK__=False' && echo 1 || echo 0)" "case 2: a browser-launch failure -> ok=False (clean refusal, not a crash)"
ok "$(echo "$OUT2" | grep -qi 'unexpected browser-session error.*simulated cloakbrowser launch failure' && echo 1 || echo 0)" "case 2: a clean refusal reason naming the exception is returned"
ok "$(! echo "$OUT2" | grep -qi 'Traceback (most recent call last)' && echo 1 || echo 0)" "case 2: NO raw traceback reaches stdout/stderr (the exception is caught, not left to propagate to the interpreter)"

# ---------- case 3: confirm_and_publish's open_editor_ready() succeeds (real ctx handle obtained) but
# select_paid_price() then raises mid-session -- proves the finally-block still closes the ctx it DOES hold
# ----------
OUT3="$("$PY" - "$LIB" "$STUB" << 'PYEOF' 2>&1
import sys

lib_dir, stub_dir = sys.argv[1], sys.argv[2]
sys.path.insert(0, lib_dir)
import note_browser_common

close_calls = {"n": 0}

class _FakeCtx:
    def close(self):
        close_calls["n"] += 1

class _FakePage:
    def evaluate(self, *a, **k):
        return ""

note_browser_common.open_editor_ready = lambda cookies, note_key, viewport, timeout_s=20: (_FakeCtx(), _FakePage())

def _select_paid_price(pg, price):
    raise RuntimeError("simulated mid-session DOM error (note.com layout changed unexpectedly)")

note_browser_common.select_paid_price = _select_paid_price

result = note_browser_common.confirm_and_publish(
    "nMIDSESSIONFAILTEST", price=500, cookies_file=stub_dir + "/dummy-cookies.json",
    note_mcp_src=stub_dir, user_id="14651590", username="anicca123", work_dir="/tmp",
)
print(f"__OK__={result['ok']}")
print(f"__REASON__={result['reason']}")
print(f"__CLOSE_CALLS__={close_calls['n']}")
PYEOF
)"
echo "  case 3 output: $OUT3"
ok "$(echo "$OUT3" | grep -q '__OK__=False' && echo 1 || echo 0)" "case 3: a mid-session DOM error -> ok=False (clean refusal, not a crash)"
ok "$(echo "$OUT3" | grep -qi 'unexpected browser-session error.*simulated mid-session DOM error' && echo 1 || echo 0)" "case 3: a clean refusal reason naming the exception is returned"
ok "$(! echo "$OUT3" | grep -qi 'Traceback (most recent call last)' && echo 1 || echo 0)" "case 3: NO raw traceback reaches stdout/stderr"
ok "$(echo "$OUT3" | grep -q '__CLOSE_CALLS__=1' && echo 1 || echo 0)" "case 3: the browser context confirm_and_publish DID obtain a handle to was closed EXACTLY ONCE via the finally block (no leak)"

rm -rf "$STUB"

[ $fails -eq 0 ] && { echo "PASS -- FIND-004 (Sprint-4 update): browser-session exceptions never surface as raw tracebacks, never leak a context, and always resolve to a clean refusal, now proven at the shared confirm_and_publish unit"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
