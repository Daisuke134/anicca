#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/weekly-audit-path.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/skill/scripts"

cat >"$TMP/skill/scripts/article_weekly_audit.py" <<'PY'
import json
import shutil
import sys

print(json.dumps({
    "python": sys.executable,
    "openclaw": shutil.which("openclaw"),
}))
PY

output="$(
  env -i \
    HOME="$HOME" \
    PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
    ARTICLE_SKILL_DIR="$TMP/skill" \
    /bin/bash "$ROOT/scripts/audit-7day.sh"
)"

/usr/bin/python3 - "$output" <<'PY'
import json
import sys

value = json.loads(sys.argv[1])
assert value["openclaw"], value
assert value["python"] != "/usr/bin/python3", value
print("PASS: weekly audit wrapper restores its launchd runtime PATH")
PY
