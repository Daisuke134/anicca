#!/usr/bin/env bash
# warmup-tiktok — 7-day ghost mode warmup orchestrator.
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
set -a; . "$ROOT/.env"; set +a

[ -f "$ACCOUNTS_DIR/tiktok.json" ] || { echo "🛑 No tiktok.json — run tiktok-account-factory first"; exit 81; }

cat <<EOF
🛡 7-DAY WARMUP — $PERSONA

Goal: convince TikTok algo this is a real US consumer, not a bot.

Daily routine (automated via iOS Voice Control once Dais OTG-mounts iPhone):
  - 5-6 FYP scroll sessions × 15-20 min
  - Watch full videos (no instant swipes)
  - Like ~5/session
  - Comment on 1/session (short, normal)
  - Days 3-4: follow 2-3 niche creators
  - Days 5-7: save 2-3 videos
  - DO NOT add PFP / bio / link until day 8+

Manual hardware bridge (Dais one-time setup):
  1. iPhone OTG-cable to Mac Mini
  2. scrcpy mirror running
  3. iOS Voice Control → enabled on iPhone
  4. macOS Keyboard Maestro / AppleScript scripts triggering Voice Control commands

Once OTG bridge is live, this script can drive the full 7-day routine.

For now (no OTG): Dais does manual scroll on iPhone, this script just tracks days.
EOF

# Mark warmup start
python3 -c "
import json, os, datetime
p = '$ACCOUNTS_DIR/tiktok.json'
d = json.load(open(p))
d['warmup_started_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
d['warmup_days_target'] = 7
d['status'] = 'warming_up'
json.dump(d, open(p, 'w'), indent=2)
print('  ✅ status → warming_up')
"

# Slack ping if configured
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  curl -sS -X POST "$SLACK_WEBHOOK_URL" -H "Content-Type: application/json" \
    -d "$(python3 -c "import json; print(json.dumps({'text': f'🛡 warmup-tiktok started for {\"$PERSONA\"} — 7-day ghost mode begins now. Day 8 → ready for posting.'}))")" >/dev/null
fi
