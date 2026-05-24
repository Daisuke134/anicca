---
name: publora-tiktok
description: >
  Post or schedule video content to TikTok using the Publora API. Use this skill
  when the user wants to publish or schedule TikTok videos via Publora.
---

# Publora — TikTok

TikTok platform skill for the Publora API. For auth, core scheduling, media upload, and workspace/webhook docs, see the `publora` core skill.

**Base URL:** `https://api.publora.com/api/v1`  
**Header:** `x-publora-key: sk_YOUR_KEY`  
**Platform ID format:** `tiktok-{userId}`

## Platform Limits (API)

> ⚠️ TikTok API is stricter than native app for captions and duration.

| Property | API Limit | Native App |
|----------|-----------|-----------|
| Caption | **2,200 characters** | 4,000 characters |
| Video duration | **10 min** | 60 min |
| Video size | 4 GB | — |
| Video format | MP4, MOV, WebM | — |
| Images | ❌ Video only | — |
| Text only | ❌ Video required | — |
| Daily posts | 15–20 posts/day | — |
| Rate limit | 2 videos/minute | — |

**Common errors:**
- `spam_risk_too_many_posts` — daily limit reached, wait 24h
- `duration_check_failed` — video must be 3s–10min
- `unaudited_client_can_only_post_to_private_accounts` — app needs TikTok audit

> ⚠️ If your TikTok app is not audited by TikTok, all posts will be **private** by default.

## Upload a TikTok Video

TikTok requires video. Use the 3-step upload workflow:

```javascript
// Step 1: Create post (draft without scheduledTime, or scheduled)
const post = await fetch('https://api.publora.com/api/v1/create-post', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'x-publora-key': 'sk_YOUR_KEY' },
  body: JSON.stringify({
    content: 'Your TikTok caption here #trending',
    platforms: ['tiktok-123456789'],
    scheduledTime: '2026-03-20T18:00:00.000Z'
  })
}).then(r => r.json());

// Step 2: Get upload URL
const upload = await fetch('https://api.publora.com/api/v1/get-upload-url', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'x-publora-key': 'sk_YOUR_KEY' },
  body: JSON.stringify({
    postGroupId: post.postGroupId,
    fileName: 'video.mp4',
    contentType: 'video/mp4',
    type: 'video'
  })
}).then(r => r.json());

// Step 3: Upload video to S3
await fetch(upload.uploadUrl, {
  method: 'PUT',
  headers: { 'Content-Type': 'video/mp4' },
  body: videoFileBytes
});
```

## Python Example

```python
import requests

HEADERS = { 'Content-Type': 'application/json', 'x-publora-key': 'sk_YOUR_KEY' }

# Step 1: Create post
post = requests.post('https://api.publora.com/api/v1/create-post', headers=HEADERS, json={
    'content': 'Your TikTok caption #viral',
    'platforms': ['tiktok-123456789'],
    'scheduledTime': '2026-03-20T18:00:00.000Z'
}).json()

# Step 2: Get upload URL
upload = requests.post('https://api.publora.com/api/v1/get-upload-url', headers=HEADERS, json={
    'postGroupId': post['postGroupId'],
    'fileName': 'video.mp4',
    'contentType': 'video/mp4',
    'type': 'video'
}).json()

# Step 3: Upload
with open('video.mp4', 'rb') as f:
    requests.put(upload['uploadUrl'], headers={'Content-Type': 'video/mp4'}, data=f)
```

## Platform Quirks

- **Video only** — TikTok does not support images or text-only posts via API
- **Minimum duration**: 3 seconds; maximum via API: 10 minutes
- **Unaudited apps post privately** — videos will be set to private if the Publora TikTok app hasn't passed TikTok's audit
- **Caption limit is 2,200 via API** (not 4,000 like native) — keep captions concise
- **Daily limit**: 15–20 posts/day enforced by TikTok
