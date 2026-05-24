#!/usr/bin/env bash
# anicca-meetup-talk-applier — watch Gmail for accept/decline mail
# This script logs what to look for; the actual mail-read happens via Gmail MCP
# in the agent turn (cron payload). Output: data/applications/<slug>.json status flip.
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-meetup-talk-applier
echo "▶ watch — pending applications:"

ls "$SKILL/data/applications/" 2>/dev/null \
  | while read -r f; do
      [ -f "$SKILL/data/applications/$f" ] || continue
      STATUS=$(jq -r .status "$SKILL/data/applications/$f")
      EVENT=$(jq -r .event "$SKILL/data/applications/$f")
      [ "$STATUS" = "pending" ] && echo "  [pending] $EVENT  ($f)"
    done

echo ""
echo "Use Gmail MCP from agent turn:"
echo "  search 'from:luma OR from:no-reply@meetup OR from:connpass newer_than:7d'"
echo "  for each thread mentioning a pending event slug, update status:"
echo "    accepted → status='accepted', accepted_at=<ts>, ping Slack + Cal"
echo "    declined → status='declined', declined_at=<ts>, log only"
