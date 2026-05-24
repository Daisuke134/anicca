#!/usr/bin/env bash
# Daily Letter Sender — Resend Batch API.
set -euo pipefail
TAG="${1:-daily}"
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

[ -n "${RESEND_API_KEY:-}" ] || { echo "❌ RESEND_API_KEY missing"; exit 3; }
[ -n "${SUPABASE_URL:-}" ] && [ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ] || { echo "❌ Supabase env missing"; exit 3; }

echo "═══════════════════════════════════════════════"
echo "  daily-letter-sender — $(date)"
echo "═══════════════════════════════════════════════"

python3 - <<'PY'
import json, os, urllib.request, datetime, time, sys

key_resend = os.environ['RESEND_API_KEY']
sb_url = os.environ['SUPABASE_URL']
sb_key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
root = os.path.expanduser('~/anicca-monk-factory')

# 1) fetch active subscribers (unsubscribed_at IS NULL)
req = urllib.request.Request(
    f'{sb_url}/rest/v1/subscribers?select=*&unsubscribed_at=is.null',
    headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        subs = json.loads(r.read().decode())
    print(f'  📋 {len(subs)} active subscribers')
except Exception as e:
    print(f'  ❌ supabase fetch failed: {e}'); sys.exit(4)

if not subs:
    print('  no subscribers, exiting'); sys.exit(0)

# 2) load letter banks
banks = {}
for lang in ['en', 'jp']:
    path = f'{root}/scripts/bank_letter_{lang}.jsonl'
    if os.path.exists(path):
        banks[lang] = [json.loads(l) for l in open(path) if l.strip()]
        print(f'  📚 bank_{lang}: {len(banks[lang])} letters')
    else:
        banks[lang] = []
        print(f'  ⚠️  bank_letter_{lang}.jsonl missing — {{profile.lateness.stakeholders.channel}}s for {lang} will be skipped')

today = datetime.date.today()
batch_to_send = []
skipped_no_letter = 0

# 3) compute each subscriber's letter for today
for s in subs:
    {{profile.lateness.stakeholders.channel}} = s['{{profile.lateness.stakeholders.channel}}']
    lang = s.get('lang', 'en')
    tier = s.get('tier', 'free')
    if lang not in banks or not banks[lang]: continue

    signed_up = s.get('signed_up_at')
    if not signed_up: continue
    try:
        sign_date = datetime.datetime.fromisoformat(signed_up.replace('Z', '+00:00')).date()
    except: continue
    day_offset = (today - sign_date).days + 1
    if day_offset < 1: continue
    if tier == 'free' and day_offset > 14:
        continue  # free tier expires after 14 days
    bank = banks[lang]
    idx = (day_offset - 1) % len(bank)
    letter = bank[idx]

    # Append "Manage subscription" footer pointing directly to Stripe portal via cid.
    cid = s.get('stripe_customer_id') or ''
    manage_url = f'https://aniccaai.com/account?cid={cid}' if cid else 'https://aniccaai.com/account'
    if lang == 'jp':
        manage_btn = (
            '<hr style="border:none;border-top:1px solid #E5DCC9;margin:32px 0;" />'
            f'<p style="text-align:center;margin:24px 0 8px 0;">'
            f'<a href="{manage_url}" style="display:inline-block;border:1px solid #8B7355;color:#8B7355;'
            'padding:10px 22px;text-decoration:none;letter-spacing:2px;font-size:11px;">'
            'サブスクリプションを管理</a></p>'
        )
    else:
        manage_btn = (
            '<hr style="border:none;border-top:1px solid #E5DCC9;margin:32px 0;" />'
            f'<p style="text-align:center;margin:24px 0 8px 0;">'
            f'<a href="{manage_url}" style="display:inline-block;border:1px solid #8B7355;color:#8B7355;'
            'padding:10px 22px;text-decoration:none;letter-spacing:2px;font-size:11px;text-transform:uppercase;">'
            'Manage subscription</a></p>'
        )
    # Inject before closing </div>; if not found, just append.
    html_with_manage = letter['html']
    if html_with_manage.rstrip().endswith('</div>'):
        html_with_manage = html_with_manage.rstrip()[:-6] + manage_btn + '</div>'
    else:
        html_with_manage = html_with_manage + manage_btn

    batch_to_send.append({
        '{{profile.lateness.stakeholders.channel}}': {{profile.lateness.stakeholders.channel}},
        'lang': lang,
        'day_offset': day_offset,
        'letter_id': letter['id'],
        'subject': letter['subject'],
        'html': html_with_manage,
    })

if not batch_to_send:
    print('  no letters to send today'); sys.exit(0)

print(f'  ✉️  preparing {len(batch_to_send)} letters')

# 4) Resend batch send (max 100 per batch)
sent = 0
failed = 0
for chunk_start in range(0, len(batch_to_send), 100):
    chunk = batch_to_send[chunk_start:chunk_start+100]
    payload = [{
        'from': 'Anicca <onboarding@resend.dev>',
        'to': [item['{{profile.lateness.stakeholders.channel}}']],
        'subject': item['subject'],
        'html': item['html'],
        'tags': [{'name': 'letter_id', 'value': item['letter_id']},
                 {'name': 'lang', 'value': item['lang']}],
    } for item in chunk]
    try:
        req = urllib.request.Request(
            'https://api.resend.com/{{profile.lateness.stakeholders.channel}}s/batch',
            data=json.dumps(payload).encode(),
            headers={'Authorization': f'Bearer {key_resend}', 'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
        sent += len(chunk)
        print(f'    ✅ batch {chunk_start//100 + 1}: sent {len(chunk)}')
        # Log to Supabase
        log_rows = [{
            '{{profile.lateness.stakeholders.channel}}': item['{{profile.lateness.stakeholders.channel}}'],
            'letter_id': item['letter_id'],
            'sent_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'lang': item['lang'],
            'day_offset': item['day_offset'],
        } for item in chunk]
        try:
            log_req = urllib.request.Request(
                f'{sb_url}/rest/v1/daily_letter_log',
                data=json.dumps(log_rows).encode(),
                headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}',
                         'Content-Type': 'application/json', 'Prefer': 'resolution=merge-duplicates'}
            )
            urllib.request.urlopen(log_req, timeout=30).read()
        except Exception as e:
            print(f'    ⚠️  log to supabase failed: {e}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f'    ❌ batch {chunk_start//100 + 1} failed: {e.code} {body[:200]}')
        failed += len(chunk)
    except Exception as e:
        print(f'    ❌ batch failed: {e}')
        failed += len(chunk)
    time.sleep(1)

print(f'\n  ✅ sent: {sent}, failed: {failed}')

# Slack notify
slack_url = os.environ.get('SLACK_WEBHOOK_URL')
if slack_url:
    try:
        text = f'📧 Daily letters sent: {sent} ✅, {failed} ❌ ({datetime.date.today()})'
        req = urllib.request.Request(slack_url, data=json.dumps({'text': text}).encode(),
                                      headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except: pass
PY

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ daily-letter-sender done"
echo "═══════════════════════════════════════════════"
