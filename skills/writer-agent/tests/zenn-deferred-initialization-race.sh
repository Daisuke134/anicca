#!/usr/bin/env bash
set -euo pipefail
export ARTICLE_TEST_ONLY=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/skills/writer-agent/tests/_exact8-fixture.sh"
CONTROL="$ROOT/skills/writer-agent/scripts/zenn-deferred-control.py"
WORKER="$ROOT/skills/writer-agent/scripts/zenn-deferred-worker.sh"
TMP="$(mktemp -d /tmp/zenn-init-race.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
RUN_ID="daily-2026-07-27"
RUN_DIR="$TMP/runs/$RUN_ID"
STATE="$RUN_DIR/gates/publication-state.json"
ARTIFACT="$RUN_DIR/gates/zenn-deferred.json"
LEDGER="$TMP/articles.jsonl"
SLUG="initialization-race-article"
mkdir -p "$TMP/repo/articles" "$RUN_DIR/gates"

printf '%s\n' '---' 'title: "Initialization race"' 'published: true' '---' '# Body' \
  >"$TMP/repo/articles/$SLUG.md"
git init --bare "$TMP/remote.git" >/dev/null
git -C "$TMP/repo" init -b main >/dev/null
git -C "$TMP/repo" -c user.name=test -c user.email=test@example.test add "articles/$SLUG.md"
git -C "$TMP/repo" -c user.name=test -c user.email=test@example.test commit -m seed >/dev/null
git -C "$TMP/repo" remote add origin "$TMP/remote.git"
git -C "$TMP/repo" push -u origin main >/dev/null

python3 "$CONTROL" create --artifact "$ARTIFACT" \
  --markdown-file "$TMP/repo/articles/$SLUG.md" --slug "$SLUG"
exact8_init_state "$ROOT" "$RUN_DIR" "$LEDGER" "$RUN_ID" topic-init-race "$SLUG"
cp "$STATE" "$TMP/full-state.json"
python3 - "$STATE" <<'PY'
import json
import sys

path = sys.argv[1]
state = json.load(open(path, encoding="utf-8"))
state["pairs"].pop("x-article/en")
with open(path, "w", encoding="utf-8") as handle:
    json.dump(state, handle, separators=(",", ":"))
PY

printf '%s\n' '{"articles":[{"slug":"older-article","published_at":"2026-07-20T17:08:36+00:00"}]}' \
  >"$TMP/api.json"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/notify"
chmod +x "$TMP/notify"
COMMON_ARGS=(
  --ledger "$LEDGER"
  --runs-root "$TMP/runs"
  --repo "$TMP/repo"
  --expected-remote "$TMP/remote.git"
  --test-allow-local-source
  --api-json "$TMP/api.json"
  --now 2026-07-21T16:08:36+00:00
  --notify-bin "$TMP/notify"
  --lock-file "$TMP/worker.lock"
  --publication-lock-dir "$TMP/publication.lockdir"
  --backlog-state "$TMP/backlog.json"
  --log "$TMP/worker.log"
)

# A partially registered exact8 state is a normal initialization race. It must
# remain retryable rather than becoming permanent poison.
bash "$WORKER" "${COMMON_ARGS[@]}"
test "$(jq -r .status "$ARTIFACT")" = pending
test "$(jq -r .last_action "$ARTIFACT")" = initialization-pending
rg -q 'initialization incomplete.*pending retained' "$TMP/worker.log"

# A legacy artifact already quarantined for that exact transient reason must
# self-heal after the complete target set appears.
cp "$TMP/full-state.json" "$STATE"
python3 - "$ARTIFACT" <<'PY'
import json
import sys

path = sys.argv[1]
artifact = json.load(open(path, encoding="utf-8"))
artifact.update({
    "status": "quarantined",
    "last_action": "quarantined",
    "last_error": "INVARIANT: publication state is not worker-safe: missing-targets",
    "quarantined_at": "2026-07-21T16:00:00Z",
    "quarantine_notification_status": "sent",
})
with open(path, "w", encoding="utf-8") as handle:
    json.dump(artifact, handle, separators=(",", ":"))
PY

bash "$WORKER" "${COMMON_ARGS[@]}"
test "$(jq -r .status "$ARTIFACT")" = pending
test "$(jq -r .last_action "$ARTIFACT")" = waiting
test "$(jq -r 'has("quarantined_at")' "$ARTIFACT")" = false
test "$(jq -r 'has("last_error")' "$ARTIFACT")" = false
rg -q 'initialization quarantine recovered' "$TMP/worker.log"

# A later pair repair can also turn an old ambiguous worker-plan quarantine
# back into a fully valid pending-publication plan. Re-read the current
# publication state instead of preserving the stale quarantine forever.
exact8_record_other_seven "$ROOT" "$RUN_DIR" "$LEDGER"
python3 - "$ARTIFACT" <<'PY'
import json
import sys

path = sys.argv[1]
artifact = json.load(open(path, encoding="utf-8"))
artifact.update({
    "status": "quarantined",
    "last_action": "quarantined",
    "last_error": "INVARIANT: publication state is not worker-safe: ambiguous-target-or-reality",
    "quarantined_at": "2026-07-21T16:05:00Z",
    "quarantine_notification_status": "sent",
})
with open(path, "w", encoding="utf-8") as handle:
    json.dump(artifact, handle, separators=(",", ":"))
PY

bash "$WORKER" "${COMMON_ARGS[@]}"
test "$(jq -r .status "$ARTIFACT")" = pending
test "$(jq -r .last_action "$ARTIFACT")" = waiting
test "$(jq -r 'has("quarantined_at")' "$ARTIFACT")" = false
test "$(jq -r 'has("last_error")' "$ARTIFACT")" = false
rg -q 'stale worker-plan quarantine recovered' "$TMP/worker.log"

echo "PASS: Zenn initialization and stale worker-plan quarantines self-heal"
