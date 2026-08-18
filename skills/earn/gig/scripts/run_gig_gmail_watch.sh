#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
set -a
. "$HOME/.openclaw/.env"
set +a
exec /opt/homebrew/bin/openclaw webhooks gmail run
