#!/usr/bin/env bash
# Letter Bank Builder — generate N letters and append to bank_letter_<lang>.jsonl.
# Usage: run.sh <en|jp> <count> [start_id=1]
set -euo pipefail
LANG_ARG="${1:?usage: run.sh <en|jp> <count> [start_id]}"
COUNT="${2:?count required}"
START_ID="${3:-1}"

ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

[ -n "${OPENAI_API_KEY:-}" ] || { echo "❌ OPENAI_API_KEY missing"; exit 3; }
mkdir -p "$ROOT/scripts"

BANK_PATH="$ROOT/scripts/bank_letter_${LANG_ARG}.jsonl"

echo "═══════════════════════════════════════════════"
echo "  letter-bank-builder — lang=$LANG_ARG count=$COUNT start_id=$START_ID"
echo "  → $BANK_PATH"
echo "═══════════════════════════════════════════════"

python3 - <<'PY' "$LANG_ARG" "$COUNT" "$START_ID" "$BANK_PATH"
import json, sys, os, urllib.request, datetime, time

lang, count, start_id, bank_path = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
key = os.environ['OPENAI_API_KEY']

THEMES = [
    'anicca / impermanence', 'dukkha / suffering has expiration', 'anatta / no-self',
    '90-second emotion half-life', 'breath as anchor', 'reactivity vs response',
    'sankhara / mental formations', 'vedana / sensation as messenger',
    'impermanence of joy', 'impermanence of pain', 'loss as teacher',
    'change is the only constant', 'aging as gift', 'death as deadline',
    'the self illusion', 'mindfulness in routine', 'non-attachment',
    'metta / loving-kindness', 'equanimity', 'samvega / urgency',
    'the present moment', 'thoughts as weather', 'desire as movement',
    'aversion as movement', 'the witness', 'pamada / heedlessness',
    'appamada / heedfulness', 'morning practice', 'evening practice',
    'walking meditation', 'eating meditation', 'social media as practice',
    'work as practice', 'family as practice', 'sleep as letting go',
    'anger as fire', 'anxiety as future-mind', 'depression as past-mind',
    'gratitude after pain', 'forgiveness as freedom', 'silence as practice',
    'noise as teacher', 'failure as compost', 'success as sand',
    'comparison as poison', 'enough-ness', 'simplicity', 'non-doing'
]

def gpt(prompt, model='gpt-4o-mini', max_tokens=1500):
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=json.dumps({'model': model, 'messages': [{'role':'user','content':prompt}], 'max_tokens': max_tokens}).encode(),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())['choices'][0]['message']['content']

if lang == 'en':
    style_hint = '''Tone: serene, direct, like a Theravada monk who reads stoicism. Lower-case "i" never; sentence case throughout.
~150-200 words. Each letter ends with "— Anicca" signature.
HTML uses Georgia serif, max-width 560px, line-height 1.7, color #2A2520 on #FBF7EF.
"Anicca" pronounced ah-NEE-cha — explain in letter 1 only.'''
    sig = '— Anicca'
else:
    style_hint = '''トーン: 静かで率直、上座部仏教の僧侶がストア派を読んだような声。
~150-200 words 相当（日本語で約 350-450 字）。各レターは「— {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}」で締める。
HTML は Hiragino Mincho ProN serif, max-width 560px, line-height 1.9, #2A2520 on #FBF7EF。
「{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}」は letter 1 でのみ説明する。'''
    sig = '— {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}'

with open(bank_path, 'a') as bf:
    for i in range(count):
        idx = start_id + i
        theme = THEMES[(idx - 1) % len(THEMES)]
        prompt = f'''Write Letter #{idx} of an Anicca daily letter series, lang={lang}.

Theme for this letter: "{theme}"

{style_hint}

Return strict JSON:
{{
  "subject": "<≤80 chars subject line>",
  "preheader": "<≤90 chars {{profile.lateness.stakeholders.channel}} preview text>",
  "html": "<the full {{profile.lateness.stakeholders.channel}} HTML body, starting with <div>...>",
  "tags": ["<tag>", "..."]
}}

The HTML body must:
- start with `<div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;padding:24px;color:#2A2520;line-height:1.7;background:#FBF7EF;">` (or Hiragino for jp)
- have an <h1 style="font-weight:300;font-size:22px;margin-top:0;"> headline
- have 3-5 short <p> paragraphs
- end with <p>{sig}</p>
- include a footer hr + a small link to {('aniccaai.com/monk' if lang == 'en' else 'aniccaai.com/achan')} with the ebook offer

Output only the JSON, no markdown wrapping.'''

        try:
            out = gpt(prompt).strip()
            if out.startswith('```'):
                out = '\n'.join(l for l in out.split('\n') if not l.strip().startswith('```'))
            letter = json.loads(out)
            entry = {
                'id': f'letter-{lang}-{idx:03d}',
                'lang': lang,
                'theme': theme,
                'subject': letter['subject'][:120],
                'preheader': letter['preheader'][:120],
                'html': letter['html'],
                'tags': letter.get('tags', []),
                'created_at': datetime.datetime.utcnow().isoformat() + 'Z',
            }
            bf.write(json.dumps(entry, ensure_ascii=False) + '\n')
            bf.flush()
            print(f'  ✅ {entry["id"]} — {entry["subject"][:60]}')
        except Exception as e:
            print(f'  ❌ idx={idx} theme="{theme}": {e}')
            time.sleep(2)
PY

echo ""
echo "✅ done — see $BANK_PATH"
echo "  total entries: $(wc -l < $BANK_PATH)"
