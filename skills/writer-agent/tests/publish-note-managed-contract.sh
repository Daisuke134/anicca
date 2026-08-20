#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/run"
printf '# ja\n' >"$TMP/run/article-ja.md"
printf '# en\n' >"$TMP/run/article-en.md"
printf 'post\n' >"$TMP/run/x-post-ja.txt"
printf 'headline' >"$TMP/run/headline.png"
HASH="$(shasum -a 256 "$TMP/run/headline.png" | awk '{print $1}')"
cat >"$TMP/state.json" <<JSON
{"pairs":{"note/ja":{"status":"intent","target_kind":"note-key","target":"n-test"}},"media":{"headline_image":{"path":"$TMP/run/headline.png","sha256":"$HASH"}}}
JSON

cat >"$TMP/bin/policy" <<'SH'
#!/usr/bin/env bash
printf '%s\n' '{"access_model":"one_time_purchase","currency":"JPY","paywall_required":true,"price_minor":500,"publisher_args":["--price","500"]}'
SH
cat >"$TMP/bin/eyecatch" <<'SH'
#!/usr/bin/env bash
echo 'EYECATCH_IN_EDITOR: https://assets.st-note.com/test.png'
SH
cat >"$TMP/bin/enable" <<'SH'
#!/usr/bin/env bash
echo enable >>"$CALL_LOG"
SH
cat >"$TMP/bin/disable" <<'SH'
#!/usr/bin/env bash
echo disable >>"$CALL_LOG"
SH
cat >"$TMP/bin/publisher" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$ARGS_LOG"
python3 - "$ARTICLE_PUBLICATION_STATE" <<'PY'
import json, sys
p=sys.argv[1]; d=json.load(open(p)); d["pairs"]["note/ja"].update({"status":"live","live_url":"https://note.com/anicca123/n/n-test"}); json.dump(d,open(p,"w"))
PY
echo 'PAID_PUBLISHED key=n-test price=500 verified=true'
SH
chmod +x "$TMP/bin/"*

CALL_LOG="$TMP/calls" ARGS_LOG="$TMP/args" \
ARTICLE_RUN_DIR="$TMP/run" \
ARTICLE_PUBLICATION_STATE="$TMP/state.json" \
NOTE_POLICY_COMMAND="$TMP/bin/policy" \
NOTE_EYECATCH_COMMAND="$TMP/bin/eyecatch" \
NOTE_ENABLE_COMMAND="$TMP/bin/enable" \
NOTE_DISABLE_COMMAND="$TMP/bin/disable" \
NOTE_PUBLISH_COMMAND="$TMP/bin/publisher" \
python3 "$ROOT/scripts/publish-note-managed.py"

grep -Fx -- '--key n-test --price 500 --after-chars 2500 --arm' "$TMP/args"
test "$(sed -n '1p' "$TMP/calls")" = enable
test "$(sed -n '2p' "$TMP/calls")" = disable
python3 - "$TMP/state.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))["pairs"]["note/ja"]["status"] == "live"
PY
echo "PASS: managed note publication is fixed paid, guarded, and durable"
