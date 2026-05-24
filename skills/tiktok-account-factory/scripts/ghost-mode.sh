#!/usr/bin/env bash
# Ghost mode: ensure no PFP / no bio / no link in bio for 48-72h.
# Algorithm trust comes from "looks like a bored US human consumer".
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"

cat <<EOF
🛡 GHOST MODE — $PERSONA
For the next 48-72 hours, the account MUST stay naked:
  ❌ No profile picture
  ❌ No bio
  ❌ No link in bio
  ✅ Scroll FYP 15-20 min/session, multiple sessions/day
  ✅ Watch full videos (no instant swipes)
  ✅ Like a few, leave short comments
  ✅ Follow 2-3 niche creators (only after watching their content fully)

This is automated by the warmup-tiktok skill (l-portet/tiktok-warmup-bot pattern).

Hand-off to:  bash ~/.openclaw/skills/warmup-tiktok/scripts/run.sh $PERSONA
EOF

# Mark account state
python3 -c "
import json
p = '$ACCOUNTS_DIR/tiktok.json'
d = json.load(open(p)) if __import__('os').path.exists(p) else {}
d['ghost_mode_started_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
d['status'] = 'ghost_mode'
json.dump(d, open(p, 'w'), indent=2)
"
echo "  ✅ status → ghost_mode"
