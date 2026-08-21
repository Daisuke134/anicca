#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DISPATCH="$ROOT/skills/writer-agent/scripts/platform-dispatch.sh"
TMP="$(mktemp -d /tmp/article-platform-dispatch.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
MANIFEST="$TMP/jobs.jsonl"
RESULTS="$TMP/results.jsonl"
HELPER="$TMP/helper.sh"

cat >"$HELPER" <<'HELPER'
#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  fail) printf '%s' "$2" >>"$CALLS"; exit 9 ;;
  record) printf '%s' "$2" >>"$CALLS" ;;
  wait) sleep 1; printf '%s' "$2" >>"$CALLS" ;;
esac
HELPER
chmod +x "$HELPER"
: >"$TMP/cover.png"

python3 - "$MANIFEST" "$HELPER" "$TMP/calls" "$TMP/cover.png" <<'PY'
import json, sys
path, helper, calls, cover = sys.argv[1:]
jobs = [
    ("note", "ja", ["bash", helper, "fail", "note"]),
    ("x", "ja", ["bash", helper, "record", "x-ja"]),
    ("x", "en", ["bash", helper, "record", "Coinbase moved $44M; only $188K was real"]),
    ("zenn", "ja", ["bash", helper, "wait", "zenn"]),
    ("substack-ja", "ja", ["bash", helper, "record", "ss-ja"]),
    ("substack-en", "en", ["bash", helper, "record", "ss-en"]),
]
with open(path, "w", encoding="utf-8") as out:
    for platform, lang, argv in jobs:
        env = {"CALLS": calls}
        if platform == "x": env["X_COVER"] = cover
        out.write(json.dumps({"platform": platform, "lang": lang, "argv": argv,
                              "env": env}) + "\n")
PY

set +e
bash "$DISPATCH" --manifest "$MANIFEST" --results "$RESULTS"
rc=$?
set -e
[ "$rc" -ne 0 ]
[ "$(wc -l <"$RESULTS" | tr -d ' ')" -eq 6 ]
[ "$(jq -r 'select(.status == "failed") | .platform' "$RESULTS")" = note ]
[ "$(jq -r 'select(.status == "ok") | .platform' "$RESULTS" | wc -l | tr -d ' ')" -eq 5 ]
test "$(cat "$TMP/calls")" = 'notess-jass-enx-jaCoinbase moved $44M; only $188K was realzenn'

# Shell command strings/background dispatch are rejected before execution.
printf '%s\n' '{"platform":"note","lang":"ja","argv":["bash","-c","sleep 30 &"]}' >"$TMP/background.jsonl"
set +e
bash "$DISPATCH" --manifest "$TMP/background.jsonl" --results "$TMP/background-results.jsonl" >"$TMP/background.out" 2>&1
bg_rc=$?
set -e
test "$bg_rc" -ne 0
rg -q 'foreground|shell -c|background' "$TMP/background.out"

echo 'PASS: dispatch preserves argv dollars, waits foreground, rejects background shell strings, and isolates failures'
