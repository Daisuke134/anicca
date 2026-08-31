#!/usr/bin/env bash

# Canonical filesystem contract for every Gig shell entrypoint.
# This file may be sourced from any working directory.
GIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MR_BOT_REPO="$(cd "$GIG_DIR/../../.." && pwd)"
MR_BOT_HOME="${MR_BOT_HOME:-${ANICCA_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/mr-bot}}"
GIG_RUNNER_DIR="${GIG_RUNNER_DIR:-$MR_BOT_REPO/runtime/agent-runner}"
GIG_BROWSER_DIR="${GIG_BROWSER_DIR:-$MR_BOT_REPO/skills/browser}"
GIG_STATE_DIR="${GIG_STATE_DIR:-$HOME/gig}"
GIG_HOST_STATE_DIR="${GIG_HOST_STATE_DIR:-$MR_BOT_HOME/state}"
GIG_LOG_DIR="${GIG_LOG_DIR:-$MR_BOT_HOME/logs}"
GIG_ENV_FILE="${GIG_ENV_FILE:-$MR_BOT_HOME/.env}"

export MR_BOT_REPO MR_BOT_HOME GIG_DIR GIG_RUNNER_DIR GIG_BROWSER_DIR
export GIG_STATE_DIR GIG_HOST_STATE_DIR GIG_LOG_DIR GIG_ENV_FILE
