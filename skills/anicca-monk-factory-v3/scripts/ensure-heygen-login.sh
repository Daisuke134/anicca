#!/usr/bin/env bash
# Ensure camofox is logged into HeyGen (autonomous, no human). Run before any HeyGen render.
# Strategy: check /avatars; if logged out, do magic-link login (camofox sends link → gog reads it → camofox opens it).
# Needs: camofox :9377 up, gog (GOG_KEYRING_PASSWORD), GOOGLE_LOGIN_EMAIL/{{profile.contact.personalEmail}}.
set -uo pipefail
source "$(dirname "$0")/lib/camo.sh"
EMAIL="${GOOGLE_LOGIN_EMAIL:-{{profile.contact.personalEmail}}}"
GOGPW="${GOG_KEYRING_PASSWORD:-<password>}"
camo_up

logged_in() {
  local tab="$1"
  camo_nav "$tab" "https://app.heygen.com/avatars" >/dev/null 2>&1; sleep 7
  ! camo_text "$tab" 2>/dev/null | grep -qiE "Sign in with|Send a secure magic|Continue with Google|Log in to"
}

TAB=$(camo_open "https://app.heygen.com/avatars"); sleep 7
if logged_in "$TAB"; then echo "HEYGEN_ALREADY_LOGGED_IN"; exit 0; fi

echo "HeyGen logged out — magic-link login"
camo_nav "$TAB" "https://app.heygen.com/login" >/dev/null; sleep 6
# reveal {{profile.lateness.stakeholders.channel}} step + fill + send
camo_click_sel "$TAB" "button:has-text(\"Use {{profile.lateness.stakeholders.channel}}\")" >/dev/null 2>&1; sleep 2
camo_eval "$TAB" "(()=>{const e=[...document.querySelectorAll('input[type={{profile.lateness.stakeholders.channel}}]')].find(i=>i.offsetParent);if(e){e.focus();e.value='';}return!!e})()" >/dev/null 2>&1
camo_type_sel "$TAB" "input[type={{profile.lateness.stakeholders.channel}}]" "$EMAIL" >/dev/null 2>&1; sleep 1
camo_click_sel "$TAB" "button:has-text(\"Send a secure magic link\")" >/dev/null 2>&1
echo "magic link requested; waiting for {{profile.lateness.stakeholders.channel}}"; sleep 8

# read the freshest magic link via gog (poll up to ~90s)
LINK=""
for i in $(seq 1 15); do
  ID=$(GOG_KEYRING_PASSWORD="$GOGPW" /opt/homebrew/bin/gog gmail search -a "$EMAIL" -p "from:heygen subject:magic newer_than:5m" 2>/dev/null | grep -i magic | head -1 | awk '{print $1}')
  if [ -n "$ID" ]; then
    LINK=$(GOG_KEYRING_PASSWORD="$GOGPW" /opt/homebrew/bin/gog gmail get "$ID" -a "$EMAIL" -p 2>/dev/null | grep -oE 'https://auth\.heygen\.com/magic-web[^ "<>]+' | head -1)
    [ -n "$LINK" ] && break
  fi
  sleep 6
done
[ -n "$LINK" ] || { echo "FATAL: no magic link {{profile.lateness.stakeholders.channel}} found"; exit 1; }
echo "got magic link, opening"
camo_nav "$TAB" "$LINK" >/dev/null; sleep 9

if logged_in "$TAB"; then echo "HEYGEN_LOGIN_OK"; exit 0; else echo "FATAL: still logged out after magic link"; exit 2; fi
