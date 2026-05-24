---
name: anicca-webapp-x-marketing
description: 5-channel X (Twitter) marketing for Anicca's web apps. Build in Public daily thread (4 tweets, dashboard.json snapshot), Pain-Point thread per app per day with 7-app rotation, UGC thank-you reply on mention, cold DM 50/day to ICP via Apify scraper, monthly $50 promoted-post boost on the best-performing thread. Posts via Postiz X integration; cold DM via {{profile.lateness.stakeholders.channel}}-harness Way 2. UTM-tracked → Supabase x_marketing_clicks. Use when triggered by `anicca-x-build-in-public-daily` 07:00 JST, `anicca-x-painpoint-daily` 12:00 JST, `anicca-x-cold-dm-daily` 14:00 JST, `anicca-x-promote-monthly` 1st 10:00 JST.
metadata:
  tags: x, twitter, marketing, web-app, build-in-public, cold-dm, postiz, {{profile.lateness.stakeholders.channel}}-harness, apify
  requires:
    bins: [bash, jq, curl, {{profile.lateness.stakeholders.channel}}-harness]
    env: [POSTIZ_API_KEY, APIFY_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]
---

# anicca-webapp-x-marketing

Web app には **X が一番効く** (TikTok だけでは認知→ブラウザ移動が弱い)。X で 5 channel 同時運用。

## 5 channels

| Channel | content | freq | cron |
|----|----|----|----|
| **A. Build in Public** | 昨日数字 + 開発内容 + ハマり + 今日の挑戦 | 毎日 07 JST (4 tweets) | `anicca-x-build-in-public-daily` |
| **B. Pain-Point Thread** | 1 web app / 日 rotation。ICP 共感 hook → 既存ツール限界 → 自分の解 = the app → CTA + UTM | 毎日 12 JST (4 tweets) | `anicca-x-painpoint-daily` |
| **C. UGC Repost** | mention/quote 即 thank-you reply | event-driven | `anicca-x-ugc-monitor-realtime` |
| **D. Cold DM** | apify Twitter scraper で ICP 50 件抽出 + DM 自動送信 | 毎日 14 JST × 50 件 | `anicca-x-cold-dm-daily` |
| **E. Promoted Post** | 過去 30 日の Channel B 勝ち thread を $50 boost | 月初 | `anicca-x-promote-monthly` |

## 7 web apps rotation queue

| Week | App | URL | ICP | 痛み |
|----|----|----|----|----|
| 1 | Letter | aniccaai.com/letter | mindfulness 興味 knowledge worker | 朝の一言 |
| 2 | GlowUp AI | TBD | 美容意識 20-30 代 | 自撮り改善 |
| 3 | ColdCraft | TBD | sales / founder | cold {{profile.lateness.stakeholders.channel}} 文面 |
| 4 | SignatureCraft | TBD | freelancer | プロらしい署名 |
| 5 | DeepWork.fm | TBD | knowledge worker | 集中音楽 |
| 6 | ClearPDF | TBD | researcher / student | PDF 整理 |
| 7 | Anicca iOS | aniccaai.com/affirmation-app | mindfulness habit | 1 日 1 nudge |

`state/rotation.json` で current_week を管理。日次 cron が +1 進めて 8 で 1 に戻す。

## UTM convention

```
?utm_source=x
&utm_medium=thread|dm|promoted
&utm_campaign=<app-slug>-<yyyy-mm>
&utm_content=<channel-A|B|C|D|E>
```

landing が `/api/track-utm` に POST → Supabase `x_marketing_clicks`:

```sql
CREATE TABLE x_marketing_clicks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  app_slug TEXT NOT NULL,
  utm_source TEXT, utm_medium TEXT, utm_campaign TEXT, utm_content TEXT,
  landing_path TEXT,
  referrer TEXT,
  ip_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  converted_at TIMESTAMPTZ,
  conversion_type TEXT  -- signup | trial | paid
);
```

## Daily flow (Channel A — Build in Public 07 JST)

```
1. fetch dashboard.json (yesterday's snapshot)
2. fetch git log (last 24h commits) — top 1 highlight
3. mkdir -p state/threads state/dms state
4. read state/yesterday-blocker.md (skill が逐次書く)
5. compose 4-tweet thread:
   T1: 数字 (MRR / sub / followers diff)
   T2: 開発内容 (1 thing shipped)
   T3: ハマり + 解
   T4: 今日の挑戦 + CTA "github.com/Daisuke134/anicca"
6. POST Postiz /public/v1/posts → schedule for 07 JST
7. save state/threads/<yyyy-mm-dd>-bip.json (post_id, urls)
```

## Daily flow (Channel B — Pain-Point 12 JST)

```
1. read state/rotation.json → current_app
2. claude が ICP 痛み + app の解を 4 tweet 以内で書く
3. each tweet 280 chars 以内、最後に CTA + UTM URL
4. POST Postiz → 12 JST 投稿
5. save state/threads/<yyyy-mm-dd>-painpoint-<app>.json
6. rotation.json: current_week +=1, mod 7
```

## Daily flow (Channel D — Cold DM 14 JST)

```
1. apify clockworks/twitter-search-scraper で ICP keyword 検索
   ex: "tired of writing cold {{profile.lateness.stakeholders.channel}}s" "need help with deep work playlists"
2. top 50 author profiles 取得
3. for each:
   a. {{profile.lateness.stakeholders.channel}}-harness Way 2 → x.com/<handle>/messages
   b. DM template (app-specific) auto-fill
   c. send
4. log to state/dms/<handle>-<yyyy-mm-dd>.json (sent_at, app, status)
5. dedup: 30 日以内に同 handle に DM 済なら skip
```

## DM templates (per app, per ICP)

| app | DM body (max 1000 char) |
|----|----|
| ColdCraft | "Hey 👋 saw your post about cold {{profile.lateness.stakeholders.channel}} rejection. Built ColdCraft (tiny tool) — does the writing for you. Free trial here: <utm-url>. Built it because I was bad at this too. — Anicca team" |
| DeepWork.fm | "Hey, your post about study music caught my eye. We made deepwork.fm — Buddhist ambient + frequencies, no ads. Free: <utm-url>. Hope it helps." |
| Letter | "Saw your post about morning routines — try Anicca Letter, 1 sentence/day in your inbox. Free for first month: <utm-url>" |
| SignatureCraft | "Your DM signature game is solid. Built SignatureCraft for freelancers who want it polished without 30 min/day: <utm-url>" |

## Cron registration

| name | schedule | script |
|----|----|----|
| `anicca-x-build-in-public-daily` | `0 7 * * *` JST | `bash scripts/bip.sh` |
| `anicca-x-painpoint-daily` | `0 12 * * *` JST | `bash scripts/painpoint.sh` |
| `anicca-x-cold-dm-daily` | `0 14 * * *` JST | `bash scripts/dm.sh` |
| `anicca-x-promote-monthly` | `0 10 1 * *` JST | `bash scripts/promote.sh` |

## State files

| file | content |
|----|----|
| `state/rotation.json` | `{"current_week": 1, "last_run": "2026-05-06"}` |
| `state/threads/<date>-<channel>.json` | post_id + URLs + impressions + clicks |
| `state/dms/<handle>-<date>.json` | sent_at, app, dm_id, status |
| `state/yesterday-blocker.md` | skill が前日トラブル要約 (BIP T3 用) |
| `state/winner-thread.json` | promoted-post 候補 (impressions 降順) |

## KPI (5/31 deadline)

| 指標 | start | target |
|----|----|----|
| follower 数 | 1k | 3k |
| daily impressions | 1k | 30k |
| web app signup from X | 0 | 100/月 |
| 月収 from X 流入 | $0 | $500-5,000 |

## Manual run

```bash
bash ~/.openclaw/skills/anicca-webapp-x-marketing/scripts/bip.sh
DRY_RUN=true bash ~/.openclaw/skills/anicca-webapp-x-marketing/scripts/painpoint.sh
bash ~/.openclaw/skills/anicca-webapp-x-marketing/scripts/dm.sh
```

# FIX by skill-fixer 2026-05-09:
# 原因: ディレクトリ未作成と完了待ちが長すぎると cron が timeout しやすかった。
# 修正: `mkdir -p` と短い完了待ち上限を明示した。
