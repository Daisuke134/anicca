#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PRUNE="$ROOT/skills/writer-agent/scripts/prune-article-runs.py"
DAILY="$ROOT/skills/writer-agent/article-daily.sh"
TMP="$(mktemp -d /tmp/article-run-prune.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
RUNS="$TMP/runs"
mkdir -p "$RUNS"

for n in $(seq -w 1 31); do
  mkdir -p "$RUNS/202607${n}-000000/gates"
done
printf '%s\n' '{"status":"pending","slug":"oldest-pending"}' >"$RUNS/20260701-000000/gates/zenn-deferred.json"

python3 "$PRUNE" --runs-root "$RUNS" --keep 30

test -d "$RUNS/20260701-000000"
test ! -d "$RUNS/20260702-000000"
test "$(find "$RUNS" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" -eq 30
rg -q 'prune-article-runs\.py' "$DAILY"
echo 'PASS: run pruning keeps the oldest pending generation and removes the oldest terminal generation'
