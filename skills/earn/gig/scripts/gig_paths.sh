#!/usr/bin/env bash

# Canonical filesystem contract for every Gig shell entrypoint.
# This file may be sourced from any working directory.
GIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIFE_MANAGER_REPO="$(cd "$GIG_DIR/../../.." && pwd)"
LIFE_MANAGER_HOME="${LIFE_MANAGER_HOME:-${ANICCA_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/life-manager}}"
GIG_RUNNER_DIR="${GIG_RUNNER_DIR:-$LIFE_MANAGER_REPO/runtime/agent-runner}"
GIG_BROWSER_DIR="${GIG_BROWSER_DIR:-$LIFE_MANAGER_REPO/skills/browser}"
GIG_STATE_DIR="${GIG_STATE_DIR:-$HOME/gig}"
GIG_HOST_STATE_DIR="${GIG_HOST_STATE_DIR:-$LIFE_MANAGER_HOME/state}"
GIG_LOG_DIR="${GIG_LOG_DIR:-$LIFE_MANAGER_HOME/logs}"
GIG_ENV_FILE="${GIG_ENV_FILE:-$LIFE_MANAGER_HOME/.env}"

export LIFE_MANAGER_REPO LIFE_MANAGER_HOME GIG_DIR GIG_RUNNER_DIR GIG_BROWSER_DIR
export GIG_STATE_DIR GIG_HOST_STATE_DIR GIG_LOG_DIR GIG_ENV_FILE
