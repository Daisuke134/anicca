#!/usr/bin/env bash
# Refill IAM photo pools (en + ja). Run monthly via cron.
set -euo pipefail
set -a; source ~/.openclaw/.env; set +a

for SLUG in anicca-iam-photo-en anicca-iam-photo-ja; do
  SKILL="$HOME/.openclaw/skills/$SLUG"
  POOL="$SKILL/pool"
  BACKUP="$SKILL/pool-backup/$(date +%Y%m%d)"
  mkdir -p "$POOL" "$BACKUP"
  # backup existing
  if compgen -G "$POOL/bg_*.jpg" > /dev/null; then
    mv "$POOL"/bg_*.jpg "$BACKUP/" 2>/dev/null || true
  fi
  echo "=== refill $SLUG ==="
  python3 -c "
import os, sys, json, requests, pathlib, datetime
sys.path.insert(0, '$SKILL/scripts')
from importlib import import_module
b = import_module('build-slideshow' if False else 'build_slideshow' if False else None) if False else None
# Just inline the BG_PROMPTS
" 2>/dev/null || true
  # extract BG_PROMPTS via python
  python3 <<PY
import os, json, requests, pathlib
SKILL = pathlib.Path('$SKILL')
exec(open(SKILL / 'scripts' / 'build-slideshow.py').read().split('def fal_background')[0])
pool = SKILL / 'pool'
headers = {'Authorization': f\"Key {os.environ['FAL_API_KEY']}\"}
for i, prompt in enumerate(BG_PROMPTS[:10], 1):
    print(f'  generating bg_{i}.jpg ({prompt[:50]}...)')
    r = requests.post('https://fal.run/fal-ai/flux/dev', headers=headers,
        json={'prompt': prompt, 'image_size':{'width':W,'height':H},'num_inference_steps':28,'guidance_scale':3.5,'num_images':1,'enable_safety_checker':True},
        timeout=180)
    r.raise_for_status()
    url = r.json()['images'][0]['url']
    img = requests.get(url, timeout=60).content
    (pool / f'bg_{i}.jpg').write_bytes(img)
print(f'  ✓ {SKILL.name}: refilled {len(list(pool.glob(\"bg_*.jpg\")))} images')
PY
done

# Slack 報告
EN_N=$(ls ~/.openclaw/skills/anicca-iam-photo-en/pool/bg_*.jpg 2>/dev/null | wc -l | tr -d ' ')
JA_N=$(ls ~/.openclaw/skills/anicca-iam-photo-ja/pool/bg_*.jpg 2>/dev/null | wc -l | tr -d ' ')
echo "✅ pool refilled: en=$EN_N ja=$JA_N"
