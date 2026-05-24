#!/usr/bin/env bash
# tokyo-mic-apply-weekly.sh — Wed 09:05 JST cron
#
# TCB open-mic sign-up is a Google Form that is reCAPTCHA-v2-IMAGE gated. No {{profile.lateness.stakeholders.channel}}
# (camofox, CloakBrowser headed/headless/fresh) passes the challenge, and audio-solve
# is disabled (Dais 2026-05-21). So instead of auto-submitting, we build a PREFILLED
# form link (all fields filled, free nights = day-locked) and EMAIL it to Dais — his
# only action is: open link → solve captcha → submit (~5s).
#
# Form: https://www.tokyocomedybar.com/open-mic-sign-up  (Google Form, weekly dates)
# Stage/Name: Aniicha
# stdout last line: TCB_PREFILL: {...}
set -uo pipefail

SKILL="$HOME/.openclaw/skills/anicca-comedy-factory"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${GOG_ACCOUNT:={{profile.contact.personalEmail}}}"; : "${GOG_KEYRING_PASSWORD:=<password>}"
export GOG_ACCOUNT GOG_KEYRING_PASSWORD

python3 "$SKILL/scripts/tcb-prefill-notify.py" \
  --name "Aniicha" --{{profile.lateness.stakeholders.senderType}} "Aniicha" --days 14 \
  --to "${DAIS_EMAIL:-{{profile.contact.personalEmail}}}"

# Slack heads-up (secondary)
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🎤 TCB weekly prefilled sign-up link {{profile.lateness.stakeholders.channel}}ed to Dais (captcha+submit only)." 2>/dev/null || true
fi
