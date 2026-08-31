#!/usr/bin/env bash
# Bounded Connector Healer shadow pass. It never installs itself, merges, deploys, or submits externally.
set -eu
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
STATE_DIR="${LM_CONNECTOR_STATE_DIR:-$HOME/.local/state/mr-bot/connector-native}"
WORKTREE_ROOT="${LM_CONNECTOR_HEALER_WORKTREE_ROOT:-$HOME/.local/state/mr-bot/connector-healer-worktrees}"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"

case "$STATE_DIR" in /*) ;; *) exit 2 ;; esac
case "$WORKTREE_ROOT" in /*) ;; *) exit 2 ;; esac
[ -n "$NODE_BIN" ] && [ -x "$NODE_BIN" ] || exit 2

exec "$NODE_BIN" "$HERE/healer-shadow-cli.js" \
  --repo-root "$REPO_ROOT" \
  --state-dir "$STATE_DIR" \
  --worktree-root "$WORKTREE_ROOT"
