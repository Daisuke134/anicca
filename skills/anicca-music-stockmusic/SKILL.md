---
name: anicca-music-stockmusic
description: Expand anicca-music-factory beyond Spotify-only royalties. Implements 5-stream monetization per Suno+Claude article — stock music libraries (AudioJungle/Pond5/Epidemic), Fiverr custom orders, YouTube ad revenue, $15/mo membership site, sync licensing pitch. Use when triggered by `anicca-music-stockmusic-batch-daily` cron at 04:30 JST, or manually as `bash scripts/upload-to-stockmusic.sh`.
metadata:
  tags: music, suno, audiojungle, pond5, fiverr, stockmusic, monetization
  requires:
    bins: [bash, jq, curl, {{profile.lateness.stakeholders.channel}}-harness]
    env: [SUNO_COOKIE, RESEND_API_KEY]
---

# anicca-music-stockmusic

Expand anicca-music-factory from 1 stream (Spotify royalties) to 5 streams.

## 5-Stream blueprint (per article)

| Stream | Mechanism | Per-track | Cron |
|------|--------|--------|----|
| 1. Stock music (AudioJungle/Pond5/Epidemic) | Upload, sells passively | $19-79 | `anicca-music-stockmusic-batch-daily` 04:30 |
| 2. Fiverr custom orders | "Custom AI music in 24h" gig | $25-200 | `anicca-music-fiverr-monitor` (hourly check) |
| 3. YouTube ad revenue | Lo-Fi study beats channel | $1-5/1000 views | (existing youtube cron) |
| 4. Membership site $15/mo | aniccaai.com/music-library | $15/mo recurring | (Stripe sub) |
| 5. Sync licensing pitch | Cold {{profile.lateness.stakeholders.channel}} biz/film | $200-2,000 one-time | `anicca-music-sync-pitch-monthly` 月初 12:00 |

## Phase 1 (5/8-5/14): Niche research + AudioJungle account

```
1. Claude analyzes AudioJungle / Pond5 ranking pages → niche gap report
2. Dais signs up AudioJungle account (manual, KYC-bound)
3. {{profile.lateness.stakeholders.channel}}-harness saves cookies for batch upload
```

## Phase 2 (5/15-5/21): Daily batch upload

```
1. anicca-music-factory generates 5-10 tracks/day with Claude-optimized Suno prompts
2. anicca-music-stockmusic packages: WAV + AudioJungle metadata
3. {{profile.lateness.stakeholders.channel}}-harness Way 2 → audiojungle.net upload → metadata fill → submit
4. Track success in Supabase music_uploads table
```

## Phase 3 (5/22+): Fiverr gig + membership site

```
1. Fiverr: 1 gig "Custom AI music 24h" — Claude writes title/desc/FAQ
2. aniccaai.com/music-library: Stripe sub $15/mo → access to library
3. Cold {{profile.lateness.stakeholders.channel}} pitch (50/mo) → sync licensing
```

## Niche prompts (Claude template)

```
You are an expert music producer who specializes in writing prompts for Suno AI.
Generate 10 detailed Suno prompts for [genre] tracks targeting [platform: AudioJungle/YouTube/Fiverr].
Each prompt: instruments + role / tempo BPM / key+scale / mood (3-5 words) / production style /
duration+structure / exclusions / platform requirement.
```

## Crons (3)

| name | schedule | action |
|------|--------|------|
| anicca-music-niche-research-weekly | `0 4 * * 1` (Mon 04:00 JST) | Claude analyzes niches → next-week production plan |
| anicca-music-stockmusic-batch-daily | `30 4 * * *` (04:30 JST) | Generate + upload 5 tracks to AudioJungle/Pond5 |
| anicca-music-sync-pitch-monthly | `0 12 1 * *` (1st 12:00) | Send 50 cold {{profile.lateness.stakeholders.channel}}s for sync license $199 offer |
