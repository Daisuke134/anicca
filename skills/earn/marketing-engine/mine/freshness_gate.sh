#!/bin/bash
# freshness_gate.sh [max_age_hours] — fail loudly when the content library has gone stale.
#
# Silence was the bug: the library sat untouched for 63 days while every loop kept
# exiting rc=0 and posting from the same 68 rows. Any loop that generates from the
# library should call this first and refuse to run on a dead library.
set -euo pipefail

LIB="${MKT_LIBRARY_DIR:-$HOME/.openclaw/state/content-library}"
MAX_AGE_HOURS="${1:-${MKT_LIBRARY_MAX_AGE_HOURS:-48}}"

python3 - "$LIB" "$MAX_AGE_HOURS" <<'PY'
import json, pathlib, sys, time

lib = pathlib.Path(sys.argv[1]); max_age = float(sys.argv[2])
runs = lib / '.scrape-runs.json'
if not runs.exists():
    print(f'LIBRARY_FRESHNESS=FAIL reason=no_scrape_marker path={runs}')
    sys.exit(1)

data = json.loads(runs.read_text())
newest, newest_niche = None, None
for niche, v in data.items():
    ts = v.get('last_mined_at') if isinstance(v, dict) else None
    if not ts:
        continue
    epoch = time.mktime(time.strptime(ts, '%Y-%m-%dT%H:%M:%SZ')) - time.timezone
    if newest is None or epoch > newest:
        newest, newest_niche = epoch, niche

if newest is None:
    print('LIBRARY_FRESHNESS=FAIL reason=never_mined '
          '(the marker only holds legacy apify run ids, no last_mined_at)')
    sys.exit(1)

age_h = (time.time() - newest) / 3600
verdict = 'OK' if age_h <= max_age else 'FAIL'
print(f'LIBRARY_FRESHNESS={verdict} newest_niche={newest_niche} '
      f'age_hours={age_h:.1f} max={max_age:.0f}')
sys.exit(0 if verdict == 'OK' else 1)
PY
