#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DISPATCH="$ROOT/skills/writer-agent/scripts/platform-dispatch.sh"
TMP="$(mktemp -d /tmp/article-platform-priority.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT

HELPER="$TMP/helper.sh"
cat >"$HELPER" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$1" >>"$CALLS"
SH
chmod +x "$HELPER"

printf '%s\n' '---' 'title: T' 'tags: [ai]' '---' '# Body' >"$TMP/devto.md"
: >"$TMP/cover.png"

python3 - "$TMP/jobs.jsonl" "$HELPER" "$TMP/calls" "$TMP/devto.md" "$TMP/cover.png" <<'PY'
import json, sys
path, helper, calls, markdown, cover = sys.argv[1:]
rows = [
    {"platform":"zenn","lang":"ja","argv":["bash",helper,"zenn"],"env":{"CALLS":calls}},
    {"platform":"devto","lang":"en","argv":["bash",helper,"devto","--markdown-file",markdown],"env":{"CALLS":calls}},
    {"platform":"substack","lang":"en","argv":["bash",helper,"substack-en"],"env":{"CALLS":calls}},
    {"platform":"note","lang":"ja","argv":["bash",helper,"note"],"env":{"CALLS":calls}},
    {"platform":"x","lang":"ja","argv":["bash",helper,"x"],"env":{"CALLS":calls,"X_COVER":cover}},
]
with open(path, "w", encoding="utf-8") as out:
    for row in rows:
        out.write(json.dumps(row) + "\n")
PY

bash "$DISPATCH" --manifest "$TMP/jobs.jsonl" --results "$TMP/results.jsonl"
test "$(paste -sd, "$TMP/calls")" = "note,substack-en,devto,x,zenn"
test "$(jq -r '.platform' "$TMP/results.jsonl" | paste -sd, -)" = "note,substack,devto,x,zenn"

echo "PASS: revenue lanes dispatch before non-revenue Zenn"
