#!/usr/bin/env bash
# warmup-youtube — 1-2 day light interest-graph seeding.
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"

[ -f "$ACCOUNTS_DIR/youtube.json" ] || { echo "🛑 No youtube.json — run youtube-account-factory first"; exit 95; }

cat <<EOF
🛡 1-2 DAY YT WARMUP — $PERSONA

Daily routine (light):
  Day 1: watch 3-5 niche videos from parent Gmail — informs algo interest graph
  Day 2: watch 3-5 more, like 1-2, subscribe 1 niche channel

Day 3+: ready for spawned factory cron uploads via Postiz YT integration.

Implementation: Playwright YT iframe player (TODO scripts/watch_loop.py).
EOF

python3 -c "
import json, datetime
p = '$ACCOUNTS_DIR/youtube.json'
d = json.load(open(p))
d['warmup_started_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
d['warmup_days_target'] = 2
d['status'] = 'warming_up'
json.dump(d, open(p, 'w'), indent=2)
print('  ✅ status → warming_up')
"
