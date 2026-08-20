#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
WORKER="$ROOT/skills/writer-agent/scripts/zenn-deferred-worker.sh"
TMP="$(mktemp -d /tmp/zenn-lock.XXXXXX)"
HOLDER=''
cleanup() { touch "$TMP/release" 2>/dev/null || true; test -z "$HOLDER" || wait "$HOLDER" 2>/dev/null || true; rm -rf -- "$TMP"; }
trap cleanup EXIT
LOCK="$TMP/worker.lock"
mkdir -p "$TMP/runs/run/gates"
printf '{"status":"pending","run_id":"run","sentinel":"unchanged"}\n' >"$TMP/runs/run/gates/zenn-deferred.json"

python3 - "$LOCK" "$TMP/ready" "$TMP/release" <<'PY' &
import fcntl, pathlib, sys, time
lock, ready, release = map(pathlib.Path, sys.argv[1:])
with lock.open("a+") as handle:
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    ready.touch()
    while not release.exists():
        time.sleep(0.02)
PY
HOLDER=$!
for _ in {1..100}; do test -e "$TMP/ready" && break; sleep 0.02; done
test -e "$TMP/ready"
bash "$WORKER" --runs-root "$TMP/runs" --ledger "$TMP/ledger" --lock-file "$LOCK" --log "$TMP/worker.log"
test "$(jq -r .sentinel "$TMP/runs/run/gates/zenn-deferred.json")" = unchanged
rg -q 'lock busy; another Zenn retry scan owns the queue' "$TMP/worker.log"

echo 'PASS: a concurrent fcntl owner prevents queue mutation'
