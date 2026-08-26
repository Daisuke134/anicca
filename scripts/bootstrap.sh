#!/bin/bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
TARGET="${LIFE_MANAGER_CHECKOUT:-$HOME/life-manager}"

if [ -e "$TARGET" ] && [ ! -d "$TARGET/.git" ]; then
  echo "[life-manager] $TARGET exists but is not a Git checkout; move it and retry" >&2
  exit 2
fi
if ! command -v brew >/dev/null 2>&1; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi
if ! command -v git >/dev/null 2>&1; then
  brew install git
fi
if ! command -v python3 >/dev/null 2>&1 \
  || ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 13))' >/dev/null 2>&1; then
  brew install python@3.14
fi

if [ -d "$TARGET/.git" ]; then
  git -C "$TARGET" fetch origin main
  git -C "$TARGET" merge --ff-only origin/main
else
  git clone --depth 1 --branch main https://github.com/Daisuke134/life-manager.git "$TARGET"
fi

VENV="$HOME/.local/share/life-manager/venv"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
if ! "$VENV/bin/python" -c 'import jsonschema' >/dev/null 2>&1; then
  "$VENV/bin/pip" install jsonschema
fi

exec "$VENV/bin/python" "$TARGET/scripts/life-manager-onboarding-server.py" --open
