#!/usr/bin/env python3
"""
revenue-allocator — monthly treasury allocation.

Reads dashboard.json (already-populated MRR + spend + profit), pulls live Apify
monthly usage, computes re-investment budget, updates personas.json with
monthly_budget_usd, snapshots allocation, and posts Slack.
"""
import json, os, sys, urllib.request, datetime, pathlib

ROOT = pathlib.Path(os.path.expanduser('~'))
DASHBOARD = ROOT / 'anicca-products/apps/landing/public/dashboard.json'
PERSONAS = ROOT / 'anicca-monk-factory/personas.json'
SKILL = ROOT / '.openclaw/skills/revenue-allocator'
STATE = SKILL / 'state'
STATE.mkdir(parents=True, exist_ok=True)

APIFY = os.environ.get('APIFY_TOKEN')
SLACK_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL_ID', '{{profile.channels.reportChannel}}')

if not DASHBOARD.exists():
    print(f'❌ dashboard.json missing: {DASHBOARD}'); sys.exit(2)

now = datetime.datetime.now(datetime.UTC)
month = now.strftime('%Y-%m')
print(f'💰 revenue-allocator — {month}')

# 1. Read dashboard.json
d = json.loads(DASHBOARD.read_text())
mrr_total = d.get('mrr', {}).get('total_usd', 0)
mrr_stripe = d.get('mrr', {}).get('sources', {}).get('stripe', 0)
mrr_rc = d.get('mrr', {}).get('sources', {}).get('revenuecat_mobile', 0) or 0
spend_total = d.get('spend', {}).get('total_usd', 0)
spend_by_cat = d.get('spend', {}).get('by_category', {})
profit = round(mrr_total - spend_total, 2)
basic_income_pool = round(mrr_total * 0.10, 2)
print(f'   MRR ${mrr_total} (Stripe ${mrr_stripe} + RC ${mrr_rc})')
print(f'   Spend ${spend_total}')
print(f'   Profit ${profit}')

# 2. Apify monthly usage
apify_usage = {'consumed_usd': None, 'alert': False}
if APIFY:
    try:
        req = urllib.request.Request('https://api.apify.com/v2/users/me/usage/monthly',
            headers={'Authorization': f'Bearer {APIFY}'})
        ar = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())['data']
        cycle = ar.get('usageCycle', {})
        # Total monthly cost = sum of monthlyServiceUsage[].amountAfterVolumeDiscountUsd
        total = sum(float(v.get('amountAfterVolumeDiscountUsd', 0)) for v in ar.get('monthlyServiceUsage', {}).values())
        apify_usage = {
            'cycle_start': cycle.get('startAt', '')[:10],
            'cycle_end': cycle.get('endAt', '')[:10],
            'consumed_usd': round(total, 4),
            'alert': total > 5,  # FREE plan = $5 monthly quota, alert at >$5
        }
        print(f'   Apify ${total:.4f} ({cycle.get("startAt","")[:10]} → {cycle.get("endAt","")[:10]})')
    except Exception as e:
        print(f'   apify err: {e}')

# 3. Reinvestment budget
reinvest = round(max(0, profit) * 0.6, 2)

# 4. Active personas
personas_doc = json.loads(PERSONAS.read_text()) if PERSONAS.exists() else {'personas': []}
personas = [p for p in personas_doc.get('personas', []) if p.get('active', True)]
n_active = max(len(personas), 1)
per_persona = round(reinvest / n_active, 2) if n_active > 0 else 0
print(f'   Reinvest ${reinvest} / {n_active} active personas = ${per_persona}/persona')

# 5. Update personas.json with monthly_budget_usd
for p in personas_doc.get('personas', []):
    if p.get('active', True):
        p['monthly_budget_usd'] = per_persona
PERSONAS.write_text(json.dumps(personas_doc, ensure_ascii=False, indent=2))
print(f'   updated personas.json')

# 6. Alerts
alerts = []
if profit < 0:
    alerts.append({'severity': 'high', 'message': f'Spend exceeds MRR by ${-profit:.2f} — runway negative'})
elif profit > 0 and reinvest == 0:
    alerts.append({'severity': 'medium', 'message': 'Profit positive but reinvest=0 — check formula'})
if apify_usage['alert']:
    alerts.append({'severity': 'medium', 'message': f'Apify FREE quota exceeded: ${apify_usage["consumed_usd"]:.2f} consumed'})

# 7. Snapshot
snap = {
    'month': month,
    'computed_at': now.isoformat(),
    'mrr': {'total_usd': mrr_total, 'stripe': mrr_stripe, 'revenuecat_mobile': mrr_rc},
    'spend': {'total_usd': spend_total, 'by_category': spend_by_cat},
    'profit_usd': profit,
    'reinvest_budget_usd': reinvest,
    'basic_income_pool_usd': basic_income_pool,
    'active_personas': n_active,
    'per_persona_budget_usd': per_persona,
    'apify_usage': apify_usage,
    'alerts': alerts,
}
snap_file = STATE / f'allocation_{month.replace("-","")}.json'
snap_file.write_text(json.dumps(snap, indent=2))
(STATE / 'allocation_latest.json').write_text(json.dumps(snap, indent=2))
print(f'   snapshot {snap_file}')

# 8. Slack
if SLACK_TOKEN:
    cat_lines = []
    for cat, v in sorted(spend_by_cat.items(), key=lambda x: -x[1]):
        if v > 0:
            cat_lines.append(f'{cat}: ${v}')
    cat_str = ' · '.join(cat_lines[:5])

    icon = '⚠️' if profit < 0 else '🟢'
    lines = [f'*💰 Monthly Revenue Allocator — {month}*', '']
    lines.append(f'*MRR*: ${mrr_total:.2f}  (Stripe ${mrr_stripe:.2f} · RC mobile ${mrr_rc:.2f})')
    lines.append(f'*Spend*: ${spend_total:.2f}  ({cat_str})')
    lines.append(f'*Profit*: ${profit:+.2f}  {icon}')
    lines.append('')
    lines.append(f'*Reinvest budget*: ${reinvest:.2f}')
    lines.append(f'*Basic income pool*: ${basic_income_pool:.2f} (10% of MRR)')
    lines.append(f'*Per-persona budget*: ${per_persona:.2f} / {n_active} active personas')
    lines.append('')
    if apify_usage['consumed_usd'] is not None:
        lines.append(f'*Apify cycle {apify_usage["cycle_start"]} → {apify_usage["cycle_end"]}*: ${apify_usage["consumed_usd"]:.4f} consumed' + (' 🔴 quota alert' if apify_usage['alert'] else ' ✅'))
    if alerts:
        lines.append('')
        lines.append('*Health alerts:*')
        for a in alerts:
            icon = '🔴' if a['severity'] == 'high' else '🟡'
            lines.append(f'{icon} {a["message"]}')

    text = '\n'.join(lines)
    try:
        req = urllib.request.Request('https://slack.com/api/chat.postMessage',
            data=json.dumps({'channel': SLACK_CHANNEL, 'text': text, 'mrkdwn': True}).encode(),
            headers={'Content-Type': 'application/json; charset=utf-8', 'Authorization': f'Bearer {SLACK_TOKEN}'})
        r = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        print(f'   slack ok={r.get("ok")} ts={r.get("ts")}')
    except Exception as e:
        print(f'   slack err: {e}')

print('\n✅ revenue-allocator done')
