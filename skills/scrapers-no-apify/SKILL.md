---
name: scrapers-no-apify
description: Free fallback scrapers (TT/IG/YT) replacing Apify. Uses agent-{{profile.lateness.stakeholders.channel}} for TT/IG profile metadata, yt-dlp for YouTube. Source any Apify-using script with `scripts/lib.sh` to get drop-in functions when Apify credit runs out. Works without API keys.
metadata:
  tags: scraping, fallback, apify-replacement, agent-{{profile.lateness.stakeholders.channel}}, yt-dlp
  requires:
    bins: [agent-{{profile.lateness.stakeholders.channel}}, yt-dlp, jq, curl, python3]
---

# scrapers-no-apify

Drop-in fallback when Apify is broke / credit out. Use agent-{{profile.lateness.stakeholders.channel}} + yt-dlp instead.

## Usage

```bash
source ~/.openclaw/skills/scrapers-no-apify/scripts/lib.sh

# All return JSON
scrape_tt_profile "your-tiktok-handle"            # → {"handle","followers","likes","bio"}
scrape_ig_profile "anicca.ai"             # → {"handle","followers","posts"}
scrape_yt_channel "https://youtube.com/@anicca-ai"  # → {"channel","followers","videos"}
download_tt_video "https://tiktok.com/@user/video/123"  # → mp4 path via snaptik.app
```

## Apify-using SKILL list (10) — wrap each with fallback

| SKILL | Apify usage |
|------|----|
| aniccaai-dashboard (fetch-followers.js) | TT/IG/YT follower scrape |
| aniccaai-dashboard (fetch-spend.js) | Apify spend self-query |
| 4.7-slideshow-factory | TT hook discovery |
| kpi-dashboard | analytics |
| winner-analyzer | hook ranking |
| tiktok-scraper | direct TT scrape |
| virality-copy-factory | TT trend discover |
| naist-metrics | metrics |
| factory-evolution | logs ref |
| yangmun-monk-factory | refs |

## Fallback pattern (add to top of any Apify script)

```bash
APIFY_OK=$(curl -sS -o /dev/null -w "%{http_code}" \
  "https://api.apify.com/v2/users/me?token=$APIFY_API_TOKEN" -m 10 || echo "000")
if [ "$APIFY_OK" != "200" ]; then
  echo "⚠ Apify down — using scrapers-no-apify fallback"
  source ~/.openclaw/skills/scrapers-no-apify/scripts/lib.sh
  USE_FALLBACK=true
else
  USE_FALLBACK=false
fi
```

## When TT/IG profile NOT found

agent-{{profile.lateness.stakeholders.channel}} returns `{"error": "not_found"}` — typically account renamed/private. Caller should handle.

## Cost

| Source | Cost |
|------|----|
| agent-{{profile.lateness.stakeholders.channel}} | $0 (Chrome for Testing local) |
| yt-dlp | $0 |
| snaptik.app | $0 ({{profile.lateness.stakeholders.channel}} navigation) |
| **Total** | **$0/month** |
