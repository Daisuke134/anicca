"""Durable, replay-safe JSONL ingest. All writers lock the same journal."""
import fcntl
import json
import math
import os
from pathlib import Path


def ingest(path, owner, body):
    record_id, record = body['record_id'], dict(body['record'])
    if not isinstance(record_id, str) or len(record_id) != 64:
        raise ValueError('invalid record id')
    if not isinstance(record.get('delivery_id'), str) or not record['delivery_id']:
        raise ValueError('missing delivery id')
    if 'stimulus' in record:
        stimulus = record['stimulus']
        probability = stimulus['assigned_probability']
        if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 < probability <= 1:
            raise ValueError('invalid assignment probability')
        for key in ('message_id', 'policy_version'):
            if not isinstance(stimulus.get(key), str):
                raise ValueError('missing assignment metadata')
        if not isinstance(record.get('fallback'), bool) or not isinstance(record.get('backend'), str):
            raise ValueError('missing provenance')
        if record['backend'] != 'manager-v1':
            record['fallback'] = True
    elif record.get('event') not in {
        'notification_delivered', 'notification_opened', 'app_opened',
        'responded', 'skipped', 'saved', 'shared', 'shown', 'thumbs_up', 'thumbs_down'
    }:
        raise ValueError('invalid event')
    record['person_id'] = owner
    row = dict(record, record_id=record_id)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+', encoding='utf-8') as journal:
        fcntl.flock(journal, fcntl.LOCK_EX)
        journal.seek(0)
        for line in journal:
            existing = json.loads(line)
            if existing['person_id'] == owner and existing['record_id'] == record_id:
                if existing != row:
                    raise ValueError('conflicting replay')
                return {'accepted': True, 'record_id': record_id}
        journal.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
        journal.flush()
        os.fsync(journal.fileno())
    return {'accepted': True, 'record_id': record_id}
