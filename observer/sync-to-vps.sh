#!/bin/bash
set -euo pipefail

OBSERVER_DIR="${HOME}/.openclaw/observer"
VPS_USER="anicca"
VPS_HOST="ubuntu-4gb-nbg1-7"  # Tailscale hostname
VPS_PATH="/home/anicca/.openclaw/workspace/observer/observations/"

# Ensure remote directory exists
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p ${VPS_PATH}" 2>/dev/null || true

# Sync observations to VPS
if rsync -avz --progress \
    "${OBSERVER_DIR}/observations/" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}"; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Sync completed successfully" >> "${OBSERVER_DIR}/logs/sync.log"
else
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Sync FAILED with exit code $?" >> "${OBSERVER_DIR}/logs/sync.log"
    exit 1
fi
