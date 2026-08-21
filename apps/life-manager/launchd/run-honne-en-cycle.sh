#!/bin/zsh
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
DATA_DIR="${LM_DATA_DIR:-$HOME/.local/state/life-manager}"
ENV_FILE="$DATA_DIR/.env"
MANIFEST="$DATA_DIR/tenants/dais-local/marketing/imports/honne-ai-reelclaw-en.json"
APPROVAL_REF="object://sha256/44c8fef63d46892d813c775b9a41462dd459761081ce67e2d155b6bdcf1e917c"

[[ -r "$ENV_FILE" && -r "$MANIFEST" ]] || exit 1
set -a
source "$ENV_FILE"
set +a

export LM_DATA_DIR="$DATA_DIR"
export LM_RUNTIME_TENANT_ID="dais-local"
export LM_HONNE_EN_PACK_REF="$(jq -r '.pack_ref' "$MANIFEST")"
export LM_HONNE_EN_MEDIA_REFS="$(jq -r '.media_refs | join(",")' "$MANIFEST")"
export LM_HONNE_EN_PUBLICATION_APPROVAL_REF="$APPROVAL_REF"

exec /opt/homebrew/bin/node \
  /Users/anicca/Projects/life-manager-main/apps/life-manager/scripts/honne-en-cycle.js run
