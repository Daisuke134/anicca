#!/usr/bin/env bash
# Stage 1: DISCOVER — find AI UGC viral videos (per Dais 8-step v2, 2026-05-06).
#
# Strategy:
#   1) Apify clockworks/tiktok-scraper if balance ≥ $0.50
#   2) yt-dlp on seed_ai_handles.txt (free, returns view counts as JSON)
#   3) NO local-references fallback (Dais NG — must always download fresh viral)
#
# Output: <run_dir>/candidates.json (top 5 by view, sorted desc)
set -euo pipefail
NICHE_KW="${1:-ai viral}"
LANG_ARG="${2:?lang required}"
RUN_DIR="${3:?run_dir required}"

ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

echo ""
echo "─── Stage 1: DISCOVER (AI UGC viral, v4) ───"
echo "  niche='$NICHE_KW' lang=$LANG_ARG"

# ── Stage 0: handle discovery via nitter (X mirror) ──────────────────
SCRIPT_DIR="$(dirname "$0")"
if [ -x "$SCRIPT_DIR/00_handle_discovery.sh" ]; then
  echo "  → Stage 0: handle discovery..."
  bash "$SCRIPT_DIR/00_handle_discovery.sh" 2>&1 | sed 's/^/    /' || true
fi

# ── Apify pre-flight ─────────────────────────────────────────────────
USE_APIFY=0
if [ -n "${APIFY_TOKEN:-}" ]; then
  REM=$(curl -sS "https://api.apify.com/v2/users/me?token=$APIFY_TOKEN" 2>/dev/null \
    | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin).get('data', {})
    plan = d.get('plan', {}) or {}
    usage = d.get('usage', {}) or {}
    limit = float(plan.get('monthlyUsageHardLimit') or plan.get('availableProxyUSD') or 0)
    used = float(usage.get('monthlyUsageUsd') or 0)
    print(round(max(limit - used, 0), 2))
except Exception:
    print(0)" 2>/dev/null || echo '0')
  echo "  Apify wallet remaining: \$${REM}"
  python3 -c "import sys; sys.exit(0 if float('${REM}') >= 0.50 else 1)" 2>/dev/null && USE_APIFY=1
fi

# ── Path A: Apify ────────────────────────────────────────────────────
if [ "$USE_APIFY" = "1" ]; then
  echo "  → Path A: Apify"
  python3 - <<PY "$NICHE_KW" "$LANG_ARG" "$RUN_DIR" "$APIFY_TOKEN" && exit 0 || true
import json, os, re, sys, urllib.request, datetime
niche_kw, lang, run_dir, apify_token = sys.argv[1:5]

AI_HASHTAGS = ['aiugc','aigenerated','aishorts','aicharacter','aifilm',
               'aitalking','aianimation','midjourneyai','veo3','sora',
               'klingai','generativeai','pika','aivideo','aiart']
seed_path = os.path.expanduser('~/anicca-monk-factory/state/seed_ai_handles.txt')
SEED = []
if os.path.exists(seed_path):
    SEED = [ln.strip() for ln in open(seed_path) if ln.strip() and not ln.startswith('#')]
payload = {'profiles': SEED, 'hashtags': AI_HASHTAGS,
           'searchQueries': ['ai ugc','made with ai','ai short film', niche_kw],
           'resultsPerPage': 50, 'shouldDownloadVideos': False}
url = f'https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token={apify_token}'
req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                              headers={'Content-Type': 'application/json'})
try:
    posts = json.loads(urllib.request.urlopen(req, timeout=300).read().decode())
except Exception as e:
    print(f'  ❌ apify error: {e}'); sys.exit(99)

seen, deduped = set(), []
for p in posts:
    pid = p.get('id')
    if pid and pid not in seen:
        seen.add(pid); deduped.append(p)
cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=60)).timestamp()
def ts(p):
    try: return datetime.datetime.fromisoformat(p['createTimeISO'].replace('Z','+00:00')).timestamp()
    except: return 0
ai_re = re.compile(r'\\b(made with|prompt|ai generated|veo|sora|kling|midjourney|pika)\\b', re.I)
def is_ai(p):
    if ai_re.search(p.get('text','') or ''): return True
    if (p.get('authorMeta') or {}).get('name','') in SEED: return True
    return any(t.get('name','').lower() in AI_HASHTAGS for t in (p.get('hashtags') or []))
filtered = [p for p in deduped if (p.get('playCount') or 0) > 100000 and ts(p) > cutoff and is_ai(p)]
filtered.sort(key=lambda x: x.get('playCount',0), reverse=True)
top = filtered[:5]
cands = []
for p in top:
    cands.append({
        'id': p.get('id'), 'web_video_url': p.get('webVideoUrl'),
        'video_download_url': (p.get('mediaUrls') or [None])[0] or p.get('videoUrl') or '',
        'caption': (p.get('text') or '')[:500],
        'play_count': p.get('playCount',0), 'digg_count': p.get('diggCount',0),
        'duration_sec': (p.get('videoMeta') or {}).get('duration',0),
        'author_handle': (p.get('authorMeta') or {}).get('name',''),
        'author_followers': (p.get('authorMeta') or {}).get('fans',0),
        'author_signature': (p.get('authorMeta') or {}).get('signature',''),
        'create_time': p.get('createTimeISO'),
        'hashtags': [h.get('name') for h in (p.get('hashtags') or [])],
    })
output = {'niche': niche_kw, 'lang': lang, 'source': 'apify',
          'searched_at': datetime.datetime.utcnow().isoformat()+'Z',
          'total_results': len(deduped), 'filtered_results': len(filtered),
          'candidates': cands}
json.dump(output, open(f'{run_dir}/candidates.json','w'), ensure_ascii=False, indent=2)
print(f'  apify→ {len(deduped)} posts, {len(filtered)} AI viral, top {len(cands)}')
for i,c in enumerate(cands,1):
    print(f'    {i}. {c["play_count"]:,} views @{c["author_handle"]} ({c["author_followers"]:,} fans) — {c["caption"][:60]}')
if not cands: sys.exit(99)
PY
  echo "  ⚠ Apify failed/empty, falling to Path B (yt-dlp)"
fi

# ─── Path C: YouTube ytsearch (autonomous, free, no seed list) ──────
echo "  → Path C: yt-dlp ytsearch on YouTube (autonomous AI-niche discovery)"
which yt-dlp >/dev/null || { echo "❌ yt-dlp not installed"; exit 7; }
mkdir -p "$RUN_DIR"
TMP="$RUN_DIR/candidates_ytdlp.jsonl"
touch "$TMP"

YT_QUERIES=(
  "ai monk wisdom viral shorts"
  "ai philosopher viral shorts"
  "ai motivational quotes viral shorts"
  "ai woman podcast viral shorts"
  "ai dating advice viral shorts"
  "ai narrator wisdom shorts"
  "veo3 ai short viral"
  "ai influencer viral shorts"
  "buddhist parable ai animation"
  "stoic motivation ai shorts"
)
for Q in "${YT_QUERIES[@]}"; do
  yt-dlp --flat-playlist --no-warnings -j --playlist-end 15 \
    --default-search "ytsearch" "ytsearch15:$Q" 2>/dev/null \
    | python3 -c "
import json, sys, re
for ln in sys.stdin:
    try:
        d = json.loads(ln)
        v = int(d.get('view_count') or 0)
        dur = int(d.get('duration') or 0)
        if v < 200000 or not dur or dur < 25 or dur > 180: continue
        # Normalize handle: prefer @handle from channel_url, else uploader, lowercase
        ch_url = d.get('channel_url') or d.get('uploader_url') or ''
        m = re.search(r'@([A-Za-z0-9._-]+)', ch_url)
        handle = (m.group(1) if m else (d.get('uploader_id','') or d.get('channel','')).lstrip('@')).lower()
        if not handle: continue
        out = {
          'id': d.get('id',''),
          'web_video_url': d.get('url') or d.get('webpage_url') or f\"https://www.youtube.com/watch?v={d.get('id','')}\",
          'video_download_url': '',
          'caption': (d.get('title') or d.get('description') or '')[:500],
          'play_count': v,
          'digg_count': 0,
          'duration_sec': dur,
          'author_handle': handle,
          'author_followers': int(d.get('channel_follower_count') or 0),
          'author_signature': '',
          'create_time': d.get('upload_date') or '',
          'hashtags': [],
          'platform': 'youtube',
        }
        print(json.dumps(out, ensure_ascii=False))
    except Exception:
        pass
" >> "$TMP" 2>/dev/null || true
done
NEW_C=$(wc -l < "$TMP" | tr -d ' ')
echo "    Path C ytsearch produced $NEW_C entries"

# ── Path B: yt-dlp on seed_ai_handles.txt (LEGACY, optional fallback) ─
SEED_FILE="$HOME/anicca-monk-factory/state/seed_ai_handles.txt"
if [ -f "$SEED_FILE" ] && [ -s "$SEED_FILE" ]; then
  echo "  → Path B (legacy): yt-dlp on seed_ai_handles.txt — append to ytsearch results"
  # Skip if seed_ai_handles.txt is marked deprecated
  if head -3 "$SEED_FILE" | grep -qi "deprecated\|disabled" 2>/dev/null; then
    echo "    seed file marked deprecated — skipping Path B"
    SEED_FILE=""
  fi
else
  echo "  → Path B skipped (no seed_ai_handles.txt — autonomous mode)"
  SEED_FILE=""
fi

# For each handle in seed (LEGACY only — only if SEED_FILE non-empty), fetch metadata via yt-dlp
if [ -n "$SEED_FILE" ]; then
  while IFS= read -r LN; do
    LN=$(echo "$LN" | tr -d '[:space:]')
    [ -z "$LN" ] && continue
    case "$LN" in '#'*) continue ;; esac
    mkdir -p "$(dirname "$TMP")"
    [ -f "$TMP" ] || touch "$TMP"
    echo "  yt-dlp @$LN ..."
    yt-dlp --flat-playlist --no-warnings -j --playlist-end 20 \
      "https://www.tiktok.com/@$LN" 2>/dev/null \
      | python3 -c "
import json, sys
for ln in sys.stdin:
    try:
        d = json.loads(ln)
        out = {
          'id': d.get('id') or d.get('url','').split('/')[-1],
          'web_video_url': d.get('url') or d.get('webpage_url') or f'https://www.tiktok.com/@${LN}/video/{d.get(\"id\",\"\")}',
          'video_download_url': '',
          'caption': (d.get('title') or d.get('description') or '')[:500],
          'play_count': int(d.get('view_count') or 0),
          'digg_count': int(d.get('like_count') or 0),
          'duration_sec': int(d.get('duration') or 0),
          'author_handle': '$LN',
          'author_followers': int(d.get('uploader_follower_count') or 0),
          'author_signature': '',
          'create_time': d.get('upload_date') or '',
          'hashtags': [],
          'platform': 'tiktok',
        }
        print(json.dumps(out, ensure_ascii=False))
    except Exception:
        pass
" >> "$TMP" 2>/dev/null || echo "    yt-dlp failed for @$LN, skipping"
  done < "$SEED_FILE"
fi

# Build candidates.json: dedupe + EXCLUDE already-spawned + group by author + pick TOP account's top 3-5
python3 - <<PY "$RUN_DIR" "$NICHE_KW" "$LANG_ARG" "$ROOT"
import json, sys, os, datetime
run_dir, niche, lang, root = sys.argv[1:5]

cands = []
seen = set()
for ln in open(f'{run_dir}/candidates_ytdlp.jsonl'):
    if not ln.strip(): continue
    try: c = json.loads(ln)
    except: continue
    if c['id'] in seen: continue
    seen.add(c['id']); cands.append(c)

# Exclude already-spawned source ids (per Dais: never copy same video twice)
already_path = f'{root}/state/already_spawned_source_ids.txt'
already = set()
if os.path.exists(already_path):
    already = {ln.strip() for ln in open(already_path) if ln.strip()}
cands = [c for c in cands if c['id'] not in already]

# Exclude already-spawned source AUTHORS — canonical source = each factory's SOURCE.json
import glob
spawned_authors = set()
for src_path in glob.glob(os.path.expanduser('~/.openclaw/skills/*-factory/SOURCE.json')):
    try:
        d = json.load(open(src_path))
        h = (d.get('source_handle') or '').strip().lower()
        if h: spawned_authors.add(h)
    except Exception:
        pass
# Legacy fallback: read flat file too (older spawns)
already_authors_path = f'{root}/state/already_spawned_authors.txt'
if os.path.exists(already_authors_path):
    spawned_authors |= {ln.strip().lower() for ln in open(already_authors_path) if ln.strip()}
print(f'  🚫 excluding {len(spawned_authors)} already-spawned source handles: {sorted(spawned_authors)}')
cands = [c for c in cands if c.get('author_handle','').lower() not in spawned_authors]

# Group by author, compute total views per author
by_author = {}
for c in cands:
    h = c.get('author_handle','').lower()
    if not h: continue
    by_author.setdefault(h, []).append(c)

# Pick the author with the highest TOP video views (proxy for account virality)
if not by_author:
    print('  ❌ no candidates left after dedupe — try expanding seed_ai_handles.txt')
    json.dump({'niche':niche,'lang':lang,'source':'yt-dlp','candidates':[],
               'note':'all viable candidates already spawned or excluded'},
              open(f'{run_dir}/candidates.json','w'), ensure_ascii=False, indent=2)
    sys.exit(8)

ranked_authors = sorted(by_author.items(),
                        key=lambda kv: max(c.get('play_count',0) for c in kv[1]),
                        reverse=True)
top_author, top_videos = ranked_authors[0]
top_videos.sort(key=lambda x: x.get('play_count',0), reverse=True)
picked_videos = top_videos[:5]   # top 5 from this account

output = {
    'niche': niche, 'lang': lang, 'source': 'yt-dlp+nitter',
    'searched_at': datetime.datetime.utcnow().isoformat()+'Z',
    'total_results': len(cands),
    'top_author': top_author,
    'top_author_video_count': len(top_videos),
    'top_author_max_views': max(c.get('play_count',0) for c in picked_videos),
    'candidates': picked_videos,
    'note': f'TOP account: @{top_author} — picked top {len(picked_videos)} videos for spawn',
}
json.dump(output, open(f'{run_dir}/candidates.json','w'), ensure_ascii=False, indent=2)
print(f'  → TOP account: @{top_author}  ({len(top_videos)} videos in pool)')
for i,c in enumerate(picked_videos,1):
    print(f'    {i}. {c["play_count"]:,} views  {c["duration_sec"]}s  — {c["caption"][:80]}')
if not picked_videos:
    print('  ❌ no candidates'); sys.exit(8)
PY
