#!/bin/bash
# Usage: provision.sh <human_email> <username>
HUMAN_EMAIL="${1:?human_email required}"
USERNAME="${2:?username required}"
python3 -c "
from agentmail import AgentMail
c = AgentMail()
r = c.agent.sign_up(human_email='$HUMAN_EMAIL', username='$USERNAME', source='anicca')
print('org_id=' + r.organization_id)
print('inbox=' + r.inbox_id)
print('api_key=' + r.api_key)
import json, os, datetime
log = os.path.expanduser('~/.openclaw/state/agentmail-pool.jsonl')
with open(log, 'a') as f:
    f.write(json.dumps({
        'created_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'human_email': '$HUMAN_EMAIL',
        'username': '$USERNAME',
        'org_id': r.organization_id,
        'inbox': r.inbox_id,
        'api_key': r.api_key,
    }) + '\n')
"
