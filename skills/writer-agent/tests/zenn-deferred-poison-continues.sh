#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/skills/writer-agent/tests/_exact8-fixture.sh"
WORKER="$ROOT/skills/writer-agent/scripts/zenn-deferred-worker.sh"
CONTROL="$ROOT/skills/writer-agent/scripts/zenn-deferred-control.py"
TMP="$(mktemp -d /tmp/zenn-poison.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
LEDGER="$TMP/articles.jsonl"
mkdir -p "$TMP/seed/articles"
printf '%s\n' '---' 'title: "False title"' 'published: true' '---' >"$TMP/seed/articles/false-slug-01.md"
git init --bare "$TMP/remote.git" >/dev/null
git -C "$TMP/seed" init -b main >/dev/null
git -C "$TMP/seed" -c user.name=test -c user.email=test@example.test add articles
git -C "$TMP/seed" -c user.name=test -c user.email=test@example.test commit -m seed >/dev/null
git -C "$TMP/seed" remote add origin "$TMP/remote.git"
git -C "$TMP/seed" push origin main >/dev/null
git clone "$TMP/remote.git" "$TMP/repo" >/dev/null 2>&1
printf '%s\n' '---' 'title: "Missing title"' 'published: true' '---' >"$TMP/repo/articles/missing-slug-1.md"
printf '%s\n' '---' 'title: "Stale healthy title"' 'published: true' '---' >"$TMP/repo/articles/stale-slug-01.md"

for run in 01-missing 02-false 03-stale-healthy; do mkdir -p "$TMP/runs/$run/gates"; done
python3 "$CONTROL" create --artifact "$TMP/runs/01-missing/gates/zenn-deferred.json" \
  --markdown-file "$TMP/repo/articles/missing-slug-1.md" --slug missing-slug-1
exact8_init_state "$ROOT" "$TMP/runs/01-missing" "$LEDGER" 01-missing topic-01-missing missing-slug-1
python3 "$CONTROL" handoff --test-allow-local-source --repo "$TMP/repo" --ledger "$LEDGER" --run-id 01-missing \
  --artifact "$TMP/runs/01-missing/gates/zenn-deferred.json" >/dev/null
python3 "$CONTROL" create --artifact "$TMP/runs/02-false/gates/zenn-deferred.json" \
  --markdown-file "$TMP/repo/articles/false-slug-01.md" --slug false-slug-01
exact8_init_state "$ROOT" "$TMP/runs/02-false" "$LEDGER" 02-false topic-02-false false-slug-01
python3 "$CONTROL" handoff --repo "$TMP/repo" --ledger "$LEDGER" --run-id 02-false \
  --artifact "$TMP/runs/02-false/gates/zenn-deferred.json" >/dev/null
python3 "$CONTROL" create --artifact "$TMP/runs/03-stale-healthy/gates/zenn-deferred.json" \
  --markdown-file "$TMP/repo/articles/stale-slug-01.md" --slug stale-slug-01
exact8_init_state "$ROOT" "$TMP/runs/03-stale-healthy" "$LEDGER" 03-stale-healthy topic-03-stale-healthy stale-slug-01
python3 "$CONTROL" handoff --test-allow-local-source --repo "$TMP/repo" --ledger "$LEDGER" --run-id 03-stale-healthy \
  --artifact "$TMP/runs/03-stale-healthy/gates/zenn-deferred.json" >/dev/null

# Advance the real remote without updating the worker clone's origin/main: one previously
# valid source becomes poison while a previously absent healthy source is added.
printf '%s\n' '---' 'title: "False title"' 'published: false' '---' >"$TMP/seed/articles/false-slug-01.md"
printf '%s\n' '---' 'title: "Stale healthy title"' 'published: true' '---' >"$TMP/seed/articles/stale-slug-01.md"
git -C "$TMP/seed" -c user.name=test -c user.email=test@example.test add articles
git -C "$TMP/seed" -c user.name=test -c user.email=test@example.test commit -m remote-advance >/dev/null
git -C "$TMP/seed" push origin main >/dev/null
printf '{"articles":[{"slug":"false-slug-01","published_at":"2026-07-20T00:00:00Z"}]}\n' >"$TMP/api.json"
printf '#!/usr/bin/env bash\nexit 1\n' >"$TMP/reality"; chmod +x "$TMP/reality"
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$*" >>"$NOTIFY_CALLS"\n' >"$TMP/notify"; chmod +x "$TMP/notify"

NOTIFY_CALLS="$TMP/notify.calls" bash "$WORKER" --ledger "$LEDGER" --runs-root "$TMP/runs" \
  --repo "$TMP/repo" --expected-remote "$TMP/remote.git" --api-json "$TMP/api.json" \
  --now 2026-07-21T01:00:00Z --reality-gate "$TMP/reality" --notify-bin "$TMP/notify" \
  --lock-file "$TMP/worker.lock" --publication-lock-dir "$TMP/publication.lockdir" \
  --backlog-state "$TMP/backlog.json" --log "$TMP/worker.log"

test "$(jq -r .status "$TMP/runs/01-missing/gates/zenn-deferred.json")" = quarantined
test "$(jq -r .status "$TMP/runs/02-false/gates/zenn-deferred.json")" = quarantined
test "$(jq -r .quarantine_notification_status "$TMP/runs/02-false/gates/zenn-deferred.json")" = sent
test "$(jq -r .last_action "$TMP/runs/03-stale-healthy/gates/zenn-deferred.json")" = reality-pending
test "$(git --git-dir="$TMP/remote.git" rev-list --count main)" -eq 3
rg -q '02-false.*quarantined' "$TMP/worker.log"
rg -q '02-false.*quarantined' "$TMP/notify.calls"

echo 'PASS: fetched missing/false poison is quarantined and stale-ref healthy work proceeds'
