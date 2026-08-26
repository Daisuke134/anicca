#!/usr/bin/env bash
set -uo pipefail

SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export X_LOOP_ROLE=original
export X_LOOP_NAME=x-tweeter
export X_REPOST_FORCE_KIND=original
export X_REPOST_DISABLE_AFFILIATE=1
export X_REPOST_STATE_DIR="${X_TWEETER_STATE_DIR:-$HOME/loops/x-tweeter}"
export X_REPOST_CODEX_HOME="${X_TWEETER_CODEX_HOME:-$HOME/.local/state/life-manager/x-tweeter-codex}"
export AFFILIATE_REPOST_PROPOSAL_PATH="$X_REPOST_STATE_DIR/no-affiliate-proposal.json"
export AFFILIATE_X_DISTRIBUTION_QUEUE="$X_REPOST_STATE_DIR/no-affiliate-jobs.jsonl"

exec "$SKILL/../x-repost/x-repost-cli.sh" "$@"
