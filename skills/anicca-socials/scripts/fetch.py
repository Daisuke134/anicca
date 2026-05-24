#!/usr/bin/env python3
"""
anicca-socials/fetch.py — pull Postiz per-account 7-day analytics.
Output: state/socials_<date>.json + state/socials_latest.json
"""
import os, json, urllib.request, datetime, sys, pathlib
from collections import defaultdict

KEY = os.environ.get('POSTIZ_API_KEY')
if not KEY:
    print('ERR: POSTIZ_API_KEY missing'); sys.exit(2)

BASE = 'https://api.postiz.com/public/v1'
SKILL_DIR = pathlib.Path(os.environ.get('SKILL_DIR', os.path.expanduser('~/.openclaw/skills/anicca-socials')))
STATE = SKILL_DIR / 'state'
STATE.mkdir(parents=True, exist_ok=True)

def api(path):
    req = urllib.request.Request(f'{BASE}{path}', headers={'Authorization': KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {'_err': str(e)}

def num(v):
    try: return float(v)
    except: return 0

now = datetime.datetime.now(datetime.UTC)
week_ago = now - datetime.timedelta(days=7)
# Postiz /posts requires full ISO 8601 datetimes, not bare YYYY-MM-DD.
start = week_ago.strftime('%Y-%m-%dT00:00:00')
end = now.strftime('%Y-%m-%dT%H:%M:%S')

print(f'[fetch] window {start} → {end}')

# 1. integrations (iterate ALL — every account must appear in output)
ints = api('/integrations')
if isinstance(ints, dict) and ints.get('_err'):
    print(f'integrations err: {ints["_err"]}'); sys.exit(3)
print(f'   integrations: {len(ints)}')

# 2. posts
pres = api(f'/posts?startDate={start}&endDate={end}')
posts = pres.get('posts', []) if isinstance(pres, dict) else []
print(f'   posts: {len(posts)}')

# 3. group ONLY published posts by account (DRAFT/ERROR have no analytics)
pub_by_acc = defaultdict(list)
for p in posts:
    if p.get('state') != 'PUBLISHED':
        continue
    ig = p.get('integration') or {}
    ig_id = ig.get('id')
    if ig_id: pub_by_acc[ig_id].append(p)
print(f'   integrations with PUBLISHED posts: {len(pub_by_acc)}')

VIEW_LABELS = ('view', 'impression', 'reach', 'play')
LIKE_LABELS = ('like', 'reaction', 'favorite', 'digg')
COMMENT_LABELS = ('comment', 'repl')

# 4. per-post analytics for every integration
results = []
for inteq in ints:
    ig_id = inteq['id']
    handle = inteq.get('profile', '?')
    platform = inteq.get('identifier', '?')
    name = inteq.get('name', '?')
    ig_posts = pub_by_acc.get(ig_id, [])

    tv = tl = tc = 0
    n_with_data = 0
    for p in ig_posts:
        ana = api(f'/analytics/post/{p["id"]}')
        # Only a non-empty list carries real analytics. [] / {"missing":true}
        # means the platform (e.g. TikTok) has no Postiz analytics — that is
        # NOT a failure and must NOT be reported as 0-views-as-if-broken.
        if not isinstance(ana, list) or not ana: continue
        had = False
        for item in ana:
            if not isinstance(item, dict): continue
            label = (item.get('label') or '').lower()
            data_arr = item.get('data') or []
            total = sum(num(d.get('total', 0)) for d in data_arr)
            if total: had = True
            if any(k in label for k in VIEW_LABELS):
                tv += total
            elif any(k in label for k in LIKE_LABELS):
                tl += total
            elif any(k in label for k in COMMENT_LABELS):
                tc += total
        if had: n_with_data += 1

    n = len(ig_posts)
    if n == 0:
        status = 'no_published_posts'
    elif n_with_data == 0:
        status = 'no_analytics_from_postiz'
    else:
        status = 'ok'
    results.append({
        'platform': platform,
        'handle': handle,
        'name': name,
        'posts_7d': n,
        'posts_with_data': n_with_data,
        'views_7d': int(tv),
        'likes_7d': int(tl),
        'comments_7d': int(tc),
        'avg_views': round(tv / n, 1) if n else 0,
        'engagement_rate': round((tl + tc) / max(tv, 1) * 100, 2) if tv else 0,
        'status': status,
    })

results.sort(key=lambda r: (-r['views_7d'], -(r['likes_7d'] + r['comments_7d'])))

# "dead" only counts accounts where Postiz HAS analytics but views are ~0.
# Accounts whose platform returns no analytics (TikTok) are NOT "dead".
dead = [r['handle'] for r in results
        if r['status'] == 'ok' and r['views_7d'] < 10 and r['posts_7d'] >= 2]
viral = [r['handle'] for r in results if r['avg_views'] >= 1000]
weekly_posts = sum(r['posts_7d'] for r in results)

snapshot = {
    'updated_at': now.isoformat(),
    'window_start': start[:10],
    'window_end': end[:10],
    'totals': {
        'accounts': len(results),
        'alive_accounts': sum(1 for r in results if r['views_7d'] > 0),
        'accounts_with_data': sum(1 for r in results if r['status'] == 'ok'),
        'accounts_no_published': sum(1 for r in results if r['status'] == 'no_published_posts'),
        'accounts_no_analytics': sum(1 for r in results if r['status'] == 'no_analytics_from_postiz'),
        'dead_accounts': len(dead),
        'weekly_views': sum(r['views_7d'] for r in results),
        'weekly_likes': sum(r['likes_7d'] for r in results),
        'weekly_comments': sum(r['comments_7d'] for r in results),
        'weekly_posts': weekly_posts,
    },
    'accounts': results,
    'dead_handles': dead,
    'viral_handles': viral,
}

date_tag = now.strftime('%Y%m%d')
dated_path = STATE / f'socials_{date_tag}.json'
latest_path = STATE / 'socials_latest.json'
dated_path.write_text(json.dumps(snapshot, indent=2))
latest_path.write_text(json.dumps(snapshot, indent=2))
print(f'   wrote {latest_path}')
print(f'   alive={snapshot["totals"]["alive_accounts"]}/{snapshot["totals"]["accounts"]}, dead={len(dead)}, weekly_views={snapshot["totals"]["weekly_views"]}')
