#!/usr/bin/env python3
"""
account-burn-detector — Shalev 10-video burn test, but using anicca-socials snapshot
instead of Apify (which is rate-limited).

Logic:
1. Read ~/.openclaw/skills/anicca-socials/state/socials_latest.json
2. For each handle with views_7d < 10 AND posts_7d >= 5: classify as SHADOWBAN_BURN
3. Match handle → persona slug → factory cron jobs (via personas.json)
4. `openclaw cron disable <id>` for matched crons (auto-shutdown)
5. Append to ~/anicca-monk-factory/accounts/burn/burned.jsonl
6. Slack message with verdict table + disabled-cron list
"""
import json, os, sys, subprocess, datetime, urllib.request
from pathlib import Path

ROOT = Path(os.path.expanduser('~/anicca-monk-factory'))
SOCIALS = Path(os.path.expanduser('~/.openclaw/skills/anicca-socials/state/socials_latest.json'))

if not SOCIALS.exists():
    print(f'❌ socials snapshot missing: {SOCIALS}'); sys.exit(2)

# Load env
ENV = {}
for path in [ROOT / '.env', Path(os.path.expanduser('~/.openclaw/.env'))]:
    if path.exists():
        for ln in path.read_text().splitlines():
            if '=' in ln and not ln.lstrip().startswith('#'):
                k, _, v = ln.partition('=')
                ENV[k.strip()] = v.strip().strip('"').strip("'")

SLACK_TOKEN = ENV.get('SLACK_BOT_TOKEN') or os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = ENV.get('SLACK_CHANNEL_ID') or os.environ.get('SLACK_CHANNEL_ID', '{{profile.channels.reportChannel}}')

snap = json.loads(SOCIALS.read_text())
accounts = snap['accounts']

# Burn rule: views_7d < 10 AND posts_7d >= 5 (more strict than 2-post minimum to allow new accounts to warm up)
burned = [a for a in accounts if a['views_7d'] < 10 and a['posts_7d'] >= 5]
watch = [a for a in accounts if 10 <= a['views_7d'] < 100 and a['posts_7d'] >= 5]
healthy = [a for a in accounts if a['views_7d'] >= 100]

print(f'📊 socials snapshot {snap["window_start"]} → {snap["window_end"]}')
print(f'   burned: {len(burned)}, watch: {len(watch)}, healthy: {len(healthy)}')

# Map handle → cron job IDs via openclaw cron list + heuristic
def list_crons():
    try:
        r = subprocess.run(['openclaw', 'cron', 'list', '--json'], capture_output=True, text=True, timeout=20)
        return json.loads(r.stdout).get('jobs', [])
    except Exception as e:
        print(f'   warn: openclaw cron list failed: {e}')
        return []

all_crons = list_crons()

def crons_for_handle(handle):
    """Match handle to cron jobs by name substring."""
    h = handle.lstrip('@').lower()
    matches = []
    for c in all_crons:
        name = (c.get('name') or '').lower()
        msg = (c.get('payload', {}).get('message', '') or '').lower()
        if h in name or h in msg:
            matches.append(c)
    return matches

# Process burned
disabled_crons = []
burn_log = ROOT / 'accounts' / 'burn' / 'burned.jsonl'
burn_log.parent.mkdir(parents=True, exist_ok=True)
ts = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

for a in burned:
    handle = a['handle']
    crons = crons_for_handle(handle)
    cron_ids = []
    for c in crons:
        cid = c['id']
        if not c.get('enabled'): continue
        try:
            subprocess.run(['openclaw', 'cron', 'disable', cid], capture_output=True, text=True, timeout=15)
            cron_ids.append({'id': cid, 'name': c.get('name', '?')})
            print(f'   🛑 disabled cron {c.get("name", cid)} for @{handle}')
        except Exception as e:
            print(f'   warn: disable cron {cid} failed: {e}')
    disabled_crons.extend(cron_ids)

    burn_log.open('a').write(json.dumps({
        'platform': a['platform'],
        'handle': '@' + handle,
        'burned_at': ts,
        'window': f'{snap["window_start"]} → {snap["window_end"]}',
        'posts_7d': a['posts_7d'],
        'views_7d': a['views_7d'],
        'reason': f'< 10 views in 7d with {a["posts_7d"]} posts (anicca-socials snapshot)',
        'disabled_crons': cron_ids,
    }, ensure_ascii=False) + '\n')

# Slack message
if SLACK_TOKEN:
    lines = [f'*🔥 Weekly Burn-Test (anicca-socials based)*']
    lines.append(f'_window: {snap["window_start"]} → {snap["window_end"]}_')
    lines.append('')
    lines.append(f'*Verdicts:* {len(burned)} burn · {len(watch)} watch · {len(healthy)} healthy')
    lines.append('')

    if burned:
        lines.append(f'*🔴 BURN ({len(burned)}) — auto-disabled crons:*')
        lines.append('```')
        for a in burned:
            lines.append(f'@{a["handle"]:<22} {a["platform"]:<22} {a["posts_7d"]:>3} posts → {a["views_7d"]} views')
        lines.append('```')

    if disabled_crons:
        lines.append('')
        lines.append(f'*🛑 Disabled {len(disabled_crons)} cron job(s):*')
        lines.append('```')
        for c in disabled_crons:
            lines.append(f'• {c["name"]} ({c["id"]})')
        lines.append('```')

    if watch:
        lines.append('')
        lines.append(f'*🟡 watch ({len(watch)}):*')
        lines.append('```')
        for a in watch[:10]:
            lines.append(f'@{a["handle"]:<22} {a["views_7d"]} views / {a["posts_7d"]} posts')
        lines.append('```')

    text = '\n'.join(lines)
    try:
        req = urllib.request.Request('https://slack.com/api/chat.postMessage',
            data=json.dumps({'channel': SLACK_CHANNEL, 'text': text, 'mrkdwn': True}).encode(),
            headers={'Content-Type': 'application/json; charset=utf-8', 'Authorization': f'Bearer {SLACK_TOKEN}'})
        r = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        print(f'   slack ok={r.get("ok")} ts={r.get("ts")}')
    except Exception as e:
        print(f'   slack failed: {e}')
else:
    print('   warn: no SLACK_BOT_TOKEN, skipping slack')

print(f'\n✅ burn-test done')
print(f'   burned: {len(burned)}')
print(f'   watch: {len(watch)}')
print(f'   healthy: {len(healthy)}')
print(f'   disabled crons: {len(disabled_crons)}')
print(f'   burn log: {burn_log}')
