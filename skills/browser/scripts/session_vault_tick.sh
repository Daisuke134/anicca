#!/bin/bash
# launchd tick (every 30 min): bank the logins, then warm the server-side sessions so they
# expire less often. Human-zero — reports only, never asks anyone to log in.
#
# Warms the daily-driver (:9222) AND every clip-accounts.json account (clip-en :9223, clip-en2
# :9224, ...). Before this, only :9222 was ever warmed, so a clip profile's Instagram session
# would go cold and die after ~24h of no browser traffic (the loop still posts via instagrapi,
# but the CDP/web session itself rots). port/profile come from clip-accounts.json — never
# hardcode them here, that file is the single source of truth for the account roster.
set -uo pipefail
V="$HOME/anicca/skills/browser/scripts/session_vault.py"
ACCOUNTS="$HOME/.cloak/clip-accounts.json"
log(){ echo "$(date '+%F %T') session_vault_tick: $*" >&2; }

# ── daily-driver (:9222) — unchanged behavior ──
log "daily-driver: dump"
python3 "$V" dump || true
log "daily-driver: keepalive"
python3 "$V" keepalive \
  "https://coconala.com/mypage/dashboard" \
  "https://www.instagram.com/" || true

# ── per-account clip browsers (clip-en, clip-en2, clip-en3, ...) ──
# Guard: clip_pass.sh drives these same Chrome profiles concurrently (posting via instagrapi,
# some CDP use). Opening extra tabs on the same IG-authenticated profile while a pass is live
# risks a concurrent-session signature_revoked (see TASKLIST 3a). So the whole clip block
# (dump + keepalive both open CDP tabs) is skipped, not just keepalive, whenever a pass is
# running — dump()'s localStorage snapshot also opens an instagram.com tab.
if pgrep -f "clip_pass\.sh" >/dev/null 2>&1; then
  log "clip accounts: SKIP all (clip_pass.sh is running — avoid concurrent-session IG signature_revoked, TASKLIST 3a)"
elif [ ! -f "$ACCOUNTS" ]; then
  log "clip accounts: SKIP (no $ACCOUNTS)"
else
  jq -r '.[] | select(.status=="ready" or .status=="warming") | "\(.handle)\t\(.profile)\t\(.port)"' "$ACCOUNTS" |
  while IFS=$'\t' read -r handle profile port; do
    [ -z "$port" ] && continue
    if ! curl -s -m 3 "http://127.0.0.1:${port}/json/version" >/dev/null 2>&1; then
      log "clip/$handle ($profile:$port): SKIP (browser not up)"
      continue
    fi
    log "clip/$handle ($profile:$port): dump"
    SESSION_VAULT_PORT="$port" SESSION_VAULT_DIR="$HOME/.cloak/vault/$profile" python3 "$V" dump || true
    log "clip/$handle ($profile:$port): keepalive"
    SESSION_VAULT_PORT="$port" SESSION_VAULT_DIR="$HOME/.cloak/vault/$profile" python3 "$V" keepalive \
      "https://www.instagram.com/" || true
  done
fi
