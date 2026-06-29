#!/usr/bin/env bash
# whop-driver/login.sh — Whop email-magic-link login on CloakBrowser daily-driver
#
# Usage:
#   bash login.sh                       # uses myclaude-clip@agentmail.to default
#   bash login.sh other@agentmail.to    # alt account
#
# Prereqs:
#   - CloakBrowser daily-driver running at :9222
#   - AGENTMAIL_API_KEY in ~/.openclaw/.env (or env)
#   - cdp.py at ~/.claude/skills/ig-account-create/scripts/
#   - read_otp.py at the same place
#
# Output (stdout, one JSON line):
#   {"tid": "<targetId>", "url": "<final URL>", "logged_in": true}
set -euo pipefail

EMAIL="${1:-myclaude-clip@agentmail.to}"
PY=/opt/homebrew/bin/python3
CDP=~/.claude/skills/ig-account-create/scripts/cdp.py
READ_OTP=~/.claude/skills/ig-account-create/scripts/read_otp.py

# Load env (= AgentMail key)
if [ -f /Users/anicca/.openclaw/.env ]; then
  set -a; source /Users/anicca/.openclaw/.env; set +a
fi

# 1. Open login page
TID=$("$PY" "$CDP" new "https://whop.com/login/")
sleep 6

# 2. Fill email + click Continue / 続ける (= both EN and JA UIs)
"$PY" "$CDP" eval "$TID" - <<JS >/dev/null
(() => {
  function setNative(el, val) {
    const p = Object.getPrototypeOf(el);
    const s = Object.getOwnPropertyDescriptor(p, 'value').set;
    s.call(el, val);
    el.dispatchEvent(new Event('input', {bubbles:true}));
    el.dispatchEvent(new Event('change', {bubbles:true}));
  }
  const i = document.querySelector('input[type=email]');
  i.focus();
  setNative(i, '$EMAIL');
  const btn = Array.from(document.querySelectorAll('button'))
    .find(b => ['Continue', '続ける'].includes((b.innerText||'').trim()));
  btn.click();
})()
JS
sleep 6

# 3. Read OTP from AgentMail inbox of the email
OTP=$("$PY" "$READ_OTP" --inbox "$EMAIL" --key-env AGENTMAIL_API_KEY --match Whop --timeout 60)
if [ -z "$OTP" ]; then
  echo "{\"error\":\"no OTP received for $EMAIL\"}" >&2
  exit 1
fi

# 4. Insert OTP into the otp input
"$PY" "$CDP" eval "$TID" - <<JS >/dev/null
(() => {
  function setNative(el, val) {
    const p = Object.getPrototypeOf(el);
    const s = Object.getOwnPropertyDescriptor(p, 'value').set;
    s.call(el, val);
    el.dispatchEvent(new Event('input', {bubbles:true}));
    el.dispatchEvent(new Event('change', {bubbles:true}));
  }
  const i = document.querySelector('input[name=otp]') ||
            Array.from(document.querySelectorAll('input'))
              .find(x => x.getBoundingClientRect().height > 0);
  i.focus();
  setNative(i, '$OTP');
})()
JS
sleep 6

# 5. Verify by reading URL — logged-in lands on /home-feed or /
URL=$("$PY" "$CDP" url "$TID" | $PY -c "import json,sys;print(json.load(sys.stdin)['url'])")
LOGGED_IN=false
case "$URL" in
  https://whop.com/home-feed/*|https://whop.com/|https://whop.com/?*)
    LOGGED_IN=true ;;
esac

echo "{\"tid\":\"$TID\",\"url\":\"$URL\",\"logged_in\":$LOGGED_IN}"
