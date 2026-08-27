#!/usr/bin/env bash
set -euo pipefail
STATE=~/.openclaw/state/postiz-integrations.json
[ -f "$STATE" ] || { echo "❌ $STATE not found"; exit 3; }
set -a; . ~/.openclaw/.env; set +a

python3 - "$STATE" <<'PY'
import json, sys, datetime, os
path = sys.argv[1]
d = json.load(open(path))
today = datetime.date.today()
flipped = []
seeded = []
changed = False
for i in d.get('integrations', []):
    if i.get('warmup_phase') != 'warmup':
        continue
    started = i.get('warmup_started_at')
    if not started:
        i['warmup_started_at'] = today.isoformat()
        seeded.append(i.get('handle','?'))
        changed = True
        continue
    try:
        start_date = datetime.date.fromisoformat(started)
    except Exception:
        continue
    age_days = (today - start_date).days
    if age_days >= 7:
        i['warmup_phase'] = 'live'
        flipped.append(f"{i.get('handle','?')} ({age_days}d)")
        changed = True

if changed:
    d['updated_at'] = datetime.datetime.now().astimezone().isoformat()
    json.dump(d, open(path, 'w'), indent=2, ensure_ascii=False)

print(f"warmup-flip: seeded={len(seeded)} flipped={len(flipped)}")
for h in seeded: print(f"  📌 seeded warmup_started_at={today}: {h}")
for h in flipped: print(f"  🚀 flipped to live: {h}")

# Slack ping if any flips (for Dais notification)
if flipped:
    slack = os.environ.get('SLACK_BOT_TOKEN')
    if slack:
        import urllib.request
        msg = f"🚀 Warmup graduation: {len(flipped)} account(s) → live\n" + "\n".join(flipped)
        req = urllib.request.Request(
            'https://slack.com/api/chat.postMessage',
            data=json.dumps({'channel':'C091G3PKHL2','text':msg}).encode(),
            headers={'Authorization': f'Bearer {slack}', 'Content-Type':'application/json'})
        urllib.request.urlopen(req).read()
PY
