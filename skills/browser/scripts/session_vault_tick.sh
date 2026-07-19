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
. "$HOME/.openclaw/skills/_shared/scripts/telegram-notify.sh" 2>/dev/null || true

# ── daily-driver (:9222) — unchanged behavior ──
log "daily-driver: dump"
python3 "$V" dump || true
log "daily-driver: keepalive"
# x.com added task #75 (2026-07-17): the article-writer loop's X session died silently for
# hours because nothing warmed/watched it here -- only coconala+instagram were on this list.
# x.com/home relies on the "Something went wrong" content-check fix in session_vault.py.
#
# zenn.dev was ALSO added here during task #75, then REMOVED again in task #76 (same day):
# Zenn publish never uses a browser session at all -- it is a plain `git push` to
# Daisuke134/zenn-articles (SKILL.md "ZENN ONE-SHOT PUBLISH", 2026-06-24), so there is no
# real session to warm or watch, and keepalive's "logged_out" check was reporting a permanent
# false alarm (zenn.dev/dashboard needs a login that this loop never uses or needs). Read the
# base skill's publish mechanism BEFORE adding a platform to this list.
KA_OUT="$(python3 "$V" keepalive \
  "https://coconala.com/mypage/dashboard" \
  "https://www.instagram.com/" \
  "https://x.com/home" || true)"
echo "$KA_OUT"
# alert immediately on any logged_out platform instead of only being discovered hours later by
# the next real business pass (exactly what happened with X today) -- never block/exit on this,
# a notify failure must not break the tick.
DEAD="$(printf '%s' "$KA_OUT" | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
dead = [p['url'] for p in d.get('pages', []) if p.get('logged_out')]
print(','.join(dead))
" 2>/dev/null || true)"
if [ -n "$DEAD" ]; then
  log "ALERT: session dead for: $DEAD"
  telegram_notify "session_vault keepalive: session DEAD for: $DEAD (daily-driver :9222). Will keep retrying every 30min; if a real pass needs it, it will self-heal or report failed per its own STEP 8." || true
fi

# password re-login self-heal for X specifically (task #75): X does not offer a passwordless
# recovery path this loop can drive, but it DOES offer a normal username+password login that
# needs no human -- as long as it is never retried more than once per incident (X flags/kills
# accounts for repeated automated login(), same warning documented in twscrape/twikit). relogin_x
# itself enforces a 6h cooldown marker, so calling it unconditionally here on every tick is safe:
# it silently no-ops (skipped:true) unless x.com is actually dead AND the cooldown has expired.
if printf '%s' "$DEAD" | grep -q "x.com"; then
  set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
  log "x.com dead -> attempting relogin_x (rate-limited to 1/6h)"
  RELOGIN_OUT="$(python3 "$V" relogin_x || true)"
  echo "$RELOGIN_OUT"
  RELOGIN_STOPPED="$(printf '%s' "$RELOGIN_OUT" | python3 -c "import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print('1' if d.get('stopped') else '')" 2>/dev/null || true)"
  if [ -n "$RELOGIN_STOPPED" ]; then
    log "ALERT: relogin_x stopped itself -- needs Dais (phone verification requested)"
    telegram_notify "X relogin self-heal STOPPED: phone/SMS verification was requested, which this AI cannot complete (SMS goes to Dais's personal phone). Needs Dais to log in manually once. See $RELOGIN_OUT" || true
  fi
fi

# ── per-account clip browsers (clip-en, clip-en2, clip-en3, ...) ──
# Guard: clip_pass.sh drives these same Chrome profiles concurrently (posting via instagrapi,
# some CDP use). Opening extra tabs on the same IG-authenticated profile while a pass is live
# risks a concurrent-session signature_revoked (see TASKLIST 3a). So the whole clip block
# (dump + keepalive both open CDP tabs) is skipped, not just keepalive, whenever a pass is
# running — dump()'s localStorage snapshot also opens an instagram.com tab.
# If a clip browser is down, relaunch it against its existing (already-logged-in) profile dir
# before giving up on it — this is what plugs the "SKIP (browser not up)" hole: a dead browser
# used to just get skipped forever, so its session never got warmed and eventually rotted.
# Never touches creds/login: this only spawns Chromium pointed at the profile's own
# user-data-dir, which restores whatever cookies are already saved on disk.
relaunch_clip_browser(){ # $1=profile $2=port
  local profile="$1" port="$2"
  local chromium
  chromium="$(ls -d "$HOME"/.cloakbrowser/chromium-*/Chromium.app/Contents/MacOS/Chromium 2>/dev/null | tail -1)"
  if [ -z "$chromium" ]; then
    log "clip/$profile:$port: relaunch SKIP (no Chromium binary found under ~/.cloakbrowser)"
    return 1
  fi
  log "clip/$profile:$port: relaunching ($chromium)"
  nohup "$chromium" --remote-debugging-port="$port" \
    --user-data-dir="$HOME/.cloak/profiles/$profile" \
    --no-first-run --no-default-browser-check \
    --disable-features=CalculateNativeWinOcclusion \
    --disable-backgrounding-occluded-windows \
    --autoplay-policy=no-user-gesture-required \
    about:blank >/dev/null 2>&1 &
  disown
  local waited=0
  while [ "$waited" -lt 15 ]; do
    if curl -s -m 2 "http://127.0.0.1:${port}/json/version" >/dev/null 2>&1; then
      log "clip/$profile:$port: relaunch OK (up after ${waited}s)"
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  log "clip/$profile:$port: relaunch FAILED (still down after 15s)"
  return 1
}

if pgrep -f "clip_pass\.sh" >/dev/null 2>&1; then
  log "clip accounts: SKIP all (clip_pass.sh is running — avoid concurrent-session IG signature_revoked, TASKLIST 3a)"
elif [ ! -f "$ACCOUNTS" ]; then
  log "clip accounts: SKIP (no $ACCOUNTS)"
else
  jq -r '.[] | select((.status=="ready" or .status=="warming") and ((.session_owner // "") != "instagrapi")) | "\(.handle)\t\(.profile)\t\(.port)"' "$ACCOUNTS" |
  while IFS=$'\t' read -r handle profile port; do
    [ -z "$port" ] && continue
    if ! curl -s -m 3 "http://127.0.0.1:${port}/json/version" >/dev/null 2>&1; then
      log "clip/$handle ($profile:$port): browser not up, attempting relaunch"
      if ! relaunch_clip_browser "$profile" "$port"; then
        log "clip/$handle ($profile:$port): SKIP (browser not up, relaunch failed)"
        continue
      fi
    fi
    log "clip/$handle ($profile:$port): dump"
    SESSION_VAULT_PORT="$port" SESSION_VAULT_DIR="$HOME/.cloak/vault/$profile" python3 "$V" dump || true
    log "clip/$handle ($profile:$port): keepalive"
    SESSION_VAULT_PORT="$port" SESSION_VAULT_DIR="$HOME/.cloak/vault/$profile" python3 "$V" keepalive \
      "https://www.instagram.com/" || true
  done

  # ── instagrapi-owned accounts (session_owner=instagrapi) ──
  # These are EXCLUDED from browser warming above (a parallel web session is the churn vector,
  # v22) — instead their golden instagrapi session gets a read-only two-stage keepalive probe
  # (v24 #12: get_timeline_feed + launcher/sync ping, never logs in, poisons on bloks).
  IG_POST="$HOME/anicca/skills/earn/marketing-engine/poster.py"
  jq -r '.[] | select((.session_owner // "") == "instagrapi" and (.status=="ready" or .status=="warming" or .status=="provisioned_pending_live_post")) | .handle' "$ACCOUNTS" |
  while IFS= read -r handle; do
    [ -z "$handle" ] && continue
    log "clip/$handle (instagrapi): golden-session keepalive"
    python3 "$IG_POST" --keepalive --handle "$handle" >&2 || true
  done
fi
