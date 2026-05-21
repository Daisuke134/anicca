#!/usr/bin/env bash
# asc auth login ヘルパー: .env の ASC_* を使って keychain に永続登録する。
# 実行後は asc を直接叩いても動く（.env 不要）。
# 前提: .env に ASC_KEY_ID, ASC_ISSUER_ID, および ASC_PRIVATE_KEY_PATH または ASC_PRIVATE_KEY が設定されていること。

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
  echo "Error: .env not found at $REPO_ROOT"
  exit 1
fi

set -a
# shellcheck source=/dev/null
. ./.env
set +a

KEY_PATH=""
if [[ -n "${ASC_PRIVATE_KEY_PATH:-}" ]] && [[ -f "${ASC_PRIVATE_KEY_PATH/#\~/$HOME}" ]]; then
  KEY_PATH="${ASC_PRIVATE_KEY_PATH/#\~/$HOME}"
elif [[ -n "${ASC_PRIVATE_KEY:-}" ]] && [[ -n "${ASC_KEY_ID:-}" ]]; then
  # asc auth login はパスを keychain に保存するため、一時ファイルではなく永続パスに保存
  ASC_KEYS_DIR="${HOME}/.asc/private_keys"
  mkdir -p "$ASC_KEYS_DIR"
  KEY_PATH="${ASC_KEYS_DIR}/AuthKey_${ASC_KEY_ID}.p8"
  echo "$ASC_PRIVATE_KEY" > "$KEY_PATH"
  chmod 600 "$KEY_PATH"
fi

if [[ -z "$KEY_PATH" ]] || [[ ! -f "$KEY_PATH" ]]; then
  echo "Error: Valid .p8 key not found."
  echo "  Set ASC_PRIVATE_KEY_PATH to a .p8 file path, or ASC_PRIVATE_KEY to key content."
  exit 1
fi

if [[ -z "${ASC_KEY_ID:-}" ]] || [[ -z "${ASC_ISSUER_ID:-}" ]]; then
  echo "Error: ASC_KEY_ID and ASC_ISSUER_ID must be set in .env"
  exit 1
fi

asc auth login \
  --name "Anicca" \
  --key-id "$ASC_KEY_ID" \
  --issuer-id "$ASC_ISSUER_ID" \
  --private-key "$KEY_PATH" \
  --network

echo "Done. Run 'asc auth doctor' to verify."
