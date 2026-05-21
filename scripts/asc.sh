#!/usr/bin/env bash
# asc ラッパー: プロジェクト .env を自動読み込みして asc を実行する。
# 使い方: ./scripts/asc.sh apps list --bundle-id "ai.anicca.app.ios"
# または:  make -C /path/to/anicca-project asc で呼び出し可。

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
fi

exec asc "$@"
