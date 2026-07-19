#!/usr/bin/env bash

CAPAFY_ACCOUNT_STATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAPAFY_MARKETING_ENGINE_ACCOUNT_STATE="${CAPAFY_MARKETING_ENGINE_ACCOUNT_STATE:-$CAPAFY_ACCOUNT_STATE_DIR/../marketing-engine/account_state.sh}"
# shellcheck source=../marketing-engine/account_state.sh
. "$CAPAFY_MARKETING_ENGINE_ACCOUNT_STATE"

capafy_ig_accounts_file() {
  printf '%s\n' "${CAPAFY_IG_ACCOUNTS_FILE:-$HOME/.cloak/clip-accounts-capafy.json}"
}

_resolve_capafy_ig_account_field() {
  IG_ACCOUNT_STATE_PYTHON="${CAPAFY_ACCOUNT_STATE_PYTHON:-${IG_ACCOUNT_STATE_PYTHON:-}}" \
    resolve_ig_account_field "${1:-$(capafy_ig_accounts_file)}" "$2"
}

resolve_capafy_ig_handle() {
  IG_ACCOUNT_STATE_PYTHON="${CAPAFY_ACCOUNT_STATE_PYTHON:-${IG_ACCOUNT_STATE_PYTHON:-}}" \
    resolve_ig_handle "${1:-$(capafy_ig_accounts_file)}"
}

resolve_capafy_ig_port() {
  IG_ACCOUNT_STATE_PYTHON="${CAPAFY_ACCOUNT_STATE_PYTHON:-${IG_ACCOUNT_STATE_PYTHON:-}}" \
    resolve_ig_port "${1:-$(capafy_ig_accounts_file)}"
}

resolve_capafy_ig_session_owner() {
  IG_ACCOUNT_STATE_PYTHON="${CAPAFY_ACCOUNT_STATE_PYTHON:-${IG_ACCOUNT_STATE_PYTHON:-}}" \
    resolve_ig_session_owner "${1:-$(capafy_ig_accounts_file)}"
}

resolve_capafy_ig_started_warming() {
  IG_ACCOUNT_STATE_PYTHON="${CAPAFY_ACCOUNT_STATE_PYTHON:-${IG_ACCOUNT_STATE_PYTHON:-}}" \
    resolve_ig_started_warming "${1:-$(capafy_ig_accounts_file)}"
}

capafy_ig_warming_day() {
  IG_ACCOUNT_STATE_PYTHON="${CAPAFY_ACCOUNT_STATE_PYTHON:-${IG_ACCOUNT_STATE_PYTHON:-}}" \
    ig_warming_day "$1" "${2:-}"
}

capafy_ig_provision_reason() {
  ig_provision_reason "$1" "$2"
}
