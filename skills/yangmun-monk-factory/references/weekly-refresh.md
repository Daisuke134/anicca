# Weekly Refresh — replenish the hook bank

Run every Monday before the week starts. Pulls what's actually working on TikTok in the anicca niche, adapts it to our voice, refills the bank.

## 1. Scrape reference accounts

```bash
export APIFY_TOKEN=$(grep APIFY_TOKEN ~/.openclaw/.env | cut -d= -f2)

ACCOUNTS_JP='["isshin.mindstructure","busshi.channel","zenmonkwisdom.jp","mindful.buddha.jp"]'
ACCOUNTS_EN='["stoicmindset0","thegreatstoic","the.wise.stoic","yang.mun","mindful.monk.wisdom"]'

for lang in jp en; do
  case $lang in
    jp) A="$ACCOUNTS_JP" ;;
    en) A="$ACCOUNTS_EN" ;;
  esac
  curl -s -X POST "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"profiles\":$A,\"resultsPerPage\":20,\"shouldDownloadVideos\":false,\"shouldDownloadCovers\":false}" \
    > ~/anicca-monk-factory/state/scrape_${lang}_$(date +%Y%m%d).json
done
```

## 2. Extract outliers

Median-play × 3 is the outlier threshold. For each account, find videos with `playCount > median * 3`.

```python
# scripts/extract_outliers.py
import json, glob, statistics
for fp in glob.glob(f'state/scrape_*_*.json'):
    data = json.load(open(fp))
    by_user = {}
    for v in data:
        by_user.setdefault(v['authorMeta']['name'], []).append(v)
    for user, vids in by_user.items():
        plays = [v['playCount'] for v in vids]
        if len(plays) < 5: continue
        med = statistics.median(plays)
        outliers = [v for v in vids if v['playCount'] > med * 3]
        for v in outliers:
            print(f"{user}\t{v['playCount']}\t{v['text'][:200]}")
```

## 3. Ask Claude to draft 20 new hooks

Feed the outlier transcripts (or text captions — do not reproduce verbatim) to Claude with this system prompt:

> You are a copy writer for Anicca, a spiritual brand teaching impermanence. Given these high-performing short-form video openings as tone reference (do NOT copy wording — only match cadence, emotional register, and formula family), produce 20 ORIGINAL opening hooks for 30-second videos. Each must map to one of the 3 formulas: A (Empathy Reframe), B (You're Doing It Wrong), or C (Validation). Topics must be impermanence-adjacent: anger, grief, overthinking, ex-relationships, sleep, aging, comparison. Output JSONL with keys: id, formula, hook, body, close, hashtags.

Human review before saving to `scripts/bank_<lang>.jsonl`. Kill any hook that:
- copies a specific phrase from source material verbatim
- uses the word "Anicca" in the spoken hook (save it for the reveal at ~10s)
- promises outcomes we can't teach in 30s

## 4. Reset the state index

If the bank was exhausted, reset `state/last_index_<lang>.json` to 0.

## 5. Log to weekly summary

```bash
echo "$(date): refreshed ${lang} bank, $(wc -l < scripts/bank_${lang}.jsonl) scripts available" \
  >> ~/anicca-monk-factory/state/refresh.log
```
