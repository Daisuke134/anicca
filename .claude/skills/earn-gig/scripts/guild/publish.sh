#!/usr/bin/env bash
# Refresh guild feed + redeploy public dashboard (every agent sees real-time).
set -uo pipefail
set -a; . "$HOME/.openclaw/.env"; set +a
G="$HOME/.claude/skills/earn-gig/scripts/guild"
DEPLOY="$HOME/.cache/guild-deploy"
SITE_ID="7f2e7689-5499-41a7-bfbe-6f50b224f963"
mkdir -p "$DEPLOY"
/opt/homebrew/bin/python3 "$G/aggregate.py" >/dev/null 2>&1
cp "$G/dashboard.html" "$DEPLOY/index.html"
cp "$G/guild_feed.json" "$DEPLOY/guild_feed.json"
/opt/homebrew/bin/netlify deploy --dir="$DEPLOY" --prod --site "$SITE_ID" --auth "$NETLIFY_AUTH_TOKEN" --no-build >/tmp/guild_publish.log 2>&1
grep -iE "live|error" /tmp/guild_publish.log | tail -2
