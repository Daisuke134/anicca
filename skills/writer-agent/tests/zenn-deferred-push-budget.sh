#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/skills/article-writer/tests/_exact8-fixture.sh"
WORKER="$ROOT/skills/article-writer/scripts/zenn-deferred-worker.sh"
CONTROL="$ROOT/skills/article-writer/scripts/zenn-deferred-control.py"
TMP="$(mktemp -d /tmp/zenn-push-budget.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
LEDGER="$TMP/articles.jsonl"
mkdir -p "$TMP/seed/articles"
for slug in budget-slug-01 budget-slug-02; do
  printf '%s\n' '---' "title: \"$slug\"" 'published: true' '---' >"$TMP/seed/articles/$slug.md"
done
git init --bare "$TMP/remote.git" >/dev/null
git -C "$TMP/seed" init -b main >/dev/null
git -C "$TMP/seed" -c user.name=test -c user.email=test@example.test add articles
git -C "$TMP/seed" -c user.name=test -c user.email=test@example.test commit -m seed >/dev/null
git -C "$TMP/seed" remote add origin "$TMP/remote.git"
git -C "$TMP/seed" push origin main >/dev/null
git clone "$TMP/remote.git" "$TMP/repo" >/dev/null 2>&1

for n in 01 02; do
  run="run-$n"; slug="budget-slug-$n"
  mkdir -p "$TMP/runs/$run/gates"
  python3 "$CONTROL" create --artifact "$TMP/runs/$run/gates/zenn-deferred.json" \
    --markdown-file "$TMP/repo/articles/$slug.md" --slug "$slug"
  exact8_init_state "$ROOT" "$TMP/runs/$run" "$LEDGER" "$run" "topic-$run" "$slug"
  python3 "$CONTROL" handoff --repo "$TMP/repo" --ledger "$LEDGER" --run-id "$run" \
    --artifact "$TMP/runs/$run/gates/zenn-deferred.json" >/dev/null
done
printf '{"articles":[{"slug":"old","published_at":"2026-07-20T00:00:00Z"}]}\n' >"$TMP/api.json"
cat >"$TMP/push-wrapper" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'push\n' >>"$PUSH_CALLS"
git -C "$1" push origin "$2:refs/heads/main"
exit 1
SH
printf '#!/usr/bin/env bash\nexit 1\n' >"$TMP/reality"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/notify"
chmod +x "$TMP/push-wrapper" "$TMP/reality" "$TMP/notify"
: >"$TMP/push.calls"

PUSH_CALLS="$TMP/push.calls" bash "$WORKER" --ledger "$LEDGER" --runs-root "$TMP/runs" \
  --repo "$TMP/repo" --expected-remote "$TMP/remote.git" --api-json "$TMP/api.json" \
  --now 2026-07-21T01:00:00Z --test-push-bin "$TMP/push-wrapper" --reality-gate "$TMP/reality" \
  --notify-bin "$TMP/notify" --lock-file "$TMP/worker.lock" \
  --publication-lock-dir "$TMP/publication.lockdir" \
  --backlog-state "$TMP/backlog.json" --log "$TMP/worker.log"

test "$(wc -l <"$TMP/push.calls" | tr -d ' ')" -eq 1
test "$(git --git-dir="$TMP/remote.git" rev-list --count main)" -eq 2
test "$(jq -r .last_action "$TMP/runs/run-01/gates/zenn-deferred.json")" = network-error
test "$(jq -r 'has("last_action")' "$TMP/runs/run-02/gates/zenn-deferred.json")" = false

# A failure to fetch happens before a push attempt: it is transient, never quarantine,
# and safely allows the scan to inspect the later queue item.
git -C "$TMP/repo" remote set-url origin "$TMP/unreachable.git"
: >"$TMP/push.calls"
PUSH_CALLS="$TMP/push.calls" bash "$WORKER" --ledger "$LEDGER" --runs-root "$TMP/runs" \
  --repo "$TMP/repo" --expected-remote "$TMP/unreachable.git" --api-json "$TMP/api.json" \
  --now 2026-07-21T01:05:00Z --test-push-bin "$TMP/push-wrapper" --reality-gate "$TMP/reality" \
  --notify-bin "$TMP/notify" --lock-file "$TMP/worker.lock" \
  --publication-lock-dir "$TMP/publication.lockdir" \
  --backlog-state "$TMP/backlog.json" --log "$TMP/worker.log"
test ! -s "$TMP/push.calls"
test "$(jq -r .status "$TMP/runs/run-01/gates/zenn-deferred.json")" = pending
test "$(jq -r .status "$TMP/runs/run-02/gates/zenn-deferred.json")" = pending
test "$(jq -r .last_action "$TMP/runs/run-02/gates/zenn-deferred.json")" = fetch-error
rg -q 'transient fetch failure.*later queue items continue' "$TMP/worker.log"

echo 'PASS: started push consumes budget while pre-push fetch failures continue safely'
