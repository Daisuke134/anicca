#!/bin/zsh
set -euo pipefail

if [[ $# -ne 1 ]]; then
  print -u2 "usage: firecrawl-search.sh <query>"
  exit 2
fi
SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"
source "$SCRIPT_DIR/private-env.sh"
job_search_load_private_env FIRECRAWL_API_KEY
exec /opt/homebrew/bin/firecrawl search "$1" \
  --limit 10 --country JP --scrape --scrape-formats markdown --json
