#!/bin/zsh
set -euo pipefail

APP_ROOT="${0:A:h:h}"
PROFILE="${XDG_CONFIG_HOME:-$HOME/.config}/anicca/job-search/profile.json"
OUTPUT="${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/materials/japan"
PYTHONPATH="$APP_ROOT" python3 -c \
  'from pathlib import Path; from job_search_loop.materials import render_japanese, render_japanese_rirekisho; import sys; p=Path(sys.argv[1]); o=Path(sys.argv[2]); print(render_japanese_rirekisho(p,o)); print(render_japanese(p,o))' \
  "$PROFILE" "$OUTPUT"
