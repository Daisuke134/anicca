#!/bin/zsh
set -euo pipefail

if [[ $# -ne 1 ]]; then
  print -u2 "usage: freehire-resolved-search.sh <query>"
  exit 2
fi

BASE_URL="${FREEHIRE_API_URL:-https://freehire.me}"
BASE_URL="${BASE_URL%/}"
HOST="${BASE_URL#https://}"
HOST="${HOST%%/*}"
RESOLVE_ARGS=()
if [[ "$HOST" == "freehire.me" ]]; then
  ADDRESS=$(dig +short @1.1.1.1 "$HOST" A +time=3 +tries=1 | awk 'NF {print; exit}')
  [[ -n "$ADDRESS" ]] || {
    print -u2 '{"error":"freehire DNS fallback returned no address","code":"SEARCH_FAILED"}'
    exit 1
  }
  RESOLVE_ARGS+=(--resolve "${HOST}:443:${ADDRESS}")
fi

exec /usr/bin/curl -sS --max-time 30 "${RESOLVE_ARGS[@]}" \
  --get "$BASE_URL/api/v1/jobs/search" \
  --data-urlencode "q=$1" \
  --data-urlencode "limit=10" \
  --data-urlencode "offset=0" \
  --data-urlencode "semantic_ratio=0" \
  --data-urlencode "posted_within_days=30" \
  --data-urlencode "countries=JP" \
  -H 'Accept: application/json' \
  -H 'User-Agent: anicca-job-search/1.0'
