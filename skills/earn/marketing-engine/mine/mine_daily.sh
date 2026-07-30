#!/bin/bash
# mine_daily.sh [niche] — refresh the shared content library with fresh competitor posts.
#
# Why this exists: the library was scraped ONCE (2026-05-28) and every loop has been
# regenerating from those same 68 rows ever since, so every post looks the same. The old
# doctrine "scrape once, generate forever" is what produced the sameness. Mining is daily now.
#
# One niche per run (rotating), so the Apify FREE tier ($5/month) covers a daily cadence.
#   mine_daily.sh                 -> next niche in rotation
#   mine_daily.sh monk-wisdom     -> that niche
#
# Appends deduped rows to <lib>/raw-<niche>.jsonl, then rebuilds pattern-<family>.jsonl
# while preserving each card's lastUsed/status (the analyzer rewrites those files wholesale).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="${MKT_LIBRARY_DIR:-$HOME/.openclaw/state/content-library}"
ANALYZER="${MKT_LIBRARY_ANALYZER:-$HOME/.openclaw/skills/anicca-core/scripts/library-structural-analyze.py}"
NICHES_JSON="${MKT_NICHES_JSON:-$HERE/niches.json}"
ROTATION_FILE="$LIB/.mine-rotation"
RESULTS_PER_PAGE="${MKT_MINE_RESULTS_PER_PAGE:-20}"

[ -f "$NICHES_JSON" ] || { echo "FATAL: niches config missing: $NICHES_JSON" >&2; exit 1; }
[ -f "$ANALYZER" ] || { echo "FATAL: analyzer missing: $ANALYZER" >&2; exit 1; }
mkdir -p "$LIB"

if [ -z "${APIFY_API_TOKEN:-}" ] && [ -f "$HOME/.openclaw/.env" ]; then
  APIFY_API_TOKEN="$(grep '^APIFY_API_TOKEN=' "$HOME/.openclaw/.env" | cut -d= -f2-)"
fi
[ -n "${APIFY_API_TOKEN:-}" ] || { echo "FATAL: APIFY_API_TOKEN missing" >&2; exit 1; }

# ── pick the niche ───────────────────────────────────────────────────────────
ALL_NICHES=$(python3 -c "
import json,sys
d=json.load(open('$NICHES_JSON'))
print(' '.join(k for k in d if not k.startswith('_')))")

NICHE="${1:-}"
if [ -z "$NICHE" ]; then
  LAST="$(cat "$ROTATION_FILE" 2>/dev/null || echo '')"
  NICHE=$(python3 -c "
ns='''$ALL_NICHES'''.split()
last='''$LAST'''.strip()
print(ns[(ns.index(last)+1) % len(ns)] if last in ns else ns[0])")
fi
case " $ALL_NICHES " in *" $NICHE "*) ;; *) echo "FATAL: unknown niche '$NICHE' (have: $ALL_NICHES)" >&2; exit 1;; esac

HASHTAGS_JSON=$(python3 -c "
import json; print(json.dumps(json.load(open('$NICHES_JSON'))['$NICHE'], ensure_ascii=False))")
echo "MINE niche=$NICHE hashtags=$HASHTAGS_JSON"

# ── scrape ───────────────────────────────────────────────────────────────────
PAYLOAD=$(jq -nc --argjson tags "$HASHTAGS_JSON" --argjson n "$RESULTS_PER_PAGE" '{
  hashtags: $tags,
  resultsPerPage: $n,
  shouldDownloadVideos: false,
  shouldDownloadCovers: false,
  shouldDownloadSubtitles: false,
  shouldDownloadSlideshowImages: false,
  proxyCountryCode: "None"
}')

RESP_FILE="$(mktemp)"
trap 'rm -f "$RESP_FILE"' EXIT
curl -sS -X POST \
  "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token=${APIFY_API_TOKEN}&timeout=240" \
  -H "Content-Type: application/json" -d "$PAYLOAD" -o "$RESP_FILE"

jq -e 'type == "array"' "$RESP_FILE" >/dev/null 2>&1 || {
  echo "FATAL: Apify response is not an array:" >&2; head -c 400 "$RESP_FILE" >&2; echo >&2; exit 2; }

# ── append deduped, one compact JSON object per line ──────────────────────────
# Rows are re-serialised because the previous scrape wrote raw newlines inside strings,
# and the analyzer silently drops every line it cannot parse.
python3 - "$RESP_FILE" "$LIB/raw-$NICHE.jsonl" <<'PY'
import json, sys, pathlib

resp_path, raw_path = sys.argv[1], pathlib.Path(sys.argv[2])
items = json.load(open(resp_path))

seen, kept = set(), []
if raw_path.exists():
    buf = ''
    for line in raw_path.read_text(errors='replace').splitlines():
        buf = (buf + line) if buf else line
        try:
            row = json.loads(buf, strict=False)
        except json.JSONDecodeError:
            continue        # row spans multiple physical lines; keep accumulating
        buf = ''
        rid = row.get('id')
        if rid and rid not in seen:
            seen.add(rid)
            kept.append(row)

added = 0
for it in items:
    rid = it.get('id')
    if not rid or rid in seen:
        continue
    seen.add(rid)
    kept.append(it)
    added += 1

with open(raw_path, 'w') as f:
    for row in kept:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

print(f'RAW scraped={len(items)} added={added} total={len(kept)} -> {raw_path.name}')
PY

# ── rebuild pattern files, preserving per-card usage history ─────────────────
python3 - "$LIB" "$ANALYZER" <<'PY'
import json, pathlib, runpy, sys

lib = pathlib.Path(sys.argv[1]); analyzer = sys.argv[2]

# Snapshot everything the analyzer does not know about. body_texts matter most: the
# library-filler writes them into pattern-card-<lang>.jsonl only, and the analyzer
# rewrites every family file from raw — so without this merge a mining pass blanks the
# copy that larry reads and the loop dies with "library entry has only 0 body_texts".
history = {}
for p in lib.glob('pattern-*.jsonl'):
    for line in p.read_text(errors='replace').splitlines():
        try:
            e = json.loads(line, strict=False)
        except json.JSONDecodeError:
            continue
        sid = e.get('source_id')
        if not sid:
            continue
        prev = history.setdefault(sid, {'lastUsed': None, 'status': 'active', 'body_texts': []})
        if e.get('lastUsed') is not None:
            prev['lastUsed'] = e['lastUsed']
        if e.get('status') and e['status'] != 'active':
            prev['status'] = e['status']
        texts = [t for t in (e.get('body_texts') or []) if str(t).strip()]
        if len(texts) > len(prev['body_texts']):
            prev['body_texts'] = e['body_texts']

sys.argv = [analyzer]
runpy.run_path(analyzer, run_name='__main__')

restored = 0
for p in lib.glob('pattern-*.jsonl'):
    rows = []
    for line in p.read_text(errors='replace').splitlines():
        try:
            e = json.loads(line, strict=False)
        except json.JSONDecodeError:
            continue
        h = history.get(e.get('source_id'))
        if h:
            touched = False
            if h['lastUsed'] is not None or h['status'] != 'active':
                e['lastUsed'] = h['lastUsed']
                e['status'] = h['status']
                touched = True
            if h['body_texts'] and not [t for t in (e.get('body_texts') or []) if str(t).strip()]:
                e['body_texts'] = h['body_texts']
                touched = True
            restored += 1 if touched else 0
        rows.append(e)
    with open(p, 'w') as f:
        for e in rows:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
print(f'HISTORY restored on {restored} cards')
PY

echo "$NICHE" > "$ROTATION_FILE"
python3 - "$LIB/.scrape-runs.json" "$NICHE" <<'PY'
import json, pathlib, sys, time
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text()) if p.exists() else {}
d[sys.argv[2]] = {'last_mined_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
p.write_text(json.dumps(d, ensure_ascii=False, indent=2))
print('MINE OK', sys.argv[2])
PY
