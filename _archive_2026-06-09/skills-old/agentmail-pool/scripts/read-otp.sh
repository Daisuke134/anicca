#!/bin/bash
# Usage: read-otp.sh <inbox_email>
INBOX="${1:?inbox required}"
python3 -c "
import json, os, urllib.request, re
pool = json.load(open(os.path.expanduser('~/.openclaw/state/agentmail-tt-pool.json')))
entry = pool['inboxes'].get('$INBOX')
if not entry: raise SystemExit(f'inbox $INBOX not in pool')
key = os.environ.get(entry['api_key_env'])
if not key: raise SystemExit(f'env {entry[\"api_key_env\"]} not set')
req = urllib.request.Request(f'https://api.agentmail.to/v0/inboxes/$INBOX/messages?limit=5', headers={'Authorization': f'Bearer {key}'})
d = json.loads(urllib.request.urlopen(req).read())
for m in d.get('messages', []):
    subj = m.get('subject', '') or ''
    prev = m.get('preview', '') or ''
    # 6-digit OTP 抽出
    codes = re.findall(r'\b(\d{4,8})\b', subj + ' ' + prev)
    if codes:
        print(f'[{m.get(\"timestamp\",\"\")[:19]}] OTP candidates: {codes}  subj=\"{subj[:70]}\"')
    else:
        print(f'[{m.get(\"timestamp\",\"\")[:19]}] subj=\"{subj[:70]}\"')
"
