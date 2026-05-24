#!/usr/bin/env bash
# revenue-allocator — monthly treasury allocation.
set -uo pipefail
[ -f ~/anicca-monk-factory/.env ] && set -a && source ~/anicca-monk-factory/.env && set +a
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
exec python3 ~/.openclaw/skills/revenue-allocator/scripts/run.py
