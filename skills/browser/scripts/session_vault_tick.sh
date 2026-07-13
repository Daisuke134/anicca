#!/bin/bash
# launchd tick (every 30 min): bank the logins, then warm the server-side sessions so they
# expire less often. Human-zero — reports only, never asks anyone to log in.
set -euo pipefail
V="$HOME/anicca/skills/browser/scripts/session_vault.py"
python3 "$V" dump || true
# Warm the sessions the loops depend on. keepalive reports logged_out=true if any redirected to /login;
# the owning loop climbs the re-login ladder itself on its next pass (see browser SKILL.md).
python3 "$V" keepalive \
  "https://coconala.com/mypage/dashboard" \
  "https://www.instagram.com/" || true
