#!/usr/bin/env bash
# Q31 — hire humans for physical-world tasks (rentahuman.ai). auth = x-api-key (account/api-keys, agent self-signup)
curl https://rentahuman.ai/api/humans -H "x-api-key: $RENTAHUMAN_KEY"          # search (free)
# create a bounty (hire), MUST pay (escrow):
curl -X POST https://rentahuman.ai/api/bounties -H "x-api-key: $RENTAHUMAN_KEY" -H "Content-Type: application/json" \
  -d '{"title":"...","reward_usdc":50,"dryRun":true}'
