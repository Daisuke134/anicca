#!/bin/bash
# reinvest — the compounding half of the loop. Revenue lands in the founder wallet on Base;
# anything above the operating reserve gets deployed to yield automatically. No human decides
# when to reinvest, and no human moves the money.
#
# Reserve exists so the wallet can always pay for compute and inference; only the surplus works.
set -uo pipefail
TS=$(date -u +%FT%TZ)
export ANICCA_HOME=/Users/anicca/.anicca-founder
export COMPUTE_RESERVE_USDC=${COMPUTE_RESERVE_USDC:-3}
export YIELD_MIN_DEPLOY_USDC=${YIELD_MIN_DEPLOY_USDC:-1}

cd /Users/anicca/.blockrun/skills/earn || exit 0
# launchd PATH lacks coreutils; call node directly (the script has its own network timeouts)
out=$(PATH=/opt/homebrew/bin:/usr/bin:/bin node execute-yield.mjs 2>&1 | tail -1)
echo "$TS $out"
