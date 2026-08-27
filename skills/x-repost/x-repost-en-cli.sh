#!/usr/bin/env bash
set -uo pipefail

SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${X_REPOST_STATE_DIR:-$HOME/loops/x-repost}"
mkdir -p "$STATE"
touch "$STATE/no-affiliate-jobs.jsonl"

export X_REPOST_DISABLE_AFFILIATE=1
export AFFILIATE_REPOST_PROPOSAL_PATH="$STATE/no-affiliate-proposal.json"
export AFFILIATE_X_DISTRIBUTION_QUEUE="$STATE/no-affiliate-jobs.jsonl"

exec "$SKILL/x-repost-cli.sh" "$@"
