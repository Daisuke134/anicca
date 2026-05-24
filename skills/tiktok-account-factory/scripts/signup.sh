#!/usr/bin/env bash
# TikTok signup via Playwright + SadCaptcha.
# Phone-number flow (NOT {{profile.lateness.stakeholders.channel}} — phone signup = trust signal per Shalev).
# STUB: real Playwright code lives in scripts/signup.spec.ts (TODO).
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"
set -a; . "$ROOT/.env"; set +a

if [ -z "${SADCAPTCHA_API_KEY:-}" ]; then
  echo "🛑 SADCAPTCHA_API_KEY missing — Dais must sign up at sadcaptcha.com"
  exit 21
fi

[ -f "$ACCOUNTS_DIR/tiktok.json" ] || { echo "❌ tiktok.json missing — run smspool-buy.sh first"; exit 22; }

PHONE=$(python3 -c "import json; print(json.load(open('$ACCOUNTS_DIR/tiktok.json')).get('phone',''))")

# TODO: implement scripts/signup.spec.ts (Playwright):
# 1. Launch Playwright with proxy (Surfshark Dedicated IP) + iOS user-agent
# 2. Open https://www.tiktok.com/signup
# 3. Click "Use phone or {{profile.lateness.stakeholders.channel}}" → "Phone"
# 4. Enter $PHONE (US format)
# 5. Solve captcha via SadCaptcha API
# 6. Wait for SMS delivery (otp-relay.sh handles the OTP fetch)
# 7. After OTP success, set username (slug-based: @<persona-slug>) + password
# 8. Save credentials to $ACCOUNTS_DIR/tiktok.json
echo "🛠 STUB: signup.sh — Playwright spec not yet implemented."
echo "  Phone: $PHONE"
echo "  Persona: $PERSONA"
echo "  Implementation reference: l-portet/tiktok-warmup-bot for {{profile.lateness.stakeholders.channel}} automation patterns."
echo "  Next: write scripts/signup.spec.ts using @playwright/test + SadCaptcha integration."
exit 99
