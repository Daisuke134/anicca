#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AUDITOR="$ROOT/skills/earn/gig/auditor.sh"

grep -F 'scripts/gig_slo.py' "$AUDITOR" >/dev/null
grep -F -- '--repair-database "$G/gig-control.sqlite3"' "$AUDITOR" >/dev/null
grep -F 'printf '\''%s\n'\'' "$slo_row" >> "$AUDIT"' "$AUDITOR" >/dev/null
grep -F 'src/gig/healing/controller.py' "$AUDITOR" >/dev/null
grep -F 'scripts/work_event_projector.py' "$AUDITOR" >/dev/null
grep -F 'telegram_report.py" work-events' "$AUDITOR" >/dev/null
# The scheduler-silence incident already reached the repair queue; it must also
# reach the person who would otherwise wait ten hours to notice.
grep -F 'telegram_report.py" pass-silence' "$AUDITOR" >/dev/null
grep -F -- '--gig-dir "$G" \' "$AUDITOR" >/dev/null
grep -F 'hermes-canary-24h-audit.json' "$AUDITOR" >/dev/null
grep -F 'hermes_canary.py audit' "$AUDITOR" >/dev/null
grep -F 'telegram_report.py" hermes-audit' "$AUDITOR" >/dev/null
test "$(grep -n 'hermes_canary.py audit' "$AUDITOR" | head -1 | cut -d: -f1)" -lt \
  "$(grep -n 'scripts/gig_slo.py' "$AUDITOR" | head -1 | cut -d: -f1)"

# Exercise the durable Hermes block with fixture executables only. The canary exits
# 1 for RED on purpose: stdout JSON, not rc alone, is the judge.
START_LINE=$(grep -n '^HERMES_AUDIT_STATE=' "$AUDITOR" | head -1 | cut -d: -f1)
END_LINE=$(grep -n '^# ─── reality-verifier' "$AUDITOR" | head -1 | cut -d: -f1)
SNIPPET=$(sed -n "${START_LINE},$((END_LINE - 1))p" "$AUDITOR")
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
G="$TMP/gig"; mkdir -p "$G" "$TMP/scripts"
mkdir -p "$TMP/.local/bin"
cat > "$TMP/.local/bin/hermes" <<'SH'
#!/bin/sh
touch "$G/hermes-resolved"
SH
chmod +x "$TMP/.local/bin/hermes"
cat > "$TMP/scripts/hermes_canary.py" <<'PY'
#!/usr/bin/env python3
import json, subprocess, sys
import os
subprocess.run(["hermes"], check=True, capture_output=True, text=True)
open(os.path.join(os.environ["G"], "canary-called"), "w").write("called")
print(json.dumps({
    "version": 1, "since": 1786365299, "until": 1786451699,
    "now": 1786369000, "window_complete": False, "verdict": "RED",
    "lanes": {}, "invariants": {}, "applications": {}, "telegram": {}, "storefront": {},
}))
raise SystemExit(1)
PY
cat > "$TMP/scripts/telegram_report.py" <<'PY'
#!/usr/bin/env python3
import os
open(os.path.join(os.environ["G"], "telegram.calls"), "a").write("telegram-called\n")
PY
chmod +x "$TMP/scripts/hermes_canary.py" "$TMP/scripts/telegram_report.py"
cat > "$G/hermes-canary-24h-audit.json" <<'JSON'
{"version":1,"audit_id":"1786365299-1786451699","since":1786365299,"until":1786451699,"phase":"active","verdict":"PENDING","raw_verdict":"PENDING","last_checked_at":null,"terminal_at":null,"result":{}}
JSON
PYTHON=$(command -v python3)
OUT=$(PATH="/usr/bin:/bin" G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry")
python3 - "$G/hermes-canary-24h-audit.json" <<'PY'
import json,sys
state=json.load(open(sys.argv[1]))
assert state["phase"] == "active" and state["verdict"] == "PENDING" and state["raw_verdict"] == "RED"
assert state["result"]["verdict"] == "RED"
PY
test -e "$G/hermes-resolved" || { echo 'FAIL: launchd-like PATH did not resolve hermes'; exit 1; }
test "$(stat -f '%Lp' "$G/hermes-canary-24h-audit.json" 2>/dev/null || stat -c '%a' "$G/hermes-canary-24h-audit.json")" = 600
grep -q telegram-called "$G/telegram.calls"
echo 'PASS: launchd-like PATH resolves hermes and rc=1 RED JSON is persisted as effective PENDING with 0600 state'

# A complete window latches terminal from the real update path.
cat > "$TMP/scripts/hermes_canary.py" <<'PY'
#!/usr/bin/env python3
import json, os
open(os.path.join(os.environ["G"], "canary-called"), "w").write("called")
print(json.dumps({"version":1,"since":1786365299,"until":1786451699,"window_complete":True,"verdict":"RED"}))
raise SystemExit(1)
PY
chmod +x "$TMP/scripts/hermes_canary.py"
rm -f "$G/telegram.calls" "$G/canary-called"
OUT=$(G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry")
python3 - "$G/hermes-canary-24h-audit.json" <<'PY'
import json,sys
state=json.load(open(sys.argv[1])); assert state["phase"] == "terminal" and state["verdict"] == "RED" and state["terminal_at"]
PY
test -e "$G/canary-called" || { echo 'FAIL: complete window did not execute canary'; exit 1; }
echo 'PASS: window_complete=true latches terminal verdict'

# Terminal is immutable and is only reconciled through the report command.
rm -f "$G/telegram.calls" "$G/canary-called"
OUT=$(G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry")
test ! -e "$G/canary-called" || { echo 'FAIL: terminal state reran audit'; exit 1; }
test -e "$G/telegram.calls" || { echo 'FAIL: terminal state skipped Telegram reconciliation'; exit 1; }
echo 'PASS: terminal state latches without rerunning canary'

# A malformed canary response preserves the terminal state and still returns to caller.
cat > "$TMP/scripts/hermes_canary.py" <<'PY'
#!/usr/bin/env python3
print("not-json")
PY
chmod +x "$TMP/scripts/hermes_canary.py"
python3 - "$G/hermes-canary-24h-audit.json" <<'PY'
import json,sys
path=sys.argv[1]; state=json.load(open(path)); state.update(phase="active",verdict="PENDING",raw_verdict="PENDING",terminal_at=None); json.dump(state,open(path,"w"))
PY
python3 - "$G/hermes-canary-24h-audit.json" "$TMP/before" <<'PY'
import shutil,sys
shutil.copyfile(sys.argv[1],sys.argv[2])
PY
echo 'CONTINUED' > "$TMP/continued"
OUT=$(G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry"; echo CONTINUED)
echo "$OUT" | grep -q CONTINUED
cmp "$G/hermes-canary-24h-audit.json" "$TMP/before"
grep -q 'canary rc=0 invalid stdout' "$G/.hermes-canary-audit.err.log"
echo 'PASS: malformed canary output preserves last good state and auditor continues'

# Empty stdout is diagnosable without persisting the failed query or its stderr.
cat > "$TMP/scripts/hermes_canary.py" <<'PY'
#!/usr/bin/env python3
PY
chmod +x "$TMP/scripts/hermes_canary.py"
python3 - "$G/hermes-canary-24h-audit.json" "$TMP/before-empty" <<'PY'
import shutil,sys
shutil.copyfile(sys.argv[1],sys.argv[2])
PY
OUT=$(G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry")
cmp "$G/hermes-canary-24h-audit.json" "$TMP/before-empty"
grep -q 'canary rc=0 empty stdout' "$G/.hermes-canary-audit.err.log"
echo 'PASS: empty canary stdout preserves state and records a safe diagnostic'

# rc>=2 is a query failure even if stdout happens to look like JSON.
cat > "$TMP/scripts/hermes_canary.py" <<'PY'
#!/usr/bin/env python3
import json
print(json.dumps({"version":1,"since":1786365299,"until":1786451699,"window_complete":False,"verdict":"PENDING"}))
raise SystemExit(2)
PY
chmod +x "$TMP/scripts/hermes_canary.py"
python3 - "$G/hermes-canary-24h-audit.json" "$TMP/before-rc" <<'PY'
import shutil,sys
shutil.copyfile(sys.argv[1],sys.argv[2])
PY
OUT=$(G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry")
cmp "$G/hermes-canary-24h-audit.json" "$TMP/before-rc"
echo 'PASS: rc>=2 preserves last good state despite JSON stdout'

# Epochs are integer identity fields; fractional state cannot be silently truncated.
python3 - "$G/hermes-canary-24h-audit.json" "$TMP/before-float" <<'PY'
import json,shutil,sys
path=sys.argv[1]; state=json.load(open(path)); state["since"]=1786365299.5; json.dump(state,open(path,"w")); shutil.copyfile(path,sys.argv[2])
PY
rm -f "$G/canary-called"
OUT=$(G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry")
test ! -e "$G/canary-called" || { echo 'FAIL: fractional state epoch ran canary'; exit 1; }
cmp "$G/hermes-canary-24h-audit.json" "$TMP/before-float"
echo 'PASS: fractional state epoch is rejected without truncation'

# Window identity is generic (a future 7-day audit does not require code edits).
cat > "$TMP/scripts/hermes_canary.py" <<'PY'
#!/usr/bin/env python3
import json,sys
since=int(float(sys.argv[sys.argv.index("--since")+1])); until=int(float(sys.argv[sys.argv.index("--until")+1]))
print(json.dumps({"version":1,"since":since,"until":until,"window_complete":False,"verdict":"PENDING"}))
PY
chmod +x "$TMP/scripts/hermes_canary.py"
python3 - "$G/hermes-canary-24h-audit.json" <<'PY'
import json,sys
path=sys.argv[1]; state=json.load(open(path)); state.update(audit_id="10-20",since=10,until=20,phase="active",verdict="PENDING"); json.dump(state,open(path,"w"))
PY
OUT=$(G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry")
python3 - "$G/hermes-canary-24h-audit.json" <<'PY'
import json,sys
state=json.load(open(sys.argv[1])); assert state["audit_id"] == "10-20" and state["result"]["since"] == 10
PY
echo 'PASS: generic audit identity is accepted without truncation'

# Cross-state combinations are rejected before the canary, so terminal/PENDING
# cannot become a permanently silent latch.
python3 - "$G/hermes-canary-24h-audit.json" "$TMP/before-invalid" <<'PY'
import json,shutil,sys
path=sys.argv[1]; state=json.load(open(path)); state.update(phase="terminal",verdict="PENDING"); json.dump(state,open(path,"w")); shutil.copyfile(path,sys.argv[2])
PY
rm -f "$G/canary-called"
OUT=$(G="$G" HOME="$TMP" PY="$PYTHON" SCRIPTS="$TMP/scripts" bash -c "$SNIPPET" "$TMP/entry")
test ! -e "$G/canary-called" || { echo 'FAIL: invalid terminal/PENDING state ran canary'; exit 1; }
cmp "$G/hermes-canary-24h-audit.json" "$TMP/before-invalid"
echo 'PASS: invalid terminal/PENDING state is preserved and skipped'
