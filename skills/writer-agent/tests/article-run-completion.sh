#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
GATE="$ROOT/skills/writer-agent/scripts/article-run-complete.py"
TMP="$(mktemp -d /tmp/article-run-complete.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
LEDGER="$TMP/articles.jsonl"
STATE="$TMP/runs/current-run/gates/publication-state.json"
mkdir -p "$(dirname "$STATE")"
printf '%s\n' '{"version":1,"publication_contract":"legacy-exact8","run_id":"current-run"}' >"$STATE"

emit() {
  printf '{"run_id":"%s","topic_id":"%s","platform":"%s","lang":"%s","live_url":"https://example.test/%s-%s","published":true,"reality_gate":"PASS"}\n' \
    "$1" "$2" "$3" "$4" "$3" "$4" >>"$LEDGER"
}

# Old complete run and a quality carry-over must not complete the current run.
for pair in 'note ja' 'zenn-article ja' 'devto en' 'substack ja' 'substack en' 'x-article ja' 'x-article en' 'x-post ja'; do set -- $pair; emit old-run old-topic "$1" "$2"; done
printf '%s\n' '{"run_id":"current-run","state":"carry-over:reader-testing","published":false}' >>"$LEDGER"
! python3 "$GATE" --ledger "$LEDGER" --run-id current-run --armed 1 --publication-state "$STATE"

# Seven valid rows are still incomplete.
for pair in 'note ja' 'zenn-article ja' 'devto en' 'substack ja' 'substack en' 'x-article ja' 'x-article en'; do set -- $pair; emit current-run current-topic "$1" "$2"; done
! python3 "$GATE" --ledger "$LEDGER" --run-id current-run --armed 1 --publication-state "$STATE"

# A row without reality PASS cannot satisfy the eighth slot.
printf '%s\n' '{"run_id":"current-run","topic_id":"current-topic","platform":"x-post","lang":"ja","live_url":"https://example.test/x-post-ja","published":true,"reality_gate":"FAIL"}' >>"$LEDGER"
! python3 "$GATE" --ledger "$LEDGER" --run-id current-run --armed 1 --publication-state "$STATE"

emit current-run current-topic x-post ja
python3 "$GATE" --ledger "$LEDGER" --run-id current-run --armed 1 --publication-state "$STATE"

# Exact-eight means a duplicate successful pair is not completion evidence.
emit current-run current-topic x-post ja
if python3 "$GATE" --ledger "$LEDGER" --run-id current-run --armed 1 --publication-state "$STATE"; then
  echo 'FAIL: duplicate successful pair incorrectly satisfied exact-eight completion' >&2
  exit 1
fi
echo 'PASS: armed completion requires the current run/topic exact eight live reality-PASS rows'
