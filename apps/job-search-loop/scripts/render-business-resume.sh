#!/bin/zsh
set -euo pipefail

APP_ROOT="${0:A:h:h}"
PROFILE="${XDG_CONFIG_HOME:-$HOME/.config}/anicca/job-search/profile.json"
OUTPUT="${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/materials/business"
PYTHONPATH="$APP_ROOT" python3 -c \
  'from pathlib import Path; from job_search_loop.materials import render_business; import sys; print(render_business(Path(sys.argv[1]), Path(sys.argv[2])))' \
  "$PROFILE" "$OUTPUT"
