#!/bin/zsh

JOB_SEARCH_PATHS_FILE="${${(%):-%N}:A}"
typeset -gx JOB_SEARCH_APP_ROOT="${JOB_SEARCH_PATHS_FILE:h:h}"
typeset -gx JOB_SEARCH_REPO_ROOT="${JOB_SEARCH_APP_ROOT:h:h}"
typeset -gx JOB_SEARCH_RUNNER="${JOB_SEARCH_REPO_ROOT}/runtime/agent-runner/agent_runner.py"
typeset -gx JOB_SEARCH_STATE_ROOT="${JOB_SEARCH_STATE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/anicca/job-search}"
typeset -gx JOB_SEARCH_PROFILE="${JOB_SEARCH_PROFILE:-${XDG_CONFIG_HOME:-$HOME/.config}/anicca/job-search/profile.json}"
typeset -gx JOB_SEARCH_INSTALL_CONFIG="${JOB_SEARCH_INSTALL_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/anicca/job-search/install.json}"
typeset -gx JOB_SEARCH_FRAMEWORK_ROOT="${JOB_SEARCH_FRAMEWORK_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/framework}"
typeset -gx JOB_SEARCH_TELEGRAM_MEDIA="${JOB_SEARCH_TELEGRAM_MEDIA:-$HOME/.openclaw/media/job-search-outbound}"
typeset -gx JOB_SEARCH_LAUNCH_AGENT_DIR="${JOB_SEARCH_LAUNCH_AGENT_DIR:-$HOME/Library/LaunchAgents}"
typeset -gx JOB_SEARCH_PRIVATE_ENV="${JOB_SEARCH_PRIVATE_ENV:-$HOME/.openclaw/.env}"
if [[ -x /opt/homebrew/bin/python3 ]]; then
  typeset -gx JOB_SEARCH_PYTHON="${JOB_SEARCH_PYTHON:-/opt/homebrew/bin/python3}"
else
  typeset -gx JOB_SEARCH_PYTHON="${JOB_SEARCH_PYTHON:-$(command -v python3)}"
fi
typeset -gx JOB_SEARCH_JQ="${JOB_SEARCH_JQ:-/usr/bin/jq}"
typeset -gx JOB_SEARCH_PLUTIL="${JOB_SEARCH_PLUTIL:-/usr/bin/plutil}"
typeset -gx JOB_SEARCH_LAUNCHCTL="${JOB_SEARCH_LAUNCHCTL:-/bin/launchctl}"
typeset -gx JOB_SEARCH_OPENCLAW="${JOB_SEARCH_OPENCLAW:-/opt/homebrew/bin/openclaw}"
if [[ -z "${AGENT_RUNNER_PROVIDER:-}" && -f "$JOB_SEARCH_INSTALL_CONFIG" ]]; then
  JOB_SEARCH_SELECTED_PROVIDER=$("$JOB_SEARCH_PYTHON" - \
    "$JOB_SEARCH_INSTALL_CONFIG" <<'PY'
import json
import sys
from pathlib import Path

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
provider = value.get("provider")
if provider not in {"codex", "claude-direct"}:
    raise SystemExit("invalid provider in install receipt")
print(provider, end="")
PY
  )
  typeset -gx AGENT_RUNNER_PROVIDER="$JOB_SEARCH_SELECTED_PROVIDER"
  unset JOB_SEARCH_SELECTED_PROVIDER
fi
