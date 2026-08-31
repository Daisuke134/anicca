#!/bin/bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
TARGET="${MR_BOT_CHECKOUT:-$HOME/mr-bot}"

if [ -e "$TARGET" ] && [ ! -d "$TARGET/.git" ]; then
  echo "[job-hunter] $TARGET exists but is not a Git checkout; move it and retry" >&2
  exit 2
fi
if ! command -v brew >/dev/null 2>&1; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi
if ! command -v git >/dev/null 2>&1; then
  brew install git
fi

if [ -d "$TARGET/.git" ]; then
  git -C "$TARGET" fetch origin main
  git -C "$TARGET" merge --ff-only origin/main
else
  git clone --depth 1 --branch main https://github.com/Daisuke134/life-manager.git "$TARGET"
fi

export MR_BOT_CHECKOUT="$TARGET"
exec "$TARGET/install.sh" job-hunter
