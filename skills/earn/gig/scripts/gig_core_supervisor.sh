#!/usr/bin/env bash
# Provider-free liveness anchor retained for the existing tmux health contract.
set -uo pipefail
HEARTBEAT="$HOME/gig/.gig-core-heartbeat"
mkdir -p "$HOME/gig"
while :; do
  touch "$HEARTBEAT"
  sleep 60
done
