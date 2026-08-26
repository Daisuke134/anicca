#!/usr/bin/env bash
# Resolve a Python that can operate the CP1 raw-CDP helper.  The old shared
# Cloak venv was removed; do not make every agent rediscover that path.
set -euo pipefail

for candidate in "${CP1_PYTHON:-}" /opt/homebrew/bin/python3 "$(command -v python3 2>/dev/null || true)"; do
  [ -n "$candidate" ] && [ -x "$candidate" ] || continue
  if "$candidate" -c 'import playwright, websocket' >/dev/null 2>&1; then
    exec "$candidate" "$@"
  fi
done

echo 'CP1 requires a Python with playwright and websocket; set CP1_PYTHON to one.' >&2
exit 127
