#!/bin/sh
# Push X_BEARER_TOKEN, APIFY_API_TOKEN, REDDAPI_API_KEY to VPS .openclaw/.env (no output of values)
set -e
cd "$(dirname "$0")/../.."
. ./.env 2>/dev/null || true
VPS="${VPS_USER:-anicca}@${VPS_HOST:-46.225.70.241}"
REMOTE="/home/anicca/.openclaw/.env"
for k in X_BEARER_TOKEN APIFY_API_TOKEN REDDIT_SESSION; do
  eval "v=\$$k"
  if [ -n "$v" ]; then
    ssh -o BatchMode=yes -o ConnectTimeout=10 "$VPS" "mkdir -p /home/anicca/.openclaw; touch $REMOTE; grep -v '^${k}=' $REMOTE 2>/dev/null > /tmp/env.tmp || true; echo '${k}=${v}' >> /tmp/env.tmp; mv /tmp/env.tmp $REMOTE" && echo "OK: $k" || echo "FAIL: $k"
  else
    echo "SKIP (empty): $k"
  fi
done
echo "Done."
