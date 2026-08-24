#!/usr/bin/env bash
set -euo pipefail

GIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "${1:-}" = "preflight" ]; then
  darwin=false; arm64=false; python=false; codex_cli=false
  codex_authenticated=false; cloakbrowser=false; disk_headroom=false

  [ "$(uname -s 2>/dev/null)" = "Darwin" ] && darwin=true
  [ "$(uname -m 2>/dev/null)" = "arm64" ] && arm64=true
  if command -v python3 >/dev/null 2>&1 \
    && python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 13))' >/dev/null 2>&1; then
    python=true
  fi
  if command -v codex >/dev/null 2>&1; then
    codex_cli=true
    codex login status >/dev/null 2>&1 && codex_authenticated=true
  fi
  for candidate in "$HOME"/.cloakbrowser/chromium-*/Chromium.app/Contents/MacOS/Chromium; do
    [ -x "$candidate" ] && cloakbrowser=true && break
  done
  if df -Pk "$HOME" 2>/dev/null | awk 'NR==2 { found=1; ok=($4 >= 524288) } END { exit !(found && ok) }'; then
    disk_headroom=true
  fi

  status=blocked; exit_code=2
  if $darwin && $arm64 && $python && $codex_cli && $codex_authenticated \
    && $cloakbrowser && $disk_headroom; then
    status=ready; exit_code=0
  fi
  printf '{"status":"%s","darwin":%s,"arm64":%s,"python":%s,"codex_cli":%s,"codex_authenticated":%s,"cloakbrowser":%s,"disk_headroom":%s}\n' \
    "$status" "$darwin" "$arm64" "$python" "$codex_cli" "$codex_authenticated" "$cloakbrowser" "$disk_headroom"
  exit "$exit_code"
fi

exec "${PYTHON:-python3}" "$GIG_DIR/scripts/money_loop_onboarding.py" "$@"
