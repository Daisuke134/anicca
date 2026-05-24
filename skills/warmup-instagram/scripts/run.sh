#!/usr/bin/env bash
# warmup-instagram — 7-day Personal-account warmup orchestrator.
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"
set -a; . "$ROOT/.env"; set +a

[ -f "$ACCOUNTS_DIR/instagram.json" ] || { echo "🛑 No instagram.json — run instagram-account-factory first"; exit 91; }

cat <<EOF
🛡 7-DAY IG WARMUP — $PERSONA

instagrapi loop (headless, no iPhone needed):
  Day 1-2: 5 explore × 10 min, like ~5/session, watch full reels
  Day 3-4: follow 2-3 niche accounts (after content view)
  Day 5-7: comment on 1-2 reels/day, save 2-3

NO PFP/bio/link/first post until day 8.

Implementation:
  pip3 install instagrapi
  Real loop: scripts/warmup_loop.py (TODO)
EOF

python3 -c "
import json, os, datetime
p = '$ACCOUNTS_DIR/instagram.json'
d = json.load(open(p)) if os.path.exists(p) else {}
d['warmup_started_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
d['warmup_days_target'] = 7
d['status'] = 'warming_up'
json.dump(d, open(p, 'w'), indent=2)
print('  ✅ status → warming_up')
"
