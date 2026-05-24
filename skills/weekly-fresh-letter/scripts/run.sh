#!/usr/bin/env bash
# Weekly Fresh Letter — append 1 fresh letter per lang to bank.
set -euo pipefail
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

[ -n "${OPENAI_API_KEY:-}" ] || { echo "❌ OPENAI_API_KEY missing"; exit 3; }
mkdir -p "$ROOT/scripts"

WEEK_TAG=$(date +%Y%V)
echo "═══════════════════════════════════════════════"
echo "  weekly-fresh-letter — week $WEEK_TAG"
echo "═══════════════════════════════════════════════"

python3 - <<PY "$WEEK_TAG"
import json, os, urllib.request, datetime, sys

week_tag = sys.argv[1]
key = os.environ['OPENAI_API_KEY']
root = os.path.expanduser('~/anicca-monk-factory')

def gpt(prompt, model='gpt-4o-mini', max_tokens=1500):
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=json.dumps({'model': model, 'messages': [{'role':'user','content':prompt}], 'max_tokens': max_tokens}).encode(),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())['choices'][0]['message']['content']

for lang in ['en', 'jp']:
    bank_path = f'{root}/scripts/bank_letter_{lang}.jsonl'
    existing_count = 0
    if os.path.exists(bank_path):
        existing_count = sum(1 for l in open(bank_path) if l.strip())

    if lang == 'en':
        sig = '— Anicca'
        style = '''Tone: Theravada monk who reads stoicism. Lower-case "i" never. ~150-200 words.
Use a current cultural moment (this week, broadly — AI saturation, layoffs, social media exhaustion, climate news, anything topical to a thoughtful US/UK reader as of {today}) as the entry door, but the letter is a meditation on impermanence not a hot-take.
HTML: Georgia serif, max-width 560px, line-height 1.7, color #2A2520 on #FBF7EF. <h1 style="font-weight:300;font-size:22px;margin-top:0;"> headline. End with <p>{sig}</p>.'''.format(today=datetime.date.today().isoformat(), sig=sig)
        product_url = 'aniccaai.com/monk'
    else:
        sig = '— {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}'
        style = '''トーン: 上座部仏教の僧侶がストア派を読んだような声。~350-450 字。
今週の文化的瞬間（AI 飽和、雇用、SNS 疲れ、気候、思慮深い日本の読者にとって今週的なもの）を入口にするが、letter 自体は無常の瞑想であってホットテイクではない。
HTML: Hiragino Mincho ProN serif, max-width 560px, line-height 1.9, #2A2520 on #FBF7EF。
<h1 style="font-weight:300;font-size:22px;margin-top:0;"> 見出し。<p>{sig}</p> で締める。'''.format(sig=sig)
        product_url = 'aniccaai.com/achan'

    prompt = f'''Write THIS WEEK's fresh letter for the Anicca daily series, lang={lang}, week={week_tag}.

{style}

The letter must include a footer:
<hr style="border:none;border-top:1px solid #E5DCC9;margin:32px 0;" />
<p style="font-size:13px;color:#8B7355;">{('If you'+chr(39)+'d like the full 49-lesson book') if lang == 'en' else '49 章すべて読みたい方は'}: <a href="https://{product_url}" style="color:#2A2520;">{('The Anicca Reset — $10.99') if lang == 'en' else '『{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}・リセット』 — ¥1,580'}</a></p>

Return strict JSON only:
{{
  "subject": "<≤80 chars>",
  "preheader": "<≤90 chars>",
  "html": "<full {{profile.lateness.stakeholders.channel}} HTML body starting with <div>>",
  "tags": ["fresh", "<theme>"]
}}'''

    try:
        out = gpt(prompt).strip()
        if out.startswith('```'):
            out = '\n'.join(l for l in out.split('\n') if not l.strip().startswith('```'))
        letter = json.loads(out)
        entry = {
            'id': f'letter-{lang}-fresh-{week_tag}',
            'lang': lang,
            'theme': 'this-week',
            'fresh': True,
            'subject': letter['subject'][:120],
            'preheader': letter['preheader'][:120],
            'html': letter['html'],
            'tags': letter.get('tags', ['fresh']),
            'created_at': datetime.datetime.utcnow().isoformat() + 'Z',
        }
        with open(bank_path, 'a') as bf:
            bf.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f'  ✅ {lang}: {entry["subject"][:80]}')
    except Exception as e:
        print(f'  ❌ {lang}: {e}')

print(f'\n  ✅ weekly fresh letter done — week {week_tag}')
PY

# Slack notify
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
python3 - <<PY
import json, urllib.request, os
url = os.environ['SLACK_WEBHOOK_URL']
text = f'📨 weekly-fresh-letter: appended fresh letter (en+jp) for week ${WEEK_TAG}'
req = urllib.request.Request(url, data=json.dumps({'text': text}).encode(),
                              headers={'Content-Type': 'application/json'})
try: urllib.request.urlopen(req, timeout=10)
except: pass
PY
fi
