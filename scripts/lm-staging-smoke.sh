#!/usr/bin/env bash
# lm-staging-smoke.sh — smoke test for the life-call-staging Railway service.
# Curls the health route (server.js serves 200 JSON {ok:true,...} on both "/" and "/health").
# Exit 0 on HTTP 200, exit 1 otherwise.
set -uo pipefail

DOMAIN="${1:-https://life-call-staging-staging.up.railway.app}"

CODE=$(curl -s -o /dev/null -m 10 -w "%{http_code}" "$DOMAIN/health")

echo "GET $DOMAIN/health -> $CODE"

if [ "$CODE" = "200" ]; then
  echo "SMOKE OK"
  exit 0
else
  echo "SMOKE FAILED"
  exit 1
fi
