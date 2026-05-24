# Postiz Publish — per-platform calls

Auth: `Authorization: ${POSTIZ_API_KEY}` (NOT `Bearer` — Postiz public API uses raw token).
Base: `https://api.postiz.com/public/v1`

## Step 1 — Upload the MP4

```bash
UPLOAD=$(curl -s -X POST "https://api.postiz.com/public/v1/upload" \
  -H "Authorization: ${POSTIZ_API_KEY}" \
  -F "file=@$FINAL_MP4;filename=$(basename $FINAL_MP4);type=video/mp4")

MEDIA_ID=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
MEDIA_PATH=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
```

`filename=` is required or Postiz saves as `.bin` and TikTok rejects.

## Step 2 — Post to each integration (separate calls)

The cron message passes the single `POSTIZ_INTEGRATION_ID` for the primary account (TikTok). If you also want IG/YT/FB, their IDs are looked up via `POSTIZ_IG_ID`, `POSTIZ_YT_ID`, `POSTIZ_FB_ID` fields in the `.env`, or passed in the same cron message.

### TikTok

```bash
curl -s -X POST "https://api.postiz.com/public/v1/posts" \
  -H "Authorization: ${POSTIZ_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"now\",
    \"date\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\",
    \"shortLink\": false,
    \"tags\": [],
    \"posts\": [{
      \"integration\": {\"id\": \"$TIKTOK_INTEGRATION_ID\"},
      \"value\": [{
        \"content\": \"$HASHTAGS\",
        \"image\": [{\"id\": \"$MEDIA_ID\", \"path\": \"$MEDIA_PATH\"}]
      }],
      \"settings\": {
        \"__type\": \"tiktok\",
        \"title\": \"$TITLE\",
        \"privacy_level\": \"PUBLIC_TO_EVERYONE\",
        \"duet\": false,
        \"stitch\": false,
        \"comment\": true,
        \"brand_content_toggle\": false,
        \"brand_organic_toggle\": false,
        \"video_made_with_ai\": true,
        \"content_posting_method\": \"DIRECT_POST\"
      }
    }]
  }"
```

Note: `video_made_with_ai: true` — required by TikTok for AI avatar content (Cover Your Ass policy compliance).

### Hashtags and Title

| Language | Title (TikTok caption) | Hashtags (IG/YT description) |
|---|---|---|
| EN | "Everything passes. Your anger too. / free Anicca one-pager in bio" | `#anicca #impermanence #buddhistmonk #mindfulness #anxiety #stoicism #lifeadvice #mentalhealth #meditation #zen` |
| JP | "怒りも不安も、必ず消える。無料の無常手帳はプロフリンク" | `#{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} #無常 #瞑想 #マインドフルネス #仏教 #メンタル #生きづらさ #自己受容 #心理学 #日常` |

## Failure Handling

- 400 response → log body, save payload to `renders/failed/YYYY-MM-DD.json`, continue to next platform
- 401 → POSTIZ_API_KEY expired, stop and notify
- If TikTok rejects for "video too long", re-cut to 60s and retry once

## Only post TikTok by default

For the first 2 weeks, only post TikTok (`POSTIZ_INTEGRATION_ID` from cron). After proving the system, add IG/YT/FB integrations and enable those calls.
