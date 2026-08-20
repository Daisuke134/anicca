#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/run/gates"
cat >"$TMP/state.json" <<JSON
{"destination_identities":{"substack/ja":"test-ja.substack.com"},"pairs":{"substack/ja":{"status":"intent","target":"123"}}}
JSON
cat >"$TMP/run/gates/platform-dispatch.jsonl" <<JSONL
{"platform":"substack-ja","lang":"ja","argv":["bash","run.sh","--channel","substack-ja","--phase","publish","--markdown-file","$TMP/a.md","--title","題","--meta","説明"],"env":{"ARTICLE_PUBLISH_PAIR":"substack/ja"}}
JSONL
cat >"$TMP/fake" <<'SH'
#!/usr/bin/env bash
echo "$*" >>"$CALL_LOG"
if [[ "$1" == publish ]]; then python3 - "$ARTICLE_PUBLICATION_STATE" <<'PY'
import json,sys
p=sys.argv[1];d=json.load(open(p));d["pairs"]["substack/ja"]["status"]="live";json.dump(d,open(p,"w"))
PY
fi
SH
chmod +x "$TMP/fake"; : >"$TMP/a.md"
CALL_LOG="$TMP/calls" ARTICLE_RUN_DIR="$TMP/run" ARTICLE_PUBLICATION_STATE="$TMP/state.json" ARTICLE_PUBLISH_PAIR=substack/ja SUBSTACK_PUBLICATION_JA=test-ja.substack.com SUBSTACK_WRAPPER_COMMAND="$TMP/fake" SUBSTACK_REFRESH_COMMAND="$TMP/fake" python3 "$ROOT/scripts/publish-substack-managed.py"
grep -Fx -- '--pair substack/ja' "$TMP/calls"
grep -Fx 'enable-publish' "$TMP/calls"
grep -Fx "publish $TMP/a.md --title 題 --subtitle 説明 --mode go" "$TMP/calls"
grep -Fx 'disable-publish' "$TMP/calls"
echo "PASS: managed Substack publishes the persisted same-ID row"
