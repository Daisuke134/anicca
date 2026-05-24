#!/usr/bin/env python3
"""anicca-socials/slack.py — post latest snapshot summary to Slack."""
import os, json, urllib.request, sys, pathlib

token = os.environ.get('SLACK_BOT_TOKEN')
channel = os.environ.get('SLACK_CHANNEL_ID', '{{profile.channels.reportChannel}}')
if not token:
    print('ERR: SLACK_BOT_TOKEN missing'); sys.exit(2)

skill_dir = pathlib.Path(os.environ.get('SKILL_DIR', os.path.expanduser('~/.openclaw/skills/anicca-socials')))
snap = json.load(open(skill_dir / 'state' / 'socials_latest.json'))

accs = snap['accounts']
totals = snap['totals']
dead = [a for a in accs if a['views_7d'] < 10 and a['posts_7d'] >= 2]
alive = [a for a in accs if a['views_7d'] >= 10]
alive.sort(key=lambda a: -a['views_7d'])
viral = [a for a in accs if a['avg_views'] >= 1000]

lines = [f'*📊 Anicca Socials — daily report*', '']
lines.append(f'_window: {snap["window_start"]} → {snap["window_end"]}, {totals["weekly_posts"]} posts across {totals["accounts"]} accounts_')
lines.append(f'_total: {totals["weekly_views"]:,} views · {totals["weekly_likes"]:,} likes · {totals["weekly_comments"]:,} comments_')
lines.append('')

lines.append('*🟢 Alive accounts (views > 0):*')
lines.append('```')
lines.append(f'{"plat":<22}{"handle":<22}{"posts":>6}{"views":>9}{"avg":>7}{"eng%":>7}')
for a in alive:
    lines.append(f'{a["platform"]:<22}{a["handle"]:<22}{a["posts_7d"]:>6}{a["views_7d"]:>9}{a["avg_views"]:>7.0f}{a["engagement_rate"]:>7.2f}')
lines.append('```')
lines.append('')

if dead:
    lines.append(f'*💀 DEAD accounts ({len(dead)}, < 10 views with 2+ posts) — candidates for SHUTDOWN:*')
    lines.append('```')
    for a in dead:
        lines.append(f'❌ {a["platform"]:<22}@{a["handle"]:<22}{a["posts_7d"]:>4} posts → {a["views_7d"]} views')
    lines.append('```')
    lines.append('')

# Headlines
hl = []
if alive:
    top = alive[0]
    hl.append(f'• 🔥 best: {top["platform"]} @{top["handle"]} → {top["views_7d"]:,} views/wk ({top["avg_views"]:.0f} avg)')
if viral:
    hl.append(f'• ⚡ viral (avg ≥1k): {", ".join("@"+v["handle"] for v in viral)}')
if dead:
    plat_dead = {}
    for a in dead:
        plat_dead.setdefault(a['platform'], 0)
        plat_dead[a['platform']] += 1
    parts = ', '.join(f'{p}: {n}' for p, n in plat_dead.items())
    hl.append(f'• 💀 {len(dead)} dead accounts ({parts}) — see `account-burn-detector`')

if hl:
    lines.append('*Headlines:*')
    lines.extend(hl)

text = '\n'.join(lines)
req = urllib.request.Request('https://slack.com/api/chat.postMessage',
    data=json.dumps({'channel': channel, 'text': text, 'mrkdwn': True}).encode(),
    headers={'Content-Type': 'application/json; charset=utf-8', 'Authorization': f'Bearer {token}'})
resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
print(f'   slack ok={resp.get("ok")} ts={resp.get("ts")} err={resp.get("error")}')
if not resp.get('ok'): sys.exit(4)
