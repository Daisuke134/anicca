#!/bin/bash
set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
exec python3 "$HOME/.openclaw/skills/mr-bot-video/store-recordings.py"
