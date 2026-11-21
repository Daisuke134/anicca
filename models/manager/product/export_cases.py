"""Read-only ManagerBench JSONL projection of the committed private journal.

Usage: python -m models.manager.product.export_cases /private/cases.db > /private/cases.jsonl
Never writes to the source DB or invents negative outcomes for missing callbacks.
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def export_cases(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as db:
        for (body,) in db.execute('SELECT body FROM cases ORDER BY subject,id'):
            decision = json.loads(body)
            row = decision.get('managerbench_case')
            if row is None:
                continue  # Legacy rows lack the new conditioning/provenance contract.
            for observation in decision['observations']:
                if observation['in_window']:
                    event = observation['event']
                    row['response'][event] = True
                    stamp = datetime.fromtimestamp(observation['observed_at'], timezone.utc).isoformat(timespec='seconds')
                    key = event + '_at'
                    row['response'][key] = min(row['response'].get(key, stamp), stamp)
            yield row


if __name__ == '__main__':
    for row in export_cases(sys.argv[1]):
        print(json.dumps(row, sort_keys=True, allow_nan=False))
