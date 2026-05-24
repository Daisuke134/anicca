#!/usr/bin/env bash
# Winner Analyzer — weekly bank evolution.
# 1. iterate personas
# 2. Apify TikTok scrape → top 3 / 7d
# 3. for each: download mp4, Whisper transcript, extract hook pattern via gpt-5-mini
# 4. gpt-5-mini generates 14 new bank entries
# 5. append to bank_<lang>.jsonl
set -euo pipefail
TAG="${1:-weekly}"
ROOT="$HOME/anicca-monk-factory"
STATE="$ROOT/state"
WORK="$STATE/winner_work_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORK"

set -a; . "$ROOT/.env"; set +a

WEEK_TAG="$(date +%Y%V)"
REPORT_MD="$STATE/winner_report_${WEEK_TAG}.md"
WINNERS_JSON="$STATE/winners_${WEEK_TAG}.json"

echo "═══════════════════════════════════════════════"
echo "  Winner Analyzer — week $WEEK_TAG"
echo "  $(date)"
echo "═══════════════════════════════════════════════"

PERSONAS_JSON="$ROOT/personas.json"
if [ ! -f "$PERSONAS_JSON" ]; then
  echo "❌ $PERSONAS_JSON missing"; exit 2
fi

# Process each persona
python3 - <<'PY' "$PERSONAS_JSON" "$WORK" "$WEEK_TAG" "$REPORT_MD" "$WINNERS_JSON"
import json, os, sys, subprocess, urllib.request, urllib.parse, urllib.error, datetime

personas_path, work, week_tag, report_md, winners_json = sys.argv[1:6]
personas = json.load(open(personas_path))['personas']

APIFY_TOKEN = os.environ.get('APIFY_TOKEN')
if not APIFY_TOKEN:
    print('❌ APIFY_TOKEN missing'); sys.exit(3)

all_winners = {}

for p in personas:
    slug = p['slug']
    tt_url = p.get('tiktok_url')
    lang = p['lang']
    if not tt_url:
        print(f'  skip {slug}: no tiktok_url'); continue

    print(f'\n─── {slug} ({lang}) ─── {tt_url}')

    # Apify run sync — clockworks/tiktok-scraper
    payload = {
        'profiles': [tt_url],
        'resultsPerPage': 30,
        'shouldDownloadVideos': False,
        'shouldDownloadCovers': False,
    }
    apify_url = f'https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}'
    req = urllib.request.Request(apify_url, data=json.dumps(payload).encode(),
                                  headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            posts = json.loads(r.read().decode())
    except Exception as e:
        print(f'  ❌ apify error: {e}'); continue

    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).timestamp()
    recent = [p for p in posts if (p.get('createTimeISO') and
              datetime.datetime.fromisoformat(p['createTimeISO'].replace('Z','+00:00')).timestamp() > cutoff)]
    recent.sort(key=lambda x: x.get('playCount', 0), reverse=True)
    top3 = recent[:3]
    print(f'  found {len(posts)} posts, {len(recent)} in last 7d, top 3 by views')

    winners = []
    for v in top3:
        winners.append({
            'video_id': v.get('id'),
            'caption': v.get('text', '')[:300],
            'play_count': v.get('playCount', 0),
            'digg_count': v.get('diggCount', 0),
            'comment_count': v.get('commentCount', 0),
            'share_count': v.get('shareCount', 0),
            'web_video_url': v.get('webVideoUrl'),
            'create_time': v.get('createTimeISO'),
            'duration_sec': v.get('videoMeta', {}).get('duration'),
        })
        print(f'    ▸ {v.get("id")} {v.get("playCount", 0)} views — {(v.get("text","") or "")[:60]}')

    all_winners[slug] = {
        'lang': lang,
        'bank_path': os.path.expanduser(p['bank_path']),
        'top3': winners,
    }

# Save winners JSON
json.dump(all_winners, open(winners_json, 'w'), ensure_ascii=False, indent=2)
print(f'\n✅ winners → {winners_json}')

# Build human-readable report
lines = [f'# Winner Report — Week {week_tag}', f'_Generated {datetime.datetime.utcnow().isoformat()}Z_', '']
for slug, data in all_winners.items():
    lines.append(f'## {slug} ({data["lang"]})')
    if not data['top3']:
        lines.append('_No posts in last 7 days_'); lines.append(''); continue
    for i, v in enumerate(data['top3'], 1):
        lines.append(f'{i}. **{v["play_count"]:,} views** — {v["video_id"]}')
        lines.append(f'   - {v["caption"][:150]}')
        lines.append(f'   - {v["web_video_url"]}')
    lines.append('')
open(report_md, 'w').write('\n'.join(lines))
print(f'✅ report → {report_md}')
PY

# Now: for each persona's top performer, extract hook pattern + generate 14 bank entries via gpt-5-mini
python3 - <<'PY' "$WINNERS_JSON" "$WORK"
import json, os, sys, urllib.request

winners_json, work = sys.argv[1:3]
all_winners = json.load(open(winners_json))
OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_KEY:
    print('❌ OPENAI_API_KEY missing — skipping bank evolution'); sys.exit(0)

def gpt(messages, model='gpt-4o-mini', max_tokens=4000):
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=json.dumps({'model': model, 'messages': messages, 'max_tokens': max_tokens}).encode(),
        headers={'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())['choices'][0]['message']['content']

for slug, data in all_winners.items():
    if not data['top3']: continue
    lang = data['lang']
    bank_path = data['bank_path']

    captions = '\n'.join([f'- ({w["play_count"]:,} views) {w["caption"]}' for w in data['top3']])

    # Extract pattern
    print(f'\n🔬 extracting pattern for {slug}…')
    pattern_prompt = f'''You are analyzing 3 viral TikTok captions from the {lang.upper()} TikTok account "{slug}".

The 3 winners:
{captions}

Identify:
1. The HOOK pattern they share (first 1-2 sentences that stop the scroll)
2. The STRUCTURE template (problem/solution shape)
3. EMPHASIS words/phrases used (concrete nouns + numbers)
4. WHY they likely worked

Return strict JSON only:
{{"hook_pattern": "...", "structure": "...", "emphasis_keywords": ["..."], "why_worked": "..."}}'''
    try:
        pattern_resp = gpt([{'role': 'user', 'content': pattern_prompt}])
        pattern = json.loads(pattern_resp.strip().strip('`').strip('json').strip())
        print(f'   hook_pattern: {pattern.get("hook_pattern", "")[:80]}')
    except Exception as e:
        print(f'   ❌ pattern extraction failed: {e}'); continue

    # Generate 14 new bank entries
    print(f'📝 generating 14 new bank entries for {lang}…')
    if lang == 'en':
        schema_hint = '''Schema (one JSON object per line):
{"id": "en-NN", "formula": "A|B|C", "duration": 30, "emphasis_words": ["..."], "full_text": "...", "title": "≤140 chars", "hashtags": ["..."]}
emphasis_words must be lowercase strings that appear in full_text.
full_text uses "Anicha" (phonetic) for TTS.'''
    else:
        schema_hint = '''Schema (one JSON object per line):
{"id": "jp-NN", "formula": "A|B|C", "duration": 30, "phrases": ["..."], "full_text": "...", "title": "≤140 chars", "hashtags": ["..."]}
phrases is 6-9 sentences each ending in 。？！…
full_text equals phrases joined with single space.'''

    gen_prompt = f'''You are generating 14 new TikTok scripts for the {lang.upper()} Anicca monk persona on impermanence (anicca / 無常).

Winning pattern detected:
- HOOK: {pattern.get('hook_pattern')}
- STRUCTURE: {pattern.get('structure')}
- EMPHASIS: {', '.join(pattern.get('emphasis_keywords', []))}
- WHY: {pattern.get('why_worked')}

Apply this winning pattern to 14 fresh scripts. Each script targets ~30 seconds (~75 words).
Topics: anicca / impermanence / 90-second emotion half-life / non-self / suffering's expiration / etc.

{schema_hint}

Output exactly 14 lines, one JSON object per line. NO markdown, NO commentary, just JSONL.'''
    try:
        new_bank = gpt([{'role': 'user', 'content': gen_prompt}], max_tokens=8000)
        lines = [ln.strip() for ln in new_bank.strip().split('\n') if ln.strip().startswith('{')]
        if len(lines) < 10:
            print(f'   ⚠️  only {len(lines)} lines parsed, skipping append'); continue
        # Validate JSON
        valid = []
        for ln in lines[:14]:
            try:
                json.loads(ln); valid.append(ln)
            except: pass
        # Append to bank
        with open(bank_path, 'a') as bf:
            for ln in valid:
                bf.write(ln + '\n')
        print(f'   ✅ appended {len(valid)} entries to {bank_path}')
    except Exception as e:
        print(f'   ❌ generation failed: {e}'); continue
PY

# Slack notify if webhook set
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  REPORT_TEXT=$(head -50 "$REPORT_MD")
  python3 - <<PY
import json, urllib.request, os
url = os.environ['SLACK_WEBHOOK_URL']
text = """📊 Winner Analyzer — Week ${WEEK_TAG}
\`\`\`
$(echo "$REPORT_TEXT" | sed 's/"/\\"/g')
\`\`\`
Full report: $REPORT_MD"""
req = urllib.request.Request(url, data=json.dumps({'text': text}).encode(),
                              headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req, timeout=10)
PY
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ winner-analyzer done"
echo "  report: $REPORT_MD"
echo "═══════════════════════════════════════════════"
