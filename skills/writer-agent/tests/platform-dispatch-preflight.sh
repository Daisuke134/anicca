#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DISPATCH="$ROOT/skills/article-writer/scripts/platform-dispatch.sh"
TMP="$(mktemp -d /tmp/article-platform-preflight.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT

HELPER="$TMP/helper.sh"
cat >"$HELPER" <<'HELPER'
#!/usr/bin/env bash
printf 'CALLED\n' >>"$CALLS"
HELPER
chmod +x "$HELPER"
printf '%s\n' '---' 'title: "T"' 'published: false' '---' '# Body' >"$TMP/no-tags.md"
printf '%s\n' '---' 'title: "T"' 'tags: [ai]' 'published: false' '---' '# Body' >"$TMP/with-tags.md"
: >"$TMP/cover.png"

write_manifest() {
  python3 - "$1" "$HELPER" "$TMP/calls" "$2" "$3" <<'PY'
import json, sys
path, helper, calls, cover, md = sys.argv[1:]
rows = [
    {"platform":"x-ja","lang":"ja","argv":["bash",helper],"env":{"CALLS":calls,"X_COVER":cover}},
    {"platform":"devto","lang":"en","argv":["bash",helper,"--markdown-file",md],"env":{"CALLS":calls}},
]
with open(path,"w") as f:
    for row in rows: f.write(json.dumps(row)+"\n")
PY
}

# Missing X cover and missing Dev.to tags fail before any row executes.
write_manifest "$TMP/bad.jsonl" "$TMP/missing-cover.png" "$TMP/no-tags.md"
set +e
bash "$DISPATCH" --manifest "$TMP/bad.jsonl" --results "$TMP/bad-results.jsonl" >"$TMP/bad.out" 2>&1
bad_rc=$?
set -e
test "$bad_rc" -ne 0
test ! -s "$TMP/calls"
rg -q 'X_COVER' "$TMP/bad.out"
rg -q 'tags' "$TMP/bad.out"

# A real cover and tags permit dispatch.
write_manifest "$TMP/good.jsonl" "$TMP/cover.png" "$TMP/with-tags.md"
bash "$DISPATCH" --manifest "$TMP/good.jsonl" --results "$TMP/good-results.jsonl"
test "$(grep -c '^CALLED$' "$TMP/calls")" -eq 2

echo 'PASS: platform preflight requires X cover and Dev.to tags before any dispatch'
