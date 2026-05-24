---
name: reelfarm
description: Create TikTok slideshows, manage automations, and publish content using the ReelFarm API. Use when the user mentions ReelFarm, TikTok slideshows, slideshow automations, TikTok publishing, content scheduling, or creating social media content.
---

# ReelFarm

ReelFarm lets you create and auto-publish TikTok slideshows using natural language. Describe what you want — the topic, tone, number of slides, images, schedule — and ReelFarm generates the content, renders it into a video, and publishes it to TikTok.

You can use this skill to interact with ReelFarm entirely from Claude Code, without ever touching the web UI.

## Authentication

All API requests require a Bearer token. Get your API key from your ReelFarm dashboard at **Settings → API Keys**.

```
Authorization: Bearer <your-api-key>
```

**Base URL:** `https://reel.farm/api/v1`

Include both headers on every request:

```bash
curl -X POST https://reel.farm/api/v1/slideshows/generate \
  -H "Authorization: Bearer rf_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"additional_context": "5 habits that changed my morning routine, casual tone, 6 slides"}'
```

---

## Core Concepts

### Slideshow

A TikTok post composed of **slides**. Each slide has a background image and text overlays. When you generate a slideshow, ReelFarm's AI creates the text content, selects or generates images, and assembles everything into a publishable video.

Slideshows go through these statuses:
- `draft` — created but not yet rendered
- `processing` — video is being rendered
- `completed` — ready to publish or already published
- `failed` — something went wrong during rendering

### Automation

A recurring schedule that generates a **new unique slideshow** and publishes it to your connected TikTok account. Think of it as a cron job for content creation.

Each automation can have one or more **jobs** — individual schedules. For example, "post every weekday at 9am and 5pm" would be one automation with two jobs.

### Slide

One frame of a slideshow. Contains:
- A background image (from your collection, AI-generated, or from a URL)
- One or more text overlays (TextItems)
- An aspect ratio (default `4:5`)
- A display duration (default 4 seconds)

### TextItem

A text overlay on a slide. You control:
- The text content
- Position on the slide (`x`, `y` coordinates)
- Size (`width`, `height`)
- Font (`TikTok Display Medium`, `Bebas Neue`, `CormorantGaramond-Regular`, `CormorantGaramond-Italic`)
- Style (`outline`, `whiteBg`, `blackBg`, `white_background`, `black_background`, `white_50_background`, `black_50_background`)
- Font size (e.g. `14px`)

### Product

A product or niche you're creating content about. When you generate slideshows, the product context guides the AI's tone and topic — but the AI is trained to create authentic, emotional content rather than marketing copy. The product name is **never** mentioned in the generated slides.

### Collection

A curated set of images you upload to use as slide backgrounds. You can create collections organized by theme, product, or campaign.

### TikTok Account

A TikTok account you've connected via OAuth through the ReelFarm dashboard. This is where your slideshows get published.

---

## Workflows

### 1. Create and publish a one-off slideshow

Generate a standalone slideshow from a natural language prompt. No automation, product, or template required — just describe what you want.

```
Step 1: Generate the slideshow (only additional_context is required)
POST /api/v1/slideshows/generate
{
  "additional_context": "5 habits that changed my morning routine, casual first-person tone, 6 slides, SMALL font for body text"
}
→ 201 { slideshow_id, status: "processing", message: "..." }
(returns immediately — generation runs in the background)

Optional: provide your own images (0-indexed, maps to slides by position):
POST /api/v1/slideshows/generate
{
  "additional_context": "5 habits that changed my morning routine",
  "images": ["https://example.com/slide0.jpg", "https://example.com/slide1.jpg", ...]
}

Step 2: Poll for progress (generation + rendering takes 30-90s)
GET /api/v1/slideshows/{slideshow_id}/status
→ { slideshow_id, status: "generating", video_id: null, video_status: null }
→ { slideshow_id, status: "rendering", video_id: "67890", video_status: "Processing slideshow..." }
→ { slideshow_id, status: "completed", video_id: "67890", video_status: "Finished" }

Step 3: Once status is "completed", get the video with rendered slide images
GET /api/v1/videos/{video_id}
→ { video_id, slideshow_images: [{ id: 0, image_url: "..." }, ...], status: "completed" }

Step 4 (optional): Publish the video to TikTok
POST /api/v1/videos/{video_id}/publish
{ "post_mode": "DIRECT_POST" }
→ 202 { message: "TikTok publish started" }

To get the rendered slide image URLs, look at the video's slideshow_images array:
GET /api/v1/videos/{video_id}
→ { slideshow_images: [{ id: 0, image_url: "https://slides.reel.farm/..." }, { id: 1, image_url: "..." }, ...] }
```

### 1b. Create a slideshow with direct slide control

Create a slideshow by specifying every slide's image, text items, styling, and positioning directly — no AI generation. Use this when you want full, granular control over every slide.

```
Step 1: Create the slideshow with explicit slides
POST /api/v1/slideshows/create
{
  "slides": [
    {
      "image_url": "https://example.com/slide0.jpg",
      "text_items": [
        {
          "text": "5 habits that changed my morning routine",
          "font_size": "extra_large",
          "text_style": "outline"
        }
      ]
    },
    {
      "image_url": "https://example.com/slide1.jpg",
      "text_items": [
        {
          "text": "1. Wake up at 5am",
          "font_size": "medium",
          "text_style": "outline"
        },
        {
          "text": "the hardest part is getting out of bed but once you do everything changes",
          "font_size": "small",
          "text_style": "outline"
        }
      ]
    }
  ],
  "aspect_ratio": "4:5",
  "text_position": "center",
  "duration": 4
}
→ 201 { slideshow_id, status: "processing", message: "..." }
(returns immediately — rendering runs in the background, no AI generation)

Step 2: Poll for progress (rendering only, takes 15-45s — faster than generate)
GET /api/v1/slideshows/{slideshow_id}/status
→ { slideshow_id, status: "rendering", video_id: "67890", video_status: "Processing slideshow..." }
→ { slideshow_id, status: "completed", video_id: "67890", video_status: "Finished" }

Step 3+: Same as workflow 1 — get the video, optionally publish to TikTok.
```

Grid layout example (2x2 grid with 4 images on a slide):
POST /api/v1/slideshows/create
{
  "slides": [
    {
      "image_urls": [
        "https://example.com/img1.jpg",
        "https://example.com/img2.jpg",
        "https://example.com/img3.jpg",
        "https://example.com/img4.jpg"
      ],
      "image_layout": "2:2",
      "text_items": [
        { "text": "my 4 favorite outfits this week", "font_size": "large", "text_style": "outline" }
      ]
    }
  ]
}

Available image_layout values:
- "single" (default) — one image per slide, use image_url
- "1:2" — 1 column, 2 rows (2 images)
- "1:3" — 1 column, 3 rows (3 images)
- "2:1" — 2 columns, 1 row (2 images)
- "2:2" — 2 columns, 2 rows (4 images)

When using a grid layout, provide image_urls (array) instead of image_url.
```

**Key differences from `/slideshows/generate`:**
- You provide the exact text for each slide — no AI writes the content
- You choose `text_position` as `"top"`, `"center"`, or `"bottom"` — no raw x/y coordinates needed
- Text width, font sizes, styles, and fonts are set per text item
- Rendering is faster because there's no AI generation step
- Each slide can override `aspect_ratio` and `text_position` individually
- Grid layouts (`"1:2"`, `"1:3"`, `"2:1"`, `"2:2"`) supported per slide via `image_layout` + `image_urls`

### 2. Set up a recurring automation

Create an automation that generates and publishes new content on a schedule.

```
Step 1: List your TikTok accounts (to get the account ID)
GET /api/v1/tiktok/accounts
→ { accounts: [{ tiktok_account_id, account_name, account_username, account_image }] }

Step 2: Create the automation
POST /api/v1/automations
{
  "tiktok_account_id": "your-tiktok-account-id",
  "schedule": [
    { "cron": "0 14 * * *" }
  ],
  "title": "Fitness motivation posts",
  "slideshow_hooks": [
    "5 habits that changed my fitness journey",
    "how I finally got consistent with the gym"
  ],
  "style": "The first slide should have 1 text item...",
  "narrative": "Create content about fitness for...",
  "language": "English",
  "num_of_slides": 6
}
→ 201 { automation_id, status: "active", schedule: [{ job_id, cron }], ... }
```

The `style` field is a detailed prompt controlling text items, fonts, sizing, positioning, and tone for the generated slides. The `slideshow_hooks` are the rotating topics/hooks the AI picks from each run.

Each time the automation fires, it generates brand new content (never repeats previous topics from the last 20 runs), renders a video, and publishes to TikTok.

### 3. Manage existing automations

```
List automations:
GET /api/v1/automations
→ { automations: [{ automation_id, title, status, schedule, slideshow_hooks, ... }] }

Get a single automation:
GET /api/v1/automations/{automation_id}

Update automation settings (individual fields merge into existing data):
PATCH /api/v1/automations/{automation_id}
{ "slideshow_hooks": ["new hook 1", "new hook 2"], "style": "updated style..." }

You can update any single field — e.g. just "style", just "language",
just "image_settings": { "body_grid_format": "1:3" } — without replacing the rest.

Pause an automation:
PATCH /api/v1/automations/{automation_id}
{ "action": "pause" }

Resume an automation:
PATCH /api/v1/automations/{automation_id}
{ "action": "unpause" }

Delete an automation:
DELETE /api/v1/automations/{automation_id}

Trigger a one-off run (generate a slideshow using the automation's settings):
POST /api/v1/automations/{automation_id}/run
{ "hook": "optional specific hook text", "mode": "export" }
→ 202 { message, automation_id, status: "processing" }

If "hook" is omitted, the AI picks from the automation's slideshow_hooks list.
mode "export" = full video, "draft_only" = slideshow draft only.

IMPORTANT — Finding the video from a triggered run:
The /run endpoint starts an async process, so there is no video_id in the response.
To find the video it produces:
1. Note the current time BEFORE calling /run.
2. Poll GET /api/v1/videos?automation_id={automation_id}&created_after={noted_time}&limit=1
3. Wait for status to change from "processing" to "completed" (or "failed").
Using created_after ensures you only see videos created after your trigger.
```

### 3b. Manage automation schedules

Schedule jobs are managed separately from the automation config. Each job has its own `job_id` and cron expression.

```
Add a new schedule:
POST /api/v1/automations/{automation_id}/schedule
{ "cron": "0 18 * * *" }

Update a schedule:
PATCH /api/v1/automations/{automation_id}/schedule
{ "job_id": "...", "cron": "30 14 * * *" }

Batch update/delete schedules:
PATCH /api/v1/automations/{automation_id}/schedule
{ "actions": [
    { "type": "update", "job_id": "...", "cron": "0 15 * * *" },
    { "type": "delete", "job_id": "..." }
  ]
}

Delete a schedule:
DELETE /api/v1/automations/{automation_id}/schedule
{ "job_id": "..." }
```

### 4. View and publish generated videos

After an automation runs (or you trigger a one-off with `/run`), the rendered output appears in the videos list.

```
List all videos (optionally filter by automation, status, or date range):
GET /api/v1/videos?automation_id={automation_id}&status=completed&created_after=2026-03-24T00:00:00Z&created_before=2026-03-25T00:00:00Z
→ { videos: [{ video_id, automation_id, status, preview_url, video_url, slideshow_images, post_id, tiktok_publish_status }], total, limit, offset }

Get a single video (includes slideshow_images and tiktok_publish_status):
GET /api/v1/videos/{video_id}

Publish a video to TikTok (uses the automation's TikTok settings):
POST /api/v1/videos/{video_id}/publish
{ "post_mode": "DIRECT_POST" }
→ 202 { message, video_id, automation_id, status: "processing" }

post_mode is optional: "DIRECT_POST" publishes immediately, "MEDIA_UPLOAD" saves as TikTok draft.

Get TikTok analytics for a specific published video:
GET /api/v1/videos/{video_id}/analytics
→ { post_id, video_id, title, caption, view_count, like_count, comment_count, share_count, bookmark_count,
    tiktok_account_id, account_username, account_name, event, publish_type, published_at }
(Only works if the video has been published — post_id must be present)
```

### 5. Check your TikTok analytics

```
List all TikTok posts with analytics:
GET /api/v1/tiktok/posts?timeframe=30
→ {
    posts: [{ post_id, video_id, title, caption, view_count, like_count, comment_count, share_count, bookmark_count,
              tiktok_account_id, account_username, account_name, event, publish_type, published_at }],
    statistics: { total_posts, total_views, total_likes, total_comments, total_shares, total_bookmarks },
    timeframe, sort, limit, offset
  }

Sort by engagement (views, likes, shares, comments, bookmarks):
GET /api/v1/tiktok/posts?sort=views&timeframe=all    ← most viewed of all time
GET /api/v1/tiktok/posts?sort=likes&timeframe=7      ← most liked this week

Filter by TikTok account (use GET /api/v1/tiktok/accounts to find the ID first):
GET /api/v1/tiktok/posts?tiktok_account_id=tt_abc123&timeframe=7

List connected TikTok accounts:
GET /api/v1/tiktok/accounts
→ { accounts: [{ tiktok_account_id, account_name, account_username, account_image }] }
```

### 6. Browse the slideshow library

Search real TikTok slideshows by niche, slide text, product medium, or audience region. Great for finding inspiration or seeing what's working in a specific space.

```
List all available niches:
GET /api/v1/library/niches
→ { niches: [{ name, profile_count }], total }

Search profiles and their slideshows (at least one filter required, max 3 per page):
GET /api/v1/library?niche=fitness
GET /api/v1/library?q=morning+routine       ← search slide text
GET /api/v1/library?niche=spirituality&region=US
GET /api/v1/library?audience_region=PH       ← profiles with audience in Philippines
GET /api/v1/library?product_medium=digital+product
→ { profiles: [{ profile_id, username, nickname, bio, avatar_url, follower_count,
     niche, product_medium, region, audience_regions,
     slideshows: [{ index, views, likes, bookmarks, image_count, images, region }] }],
   total, limit, offset }

Get a single profile with full details:
GET /api/v1/library/profiles/{profile_id}
→ same as above + following_count, link_in_bio
```

### 7. Search Pinterest for images

Search Pinterest for image inspiration or to find background images for your slideshows. Returns full-resolution image URLs, paginated up to 5 pages per search.

```
Search for images:
GET /api/v1/pinterest/search?q=aesthetic+coffee
→ { images: ["https://i.pinimg.com/originals/...", ...], cursor: "eyJj...", has_more: true, page: 1, total_pages_allowed: 5 }

Get the next page:
GET /api/v1/pinterest/search?q=aesthetic+coffee&cursor=eyJj...
→ { images: [...], cursor: "eyJk...", has_more: true, page: 2, total_pages_allowed: 5 }

...up to page 5. After that, cursor is null and has_more is false.
```

The returned `images` array contains direct URLs to full-resolution Pinterest images. You can use these URLs directly in `/api/v1/slideshows/create` as `image_url` or `image_urls` values, or in `/api/v1/slideshows/generate` via the `images` array.

**Tip — Describing images with a vision model:**
If you have an OpenAI API key, Gemini API key, or Anthropic API key available, you can pass the Pinterest image URLs to a fast vision model (e.g. `gpt-4o-mini`, `gemini-2.0-flash`, or `claude-3-5-haiku`) to get a text description of what's in each image. This lets you preview and filter images before using them in a slideshow — useful when you want to pick the best images for your slides without manually viewing each one.

### 8. Check your account

```
GET /api/v1/account
→ { name, {{profile.lateness.stakeholders.channel}}, credits, user_id, cancelled, next_reset_date,
    subscription_tier, ai_credits, purchased_credits }
```

---

## API Reference

For complete endpoint documentation including request/response schemas, see [api-reference.md](api-reference.md).

---

## The `additional_context` Prompt

The `additional_context` field (used in `POST /api/v1/slideshows/generate` and as the `style` field in automations) is the most powerful control you have. It's a detailed natural-language prompt that tells the AI exactly how to structure every slide, text item, font, position, tone, and content direction.

**You can control all of the following in a single prompt:**

### Slide Count
Specify the exact number of slides. The AI respects this strictly.
- `"I want EXACTLY 6 slides (NO MORE THAN 6 TOTAL SLIDES)"`

### Text Items Per Slide
How many text items each slide should have, and what each one should contain.
- `"The first slide should have 1 text item"` 
- `"All other slides should have 3 text items"`
- `"2 text items on each slide: a heading and a body"`

### Font Sizes
Available sizes (smallest to largest): `extra extra small`, `extra small`, `small`, `medium`, `large`, `extra large`
- `"first text item in EXTRA LARGE font size"`
- `"body text in SMALL font size"`
- `"heading in MEDIUM, supporting text in EXTRA SMALL"`

### Text Width
Control how wide text items are on the slide (percentage of slide width).
- `"90% width"`, `"70% width"`, `"60% width"`, `"full width"`

### Text Position
Where text items sit vertically on the slide.
- `"Top 1/3rd of the slide"` — text near the top
- `"Middle 1/3rd"` or `"centered"` — text in the middle
- `"Bottom 1/3rd of the slide"` — text near the bottom

### Text Styles
The visual treatment of the text. Each text item can have its own style.
- `"outline"` — white text with black border (default)
- `"white text"` — plain white
- `"black text"` — plain black
- `"yellow text"` — pastel yellow
- `"white background"` — white background behind text
- `"black background"` — black background behind text
- `"light white background"` — semi-transparent white (50% opacity)
- `"light black background"` — semi-transparent black (50% opacity)

### Fonts
- `"default"` / `"tiktok"` — TikTok Display Medium
- `"condensed bold"` / `"bebas neue"` — Bebas Neue (big bold condensed)
- `"serif"` — Cormorant Garamond Regular
- `"serif italic"` — Cormorant Garamond Italic

### Writing Tone & Style
Describe the voice, perspective, reading level, and content direction in plain language.
- `"Written in a motivational yet conversational tone using FIRST person 'I' perspective"`
- `"Write at a 7th grade reading level"`
- `"Use short, punchy sentences"`
- `"ALL TEXT SHOULD BE LOWERCASE"`

### Per-Slide Content Direction
You can describe what each slide should cover.
- `"slide 1 being the hook, slides 2-6 each covering one of the 5 ways"`
- `"The 3rd or 4th slide MUST mention 'Product Name' as the solution"`

### Word Count
Specify word count per text item.
- `"1-2 words for the heading"`, `"5-10 words for the body text"`, `"10+ words"`

---

### Full Example

Here's a real `additional_context` prompt that controls everything:

```
I want EXACTLY 6 slides (NO MORE THAN 6 TOTAL SLIDES) about 'ways i stopped
entertaining situationships for good' with the first slide text saying
'5 ways i stopped entertaining situationships for good:'.

The first slide should have 1 text item in EXTRA LARGE font size, all lowercase.

All other slides (slides 2-6) should have 3 text items in SMALL font size and
70% width: first text item is a numbered heading like "1. [title]" (5-7 words)
followed by 2 short supporting text items (about 10 words each). The 2nd text
item should reaffirm the problem, and the 3rd text item should be a quick
solution. ALL TEXT SHOULD BE LOWERCASE. ALL TEXT ITEMS SHOULD BE OUTLINE TEXT
STYLE AND ON THE TOP 1/3RD OF THE SLIDE.

Written in a motivational yet conversational tone using FIRST person "I"
perspective. Write at a 7th grade reading level in a style that sounds like a
supportive friend. Use short, punchy sentences, the writing should feel
authentic and conversational.

The slideshow should have EXACTLY 6 slides total with slide 1 being the hook
and slides 2-6 each covering one of the 5 ways. DO NOT create more than
6 slides - stop after slide 6.
```

### Minimal Example

At its simplest, you can just describe the topic and basic structure:

```
I want 5 slides. 1 text item on first slide that says "5 habits that changed
my morning routine", 2 text items on the rest. The first slide text item should
be large font size. On the rest, the first text item should be medium size with
1-2 words, the second text item should be small and 5-10 words total. All text
items should be on the top 1/3rd of the slide, and all text items should be 80%
width. Use a casual, conversational tone with short punchy sentences.
```

---

## Tips

- **Cron schedules are stored in Pacific Standard Time (PST/PDT).** The `cron_schedule` in each job uses Pacific time. For example, 9am PST = `0 9 * * *`, 5pm PST = `0 17 * * *`.

- **Polling for progress:** After generating a slideshow, poll `GET /api/v1/slideshows/{slideshow_id}/status` every 5–10 seconds. The `status` field progresses through `draft` → `generating` → `rendering` → `completed`. Once `completed`, use the `video_id` from the response to fetch the finished video. The full pipeline typically takes 30–90 seconds.

- **The AI never mentions your product by name.** This is by design. The product context shapes the *tone and topic*, but the generated text reads like authentic, organic content — not ads.

- **Each automation run produces unique content.** The AI tracks your last 20 slideshows and ensures new content never repeats the same topics, items, or angles.

- **Credit usage:** Each slideshow generation costs 1 credit. Check your balance with `GET /api/v1/account`.

- **The `style` field on automations is the same format as `additional_context`.** When creating or updating an automation, the `style` field accepts the exact same prompt format documented above. The difference is that for automations, the `slideshow_hooks` list provides the topic/hook, and the `style` controls everything else (text structure, fonts, positioning, tone). For standalone slideshows via `/api/v1/slideshows/generate`, the `additional_context` field covers both the topic AND the formatting in a single prompt.

---

## Cron Mode: Daily Metrics Iteration (LOOP A)

Triggered by cron `reelfarm-metrics-loop` daily at 04:00 JST.

**API Key:** `rf_pDYHO4OHekj7LGGyt4wVSsWA69A3kdxHR0gmMxg0CHg`
**Base URL:** `https://reel.farm/api/v1`

### 手順

1. **クレジット確認:** `GET /api/v1/account` — 残高1000未満なら警告付きで続行
2. **アカウントマッピング構築:** `GET /api/v1/tiktok/accounts` → tiktok_account_id → username のマップを作る（automationレスポンスにusernameが含まれないため必須）
3. **全アクティブautomation取得:** `GET /api/v1/automations` → `status: "active"` のものを全て抽出
4. **各automationについて以下を実行:**
   a. `GET /api/v1/tiktok/posts?tiktok_account_id={id}&timeframe=7&sort=views`
      ※ timeframe は日数指定だがAPIは最大20件程度を返す。timeframe=7 で直近1週間の上位投稿を取得
   b. 投稿が0件ならスキップ（新規ウォームアップ中の可能性）
   c. **エンゲージメントスコア算出:**
      `score = views * 0.4 + likes * 0.3 + comments * 0.2 + shares * 0.1`
   d. **上位20%と下位20%のフックを特定**
   e. `GET /api/v1/automations/{automation_id}` で現在のhooksを取得
   f. **hooks更新:** 下位フックを削除し、上位フックのパターンに基づく新フックを生成
      `PATCH /api/v1/automations/{automation_id} { "slideshow_hooks": [...] }`
      - style は週1回のみ変更（頻繁な変更は逆効果）
      - フック最小数: 5個（削除で5未満にならないよう新フックで補填）
   g. PATCH失敗時はログに記録して次のautomationへ続行
5. **結果保存:** `~/.openclaw/workspace/reelfarm/metrics/YYYY-MM-DD.json`（ディレクトリがなければ作成）
   ```json
   {
     "date": "YYYY-MM-DD",
     "credits_remaining": 9000,
     "automations_processed": 7,
     "accounts": [
       {
         "automation_id": "...",
         "account": "anicca.en",
         "posts_analyzed": 12,
         "top_hooks": ["hook1", "hook2"],
         "bottom_hooks": ["hook3"],
         "hooks_replaced": 2,
         "total_views_7d": 45000
       }
     ],
     "total_hooks_replaced": 5
   }
   ```
6. **結果保存のみ:** `~/.openclaw/workspace/reelfarm/metrics/YYYY-MM-DD.json` を更新して終了。外部送信はしない。

### 重要ルール
- 全アクティブautomationを動的に処理（IDハードコード禁止）
- Step 2 のアカウントマッピングは必須（APIレスポンスにusernameがないため）
- 各automationは独立にイテレート（EN/JP/ES を結合しない）
- フック生成時: 勝ちパターンの感情・構造・トーンを分析して新フックを書く

---

## Cron Mode: Weekly Library Exploration (LOOP B)

Triggered by cron `reelfarm-library-loop` every Sunday at 04:30 JST.

**API Key:** `rf_pDYHO4OHekj7LGGyt4wVSsWA69A3kdxHR0gmMxg0CHg`
**Base URL:** `https://reel.farm/api/v1`

### 実行前チェック

- `GET /api/v1/account` でクレジット確認（1000未満なら警告付きで続行）
- キュー確認: `POST /slideshows/generate` が `CONCURRENT_LIMIT` エラーを返す場合、新automation作成はスキップしてSlackに「キュー詰まりのためスキップ」と報告

### 手順

1. **利用可能ニッチ確認:** `GET /api/v1/library/niches` → 返ってきたニッチ名を確認
   関連ニッチ候補: spirituality, mental health, affirmation, meditation, wellness, self-improvement, mindfulness, productivity
   ※ ニッチによってはライブラリに0件の場合あり（self-improvement, mindfulness は0件だった実績）。存在するニッチのみ使う
2. **各ニッチのバイラルスライドショー発見:**
   `GET /api/v1/library?niche={niche}`
   → プロフィールごとのスライドショーをviews/likesでソート（views表記は "4.3M", "53.1K" 等。数値に変換して比較）
   → 上位3件のスライドショー構造を分析:
   - スライド枚数
   - テキストスタイル
   - 画像の雰囲気
   - フックのパターン
3. **Pinterest画像検索:**
   バイラルスライドショーの画像テーマに基づいて:
   `GET /api/v1/pinterest/search?q={aesthetic+keyword}`
4. **投稿枠チェック:**
   `GET /api/v1/automations` → 全automationを取得
   各アカウントの投稿枠を計算:
   - 1アカウントあたりの投稿上限 = 6回/日
   - 現在の投稿数 = そのアカウントに紐づく全automationのschedule（cron）数の合計
   - 投稿枠 = 6 - 現在の投稿数
   - 合計automation数が20個以上なら最低パフォーマンスのものを1つ削除してから作成
5. **新automation作成（最大2個/週）:**
   投稿枠ありのアカウントがある場合のみ:
   ```
   POST /api/v1/automations
   {
     "tiktok_account_id": "{投稿枠に余裕のあるアカウント}",
     "schedule": [{ "cron": "既存cronと30分以上ずらした時間" }],
     "title": "Auto-{niche}-{date}",
     "slideshow_hooks": [バイラルから模倣したフック 10-15個],
     "style": [バイラルから模倣したスタイルプロンプト],
     "language": "{EN or JP — アカウントに合わせる}",
     "num_of_slides": {バイラルと同じ枚数、通常5-7}
   }
   ```
   作成後に image_settings も設定:
   ```
   PATCH /api/v1/automations/{new_id}
   {
     "image_settings": {
       "auto_pull_images": true,
       "all_slides": "auto",
       "aspect_ratio": "4:5",
       "hook_grid_format": "single",
       "body_grid_format": "single"
     }
   }
   ```
   - 既存automationと同じフックを使わない
   - 最初7日はドラフトモード推奨（新ニッチのテスト）
6. **結果保存:** `~/.openclaw/workspace/reelfarm/library/YYYY-MM-DD.json`（ディレクトリがなければ作成）
   ```json
   {
     "date": "YYYY-MM-DD",
     "niches_scanned": 5,
     "niches_with_data": ["spirituality", "mental health"],
     "niches_empty": ["self-improvement", "mindfulness"],
     "viral_slideshows_found": 24,
     "top_viral": [
       {
         "niche": "spirituality",
         "username": "@slideofreality",
         "views": 29900000,
         "hook_pattern": "emotional 2nd person"
       }
     ],
     "posting_capacity": {
       "anicca.en4": {"current": 3, "max": 6, "available": 3},
       "anicca.jp4": {"current": 3, "max": 6, "available": 3}
     },
     "automations_created": [
       {
         "automation_id": "...",
         "title": "Auto-spirituality-2026-03-28",
         "account": "anicca.en5",
         "hooks_count": 12
       }
     ],
     "automations_deleted": []
   }
   ```
7. **結果保存のみ:** `~/.openclaw/workspace/reelfarm/library/YYYY-MM-DD.json` を更新して終了。外部送信はしない。

### 投稿枠フル時の対応
全アカウントの投稿枠がフルの場合、新automationは作成しない。state に理由だけ記録して終了する。

### 制約
| 制約 | 値 | 理由 |
|------|-----|------|
| 新automation数/週 | 最大2個 | 品質重視、クレジット節約 |
| 既存automationの最大数 | 20個 | 管理可能な範囲 |
| 同一アカウントへの投稿上限 | 6回/日 | TikTok API制限 |
| 投稿スケジュール | 既存cronと30分以上空ける | Gateway衝突回避 |

### 重要ルール
- 新automationは投稿枠に余裕のあるアカウントに割り当て（6投稿/日上限）
- image_settings は必ず auto_pull_images=true, all_slides="auto" で設定（コレクション使わない）
- 関連ニッチ以外は探索しない（ブランド整合性維持）
- 作成失敗時はログに記録して続行

# FIX by skill-fixer 2026-05-09:
# 原因: Slack 報告を前提にした古い記述が残り、cron 配信が Message failed になりやすかった。
# 修正: cron は結果保存のみ、外部送信なしに統一した。
