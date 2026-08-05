#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
SOURCE="$SCRIPT_DIR/stable-launcher.sh"
DESTINATION="${JOB_SEARCH_LIBEXEC_ROOT:-$HOME/.local/libexec/anicca/job-search}"
mkdir -p "$DESTINATION"
chmod 0755 "$DESTINATION"
for lane in daily inbox learning; do
  install -m 0555 "$SOURCE" "$DESTINATION/$lane"
done
print -r -- "$DESTINATION"
