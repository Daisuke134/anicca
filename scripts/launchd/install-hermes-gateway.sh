#!/usr/bin/env bash
# Installs the Hermes gateway as a user-level launchd background service.
# Idempotent: if already installed, `hermes gateway install` is a no-op or upgrade.
set -euo pipefail
hermes gateway install
hermes cron status
launchctl list | grep -i hermes || true
