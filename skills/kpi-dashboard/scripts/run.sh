#!/usr/bin/env bash
# KPI Dashboard — daily aggregation + anomaly detection.
set -euo pipefail
TAG="${1:-daily}"
ROOT="$HOME/anicca-monk-factory"
STATE="$ROOT/state"
mkdir -p "$STATE"

set -a; . "$ROOT/.env"; set +a

DATE_TAG=$(date +%Y%m%d)
KPI_JSON="$STATE/kpi_${DATE_TAG}.json"
KPI_MD="$STATE/kpi_${DATE_TAG}.md"

echo "═══════════════════════════════════════════════"
echo "  KPI Dashboard — $DATE_TAG"
echo "  $(date)"
echo "═══════════════════════════════════════════════"

PERSONAS_JSON="$ROOT/personas.json"
[ -f "$PERSONAS_JSON" ] || { echo "❌ $PERSONAS_JSON missing"; exit 2; }

python3 - <<'PY' "$KPI_JSON" "$KPI_MD" "$PERSONAS_JSON"
import json, os, sys, urllib.request, urllib.parse, urllib.error, datetime, base64

kpi_json, kpi_md, personas_path = sys.argv[1:4]
result = {
    'ts': datetime.datetime.utcnow().isoformat() + 'Z',
    'stripe': None, 'postiz': None, 'personas': [], 'supabase': None,
    'alerts': []
}

# ─── 1. Stripe ───
stripe_key = os.environ.get('STRIPE_SECRET_KEY')
if stripe_key:
    try:
        # yesterday's charges
        yday_start = int((datetime.datetime.utcnow() - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0).timestamp())
        yday_end = int(datetime.datetime.utcnow().replace(hour=0, minute=0, second=0).timestamp())

        url = f'https://api.stripe.com/v1/charges?created[gte]={yday_start}&created[lt]={yday_end}&limit=100'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {stripe_key}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            charges = json.loads(r.read().decode())
        succ = [c for c in charges['data'] if c.get('status') == 'succeeded']
        revenue = sum(c['amount'] for c in succ) / 100.0

        # active subscriptions for MRR
        url2 = 'https://api.stripe.com/v1/subscriptions?status=active&limit=100'
        req2 = urllib.request.Request(url2, headers={'Authorization': f'Bearer {stripe_key}'})
        with urllib.request.urlopen(req2, timeout=30) as r2:
            subs = json.loads(r2.read().decode())
        mrr = 0.0
        for s in subs['data']:
            for it in s.get('items', {}).get('data', []):
                price = it.get('price', {})
                if price.get('recurring', {}).get('interval') == 'month':
                    mrr += (price.get('unit_amount', 0) * it.get('quantity', 1)) / 100.0

        result['stripe'] = {
            'yesterday_revenue_usd': round(revenue, 2),
            'yesterday_count': len(succ),
            'mrr_usd': round(mrr, 2),
            'active_subs': len(subs['data']),
        }
        print(f'  💰 Stripe: ${revenue:.2f} yesterday, MRR ${mrr:.2f}')
    except Exception as e:
        print(f'  ❌ Stripe: {e}')
        result['alerts'].append({'severity': 'medium', 'message': f'Stripe API failed: {e}'})

# ─── 2. Postiz (from local posted.jsonl) ───
try:
    posted_lines = open(os.path.expanduser('~/anicca-monk-factory/state/posted.jsonl')).readlines()
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat() + 'Z'
    recent = []
    for l in posted_lines:
        l = l.strip()
        if not l: continue
        try:
            obj = json.loads(l)
        except: continue
        # Skip legacy non-dict lines (raw API responses) — only dict entries with 'ts' count
        if not isinstance(obj, dict): continue
        if obj.get('ts', '') > cutoff:
            recent.append(obj)
    failed = [r for r in recent if 'error' in str(r.get('response', '')).lower()[:200]]
    result['postiz'] = {'posted_24h': len(recent), 'failed_24h': len(failed)}
    print(f'  📤 Postiz: {len(recent)} posted, {len(failed)} failed (24h)')
    if len(failed) > 0 and len(failed) / max(len(recent), 1) > 0.1:
        result['alerts'].append({'severity': 'high', 'message': f'Postiz fail rate {len(failed)}/{len(recent)} > 10%'})
except FileNotFoundError:
    result['postiz'] = {'posted_24h': 0, 'failed_24h': 0}
    print('  📤 Postiz: no posted.jsonl yet')

# ─── 3. Apify per-persona ───
apify_token = os.environ.get('APIFY_TOKEN')
personas = json.load(open(personas_path))['personas']
if apify_token:
    for p in personas:
        slug = p['slug']
        tt_url = p.get('tiktok_url')
        if not tt_url: continue
        try:
            payload = {'profiles': [tt_url], 'resultsPerPage': 5,
                       'shouldDownloadVideos': False, 'shouldDownloadCovers': False}
            url = f'https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token={apify_token}'
            req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                          headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r:
                posts = json.loads(r.read().decode())
            if not posts:
                result['personas'].append({'slug': slug, 'followers': 0, 'recent_views': []})
                continue
            author = posts[0].get('authorMeta', {})
            followers = author.get('fans', 0)
            recent_views = [p.get('playCount', 0) for p in posts[:3]]
            result['personas'].append({
                'slug': slug,
                'followers': followers,
                'recent_views': recent_views,
                'last_post_views': recent_views[0] if recent_views else 0,
            })
            print(f'  👤 {slug}: {followers} followers, last 3 views: {recent_views}')

            # Anomaly: 2 consecutive posts < 100 views
            if len(recent_views) >= 2 and all(v < 100 for v in recent_views[:2]):
                result['alerts'].append({
                    'severity': 'high',
                    'message': f'{slug}: 2 consecutive posts < 100 views (shadowban/cold-start risk)'
                })
        except Exception as e:
            print(f'  ❌ Apify {slug}: {e}')

# ─── 4. Supabase ───
sb_url = os.environ.get('SUPABASE_URL')
sb_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
if sb_url and sb_key:
    try:
        # subscribers count
        req = urllib.request.Request(f'{sb_url}/rest/v1/subscribers?select=count',
                                      headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Prefer': 'count=exact'})
        with urllib.request.urlopen(req, timeout=15) as r:
            content_range = r.headers.get('content-range', '0-0/0')
            total_subs = int(content_range.split('/')[-1])
        # buyers count
        req = urllib.request.Request(f'{sb_url}/rest/v1/buyers?select=count',
                                      headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Prefer': 'count=exact'})
        with urllib.request.urlopen(req, timeout=15) as r:
            total_buyers = int(r.headers.get('content-range', '0-0/0').split('/')[-1])
        result['supabase'] = {'subscribers_total': total_subs, 'buyers_total': total_buyers}
        print(f'  📧 Supabase: {total_subs} subscribers, {total_buyers} buyers')
    except Exception as e:
        print(f'  ❌ Supabase: {e}')

# ─── 5. gpt-5-mini anomaly summarization ───
openai_key = os.environ.get('OPENAI_API_KEY')
ai_summary = ''
if openai_key:
    try:
        prompt = f'''You are an autonomous KPI watchdog for a TikTok-driven content business.

Today's snapshot:
{json.dumps(result, ensure_ascii=False, indent=2)}

In <80 words, give:
- a one-line headline
- top 1-2 ACTIONABLE things to do today (skip if all healthy)
Keep it tight and direct. Use emoji sparingly.'''
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps({'model': 'gpt-4o-mini', 'messages': [{'role':'user', 'content': prompt}], 'max_tokens': 300}).encode(),
            headers={'Authorization': f'Bearer {openai_key}', 'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            ai_summary = json.loads(r.read().decode())['choices'][0]['message']['content']
        print(f'\n🧠 AI summary:\n{ai_summary}\n')
    except Exception as e:
        print(f'  ❌ AI summary failed: {e}')

# Save JSON + MD
json.dump(result, open(kpi_json, 'w'), ensure_ascii=False, indent=2)

md_lines = [
    f'# KPI — {datetime.datetime.utcnow().strftime("%Y-%m-%d")}',
    '',
    '## Stripe',
    f'- Yesterday: ${result["stripe"]["yesterday_revenue_usd"]:.2f} ({result["stripe"]["yesterday_count"]} charges)' if result.get('stripe') else '- (Stripe data unavailable)',
    f'- MRR: ${result["stripe"]["mrr_usd"]:.2f} ({result["stripe"]["active_subs"]} active subs)' if result.get('stripe') else '',
    '',
    '## Distribution',
    f'- Postiz posted (24h): {result["postiz"]["posted_24h"]} (failed: {result["postiz"]["failed_24h"]})' if result.get('postiz') else '',
    '',
    '## Personas',
] + [f'- **{p["slug"]}**: {p["followers"]} followers, last 3 views: {p.get("recent_views", [])}' for p in result['personas']] + [
    '',
    '## Subscribers',
    f'- Total subscribers: {result["supabase"]["subscribers_total"]}, buyers: {result["supabase"]["buyers_total"]}' if result.get('supabase') else '',
    '',
    '## Alerts',
] + ([f'- **{a["severity"].upper()}** — {a["message"]}' for a in result['alerts']] if result['alerts'] else ['_No alerts_']) + [
    '',
    '## AI Summary',
    ai_summary or '_(skipped)_',
]
open(kpi_md, 'w').write('\n'.join(md_lines))
print(f'\n✅ KPI saved → {kpi_md}')

# Slack notify
slack_url = os.environ.get('SLACK_WEBHOOK_URL')
if slack_url and ai_summary:
    try:
        text = f'📊 KPI {datetime.datetime.utcnow().strftime("%Y-%m-%d")}\n{ai_summary}'
        if result['alerts']:
            text += '\n\n⚠️ Alerts:\n' + '\n'.join([f'- {a["message"]}' for a in result['alerts']])
        req = urllib.request.Request(slack_url, data=json.dumps({'text': text}).encode(),
                                      headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
        print('  ✅ Slack posted')
    except Exception as e:
        print(f'  ❌ Slack failed: {e}')
PY

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ kpi-dashboard done — $KPI_MD"
echo "═══════════════════════════════════════════════"
