# ReelFarm API Reference

**Base URL:** `https://reel.farm/api/v1`

All requests require `Authorization: Bearer <api-key>` and `Content-Type: application/json`.

---

## Slideshows

### Generate a slideshow

Creates a new slideshow from a natural-language prompt. The AI generates text content, selects images, and rendering begins automatically. No product, template, or image collection is required — just describe what you want.

```
POST /api/v1/slideshows/generate
```

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `additional_context` | string | Yes | Detailed natural-language prompt that controls everything: topic, slide count, text items per slide, font sizes, text positions, text styles, fonts, width, word counts, writing tone, and per-slide content direction. See the "The `additional_context` Prompt" section in [SKILL.md](SKILL.md) for the full reference and examples. |
| `images` | string[] | No | 0-indexed array of image URLs to use as slide backgrounds. `images[0]` → slide 0, `images[1]` → slide 1, etc. If fewer images than slides, remaining slides use auto-selected images. |

All other settings use sensible defaults:
- Aspect ratio: `4:5`
- Template: `educational`
- Auto-pull images from Pinterest for any slides without a user-provided image
- Text on all slides: enabled
- Keep original aspect ratio: off

**Example request with custom images:**

```json
{
  "additional_context": "5 habits that changed my morning routine, casual first-person tone, 6 slides",
  "images": [
    "https://example.com/morning-coffee.jpg",
    "https://example.com/cold-shower.jpg",
    "https://example.com/journal.jpg",
    "https://example.com/meditation.jpg",
    "https://example.com/workout.jpg",
    "https://example.com/sunrise.jpg"
  ]
}
```

If `images` is omitted, all slides automatically get images sourced from Pinterest based on the slide content.

**Response (201):**

```json
{
  "slideshow_id": 12345,
  "status": "processing",
  "message": "Slideshow generation started. Poll GET /api/v1/videos to find the finished video."
}
```

The response returns immediately (~1-2 seconds). The full pipeline — AI content generation, image selection, and video rendering — runs asynchronously in the background.

**What happens after this call:**

1. The AI generates text content and selects images based on your prompt (takes 30-60 seconds).
2. The rendering pipeline produces a `video` record with the final `slideshow_images` (rendered slide images with text baked in).
3. Poll `GET /api/v1/slideshows/{slideshow_id}/status` every 5-10 seconds to track progress. Once `status` is `"completed"`, the `video_id` field will be present.

---

### Create a slideshow (direct control)

Creates a slideshow by specifying every slide's image, text, styling, and positioning directly. No AI generation — the content you provide is used exactly as-is. This gives you full granular control over every slide.

```
POST /api/v1/slideshows/create
```

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slides` | object[] | Yes | Array of slide objects (1–20 slides). See **Slide object** below. |
| `title` | string | No | Slideshow title (default `"API Slideshow"`) |
| `aspect_ratio` | string | No | Default aspect ratio for all slides (default `"4:5"`). Individual slides can override this. |
| `text_position` | string | No | Default vertical text position: `"top"`, `"center"`, or `"bottom"` (default `"center"`). Individual slides can override this. |
| `duration` | number | No | Seconds each slide is displayed (default `4`). |
| `is_bg_overlay_on` | boolean | No | Enable dark overlay on body slides (default `false`) |
| `is_bg_overlay_on_hook_image` | boolean | No | Enable dark overlay on the first (hook) slide (default `false`) |
| `background_opacity` | number | No | Overlay opacity 0–100 (default `20`) |
| `keep_original_aspect_ratio` | boolean | No | Use each image's native aspect ratio instead of the default (default `false`) |

**Slide object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image_url` | string | Conditional | URL of the background image for this slide. Required for single-image slides. For grid layouts, use `image_urls` instead. |
| `image_urls` | string[] | Conditional | Array of image URLs for grid layouts. Required when `image_layout` is set to a grid value. The number of URLs must match the grid cell count (e.g., 4 for `"2:2"`). For single-image slides, you can use either `image_url` or `image_urls[0]`. |
| `image_layout` | string | No | Image grid layout for this slide. Default `"single"`. Options: `"single"` (1 image), `"1:2"` (1 col × 2 rows, 2 images), `"1:3"` (1 col × 3 rows, 3 images), `"2:1"` (2 cols × 1 row, 2 images), `"2:2"` (2 cols × 2 rows, 4 images). |
| `text_items` | object[] | No | Array of text items to overlay on this slide. If omitted or empty, the slide has no text. |
| `aspect_ratio` | string | No | Override the global aspect ratio for this specific slide |
| `text_position` | string | No | Override the global text position for this slide (`"top"`, `"center"`, `"bottom"`) |

**TextItem object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | The text content to display |
| `font_size` | string | No | Named size or pixel value (default `"medium"` / `"12px"`). Named sizes: `"extra_extra_small"` (6px), `"extra_small"` (8px), `"small"` (10px), `"medium"` (12px), `"large"` (14px), `"extra_large"` (16px). Raw pixel values like `"14px"` or `"14"` also accepted. |
| `text_style` | string | No | Visual style (default `"outline"`). Options: `"outline"`, `"whiteText"`, `"blackText"`, `"yellowText"`, `"white_background"`, `"black_background"`, `"white_50_background"`, `"black_50_background"` |
| `font` | string | No | Font family. Options: `"TikTokDisplay-Bold"`, `"BebasNeue-Regular"`, `"CormorantGaramond-Regular"`, `"CormorantGaramond-Italic"`. If omitted, uses the default TikTok Display font. |
| `text_width` | string | No | Width of the text box as a percentage of the slide width. Examples: `"100%"`, `"80%"`, `"50%"`, `"full"`. If omitted, the system calculates an optimal width to avoid orphan words. |

**Example request:**

```json
{
  "slides": [
    {
      "image_url": "https://example.com/hook.jpg",
      "text_items": [
        {
          "text": "5 habits that changed my morning routine",
          "font_size": "extra_large",
          "text_style": "outline"
        }
      ]
    },
    {
      "image_url": "https://example.com/habit1.jpg",
      "text_items": [
        {
          "text": "1. Wake up at 5am",
          "font_size": "medium",
          "text_style": "outline",
          "font": "BebasNeue-Regular"
        },
        {
          "text": "the hardest part is getting out of bed but once you do everything changes",
          "font_size": "small",
          "text_style": "outline",
          "text_width": "90%"
        }
      ]
    },
    {
      "image_url": "https://example.com/cta.jpg",
      "text_items": []
    }
  ],
  "aspect_ratio": "4:5",
  "text_position": "center",
  "duration": 4,
  "is_bg_overlay_on": true,
  "background_opacity": 20
}
```

**Example request with grid layout:**

```json
{
  "slides": [
    {
      "image_url": "https://example.com/hook.jpg",
      "text_items": [
        { "text": "4 outfits I wore this week", "font_size": "extra_large" }
      ]
    },
    {
      "image_layout": "2:2",
      "image_urls": [
        "https://example.com/outfit1.jpg",
        "https://example.com/outfit2.jpg",
        "https://example.com/outfit3.jpg",
        "https://example.com/outfit4.jpg"
      ],
      "text_items": [
        { "text": "monday through thursday", "font_size": "medium", "text_style": "white_50_background" }
      ]
    },
    {
      "image_layout": "1:2",
      "image_urls": [
        "https://example.com/friday.jpg",
        "https://example.com/saturday.jpg"
      ],
      "text_items": []
    }
  ],
  "aspect_ratio": "4:5",
  "text_position": "bottom"
}
```

**Response (201):**

```json
{
  "slideshow_id": 12345,
  "status": "processing",
  "message": "Slideshow created and rendering started. Poll GET /api/v1/slideshows/12345/status to track progress."
}
```

**Key differences from `/slideshows/generate`:**

- No AI generation — you provide the exact text content for each slide
- Text positioning uses semantic labels (`"top"`, `"center"`, `"bottom"`) instead of raw pixel coordinates
- Rendering is faster (15–45s) because it skips the AI generation step (30–60s)
- You have full control over every text item's style, font, size, and width
- Slides without `text_items` (or with an empty array) render as image-only slides
- Grid layouts (`"1:2"`, `"1:3"`, `"2:1"`, `"2:2"`) are supported per slide — use `image_layout` + `image_urls`

**What happens after this call:**

1. The slideshow record is created in the database with your exact slide content.
2. The rendering pipeline produces a `video` record with the final `slideshow_images` (rendered slide images with text baked in).
3. Poll `GET /api/v1/slideshows/{slideshow_id}/status` every 5-10 seconds to track progress. Once `status` is `"completed"`, the `video_id` field will be present.

---

### Check slideshow generation status

Lightweight polling endpoint that returns the current status of a slideshow being generated.

```
GET /api/v1/slideshows/{slideshow_id}/status
```

**Response (200):**

```json
{
  "slideshow_id": 12345,
  "status": "rendering",
  "video_id": "67890",
  "video_status": "Downloading and processing images..."
}
```

| Field | Description |
|-------|-------------|
| `status` | Overall status: `"draft"` → `"generating"` → `"rendering"` → `"completed"` or `"failed"` |
| `video_id` | The video record ID (present once rendering starts). Use this with `GET /api/v1/videos/{video_id}` to get the final result. |
| `video_status` | Granular rendering progress from the video pipeline (e.g. `"Processing slideshow..."`, `"Creating slideshow video..."`, `"Adding music..."`, `"Finished"`) |

**Status flow:**

1. `draft` — slideshow record created, pipeline not started yet
2. `generating` — AI is generating text content and selecting images
3. `rendering` — content is ready, images are being rendered into slides/video
4. `completed` — done, video is ready
5. `failed` — something went wrong

**Getting the rendered image URLs:**

Once the video record is `completed`, its `slideshow_images` field contains the final rendered slides:

```json
{
  "video_id": "uuid-1234",
  "status": "completed",
  "slideshow_images": [
    { "id": 0, "image_url": "https://slides.reel.farm/encoded_email_processId/image_0.jpg" },
    { "id": 1, "image_url": "https://slides.reel.farm/encoded_email_processId/image_1.jpg" },
    { "id": 2, "image_url": "https://slides.reel.farm/encoded_email_processId/image_2.jpg" }
  ]
}
```

These are the fully rendered images with text overlays applied — ready for download or publishing.

---

## Automations

### Create an automation

Set up a recurring schedule that generates and publishes new slideshows automatically.

```
POST /api/v1/automations
```

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tiktok_account_id` | string | Yes | Target TikTok account (`account_id` from the `tiktok_accounts` table) |
| `schedule` | object[] | Yes | Array of `{ cron: "cron-expression" }` in Pacific time |
| `title` | string | No | Descriptive name for this automation |
| `product_id` | integer | No | Link to a product in the `products` table |
| `slideshow_hooks` | string[] | No | List of hook/topic templates the AI rotates through |
| `style` | string | No | Detailed natural-language prompt controlling text items per slide, font sizes, text positions, text styles, fonts, width, word counts, tone, and writing style. Same format as `additional_context` — see the "The `additional_context` Prompt" section in [SKILL.md](SKILL.md) for the full reference. |
| `narrative` | string | No | Content themes and listicle title templates for the AI |
| `language` | string | No | Language for generated content (default `"English"`) |
| `num_of_slides` | integer | No | Number of slides per generated slideshow |
| `tiktok_post_settings` | object | No | TikTok posting config (see below) |
| `image_settings` | object | No | Image collection and display config (see below) |

**`tiktok_post_settings` object:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `caption` | object | AI prompt | `{ mode: "prompt"\|"static", prompt_text: "...", static_text: "..." }` |
| `description` | object | AI hashtags | `{ mode: "prompt"\|"static", prompt_text: "...", static_text: "..." }` |
| `auto_post` | boolean | `true` | Auto-publish to TikTok when video is ready |
| `visibility` | string | `"PUBLIC_TO_EVERYONE"` | `PUBLIC_TO_EVERYONE`, `SELF_ONLY`, `MUTUAL_FOLLOW_FRIENDS`, `FOLLOWER_OF_CREATOR` |
| `auto_music` | boolean | `true` | Let TikTok add trending music |
| `post_mode` | string | `"MEDIA_UPLOAD"` | `MEDIA_UPLOAD` or `DIRECT_POST` |
| `allow_comments` | boolean | `true` | Allow comments on the post |
| `allow_duet` | boolean | `true` | Allow duets |
| `allow_stitch` | boolean | `true` | Allow stitches |

When `caption.mode` or `description.mode` is `"prompt"`, the `prompt_text` is sent to Claude AI along with the generated slide content to produce the caption/description. When `"static"`, the `static_text` is used as-is.

**`image_settings` object:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `first_slide` | object | `null` | `{ collection: "user_collection_123", mode: "collection", single_image: "img_id" }` |
| `all_slides` | string | `null` | Collection ID for body slide images (e.g. `"user_collection_456"`) |
| `aspect_ratio` | string | `"4:5"` | Default aspect ratio (`"4:5"`, `"9:16"`, `"1:1"`, etc.) |
| `is_bg_overlay_on` | boolean | `false` | Enable background overlay on body slides |
| `is_bg_overlay_on_hook_image` | boolean | `false` | Enable background overlay on hook slide |
| `background_opacity` | integer | `20` | Overlay opacity (0-100) |
| `keep_original_aspect_ratio` | boolean | `false` | Override default aspect ratio with each image's native ratio |
| `text_on_first_slide_only` | boolean | `false` | Only show text on the first (hook) slide |
| `no_text_on_slides` | boolean | `false` | Remove text from all slides |
| `auto_pull_images` | boolean | `false` | Auto-pull images from Pinterest |
| `auto_images_no_text` | boolean | `false` | No text on auto-pulled images |
| `disable_auto_image_for_first_slide` | boolean | `false` | Don't auto-pull for the hook slide |
| `hook_grid_format` | string | `"single"` | Grid layout for hook image (`"single"`, `"1:3"`, etc.) |
| `body_grid_format` | string | `"single"` | Grid layout for body images |
| `cta_slide` | object | `null` | CTA slide config: `{ check: bool, cta_collection_check: bool, cta_collection_id: string, image_id: string }` |

**Response (201):**

```json
{
  "automation_id": "a1b2c3d4-e5f6-...",
  "title": "Fitness motivation posts",
  "status": "active",
  "product_id": 42,
  "tiktok_account_id": "tt_abc123",
  "schedule": [
    { "job_id": "f7g8h9i0-...", "cron": "0 14 * * *" }
  ],
  "slideshow_hooks": ["5 habits that changed my fitness journey", "..."],
  "style": "The first slide should have...",
  "narrative": "Create content about fitness...",
  "language": "English",
  "num_of_slides": 6,
  "tiktok_post_settings": { ... },
  "image_settings": { ... },
  "created_at": "2026-03-24T10:00:00Z"
}
```

---

### List automations

```
GET /api/v1/automations
```

**Response (200):**

```json
{
  "automations": [
    {
      "automation_id": "a1b2c3d4-...",
      "title": "Fitness motivation posts",
      "status": "active",
      "product_id": 42,
      "tiktok_account_id": "tt_abc123",
      "schedule": [{ "job_id": "f7g8h9i0-...", "cron": "0 14 * * *" }],
      "slideshow_hooks": ["5 habits that...", "..."],
      "style": "...",
      "narrative": "...",
      "language": "English",
      "num_of_slides": 6,
      "tiktok_post_settings": { ... },
      "image_settings": { ... },
      "created_at": "2026-03-24T10:00:00Z"
    }
  ]
}
```

---

### Get a single automation

```
GET /api/v1/automations/{automation_id}
```

**Response (200):** Same shape as a single item in the list response.

---

### Update an automation

Update any combination of automation settings. To pause/unpause, use the `action` field instead.

```
PATCH /api/v1/automations/{automation_id}
```

**Request body (config update):**

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Update the automation title |
| `slideshow_hooks` | string[] | Replace the hooks list |
| `style` | string | Update the style prompt |
| `narrative` | string | Update the narrative prompt |
| `language` | string | Update the language |
| `num_of_slides` | integer | Update slide count |
| `tiktok_account_id` | string | Change target TikTok account |
| `tiktok_post_settings` | object | Update TikTok posting settings |
| `product_id` | integer | Change linked product |
| `image_settings` | object | Update image/collection settings |

**Request body (pause/unpause):**

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | `"pause"` or `"unpause"` |

**Response (200):** Returns the full updated automation object.

---

### Delete an automation

```
DELETE /api/v1/automations/{automation_id}
```

**Response (200):**

```json
{ "message": "Automation deleted" }
```

---

### Run an automation (one-off)

Trigger a one-off slideshow generation using the automation's saved settings (hooks, style, image settings, etc.). This does not affect the automation's cron schedule.

```
POST /api/v1/automations/{automation_id}/run
```

**Request body (all optional):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `hook` | string | _random from hooks list_ | Override the hook/topic for this single run |
| `mode` | string | `"export"` | `"export"` (generate video) or `"draft_only"` (generate slideshow draft only, no video) |

**Response (202):**

```json
{
  "message": "Slideshow generation started",
  "automation_id": "a1b2c3d4-...",
  "status": "processing",
  "mode": "export",
  "hook": null
}
```

> **Finding the video from a triggered run:** The `/run` endpoint starts an async process — no `video_id` is returned. To find the resulting video:
> 1. Note the current time **before** calling `/run`.
> 2. Poll `GET /api/v1/videos?automation_id={automation_id}&created_after={noted_time}&limit=1`.
> 3. Wait for its `status` to change from `"processing"` to `"completed"` (or `"failed"`).
>
> Using `created_after` ensures you only see videos created after your trigger — no risk of grabbing an older one.

The generation runs asynchronously. Once complete, a new video will appear in `GET /api/v1/videos?automation_id={automation_id}`.

---

### Manage automation schedules

Schedule jobs (cron entries) are managed via a sub-resource. Each job has its own `job_id` and cron expression in Pacific time.

#### Add a schedule job

```
POST /api/v1/automations/{automation_id}/schedule
```

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cron` | string | Yes | Cron expression in Pacific time (e.g. `"0 14 * * *"`) |

**Response (201):** Returns the full updated automation object.

---

#### Update a schedule job

```
PATCH /api/v1/automations/{automation_id}/schedule
```

**Request body (single job):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_id` | string | Yes | The job to update |
| `cron` | string | Yes | New cron expression |

**Request body (batch operations):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `actions` | object[] | Yes | Array of `{ type: "update"\|"delete", job_id: "...", cron: "..." }` |

**Response (200):** Returns the full updated automation object.

---

#### Delete a schedule job

```
DELETE /api/v1/automations/{automation_id}/schedule
```

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_id` | string | Yes | The job to remove |

**Response (200):** Returns the full updated automation object.

---

## Videos

Videos are the rendered output of slideshows. When an automation runs (or you trigger a one-off run), the system generates a slideshow draft, renders it into slide images, and optionally creates a video file. The video record in the `videos` table contains the final `slideshow_images` (S3 URLs of each rendered slide) and, if video export was enabled, a `video_url`.

### List videos

```
GET /api/v1/videos
```

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `automation_id` | string | Filter by automation (`created_by_cron_id`) |
| `status` | string | `"completed"`, `"processing"`, or `"failed"` |
| `created_after` | string | ISO 8601 timestamp — only return videos created after this time |
| `created_before` | string | ISO 8601 timestamp — only return videos created before this time |
| `limit` | number | Max results (default 20, max 100) |
| `offset` | number | Pagination offset |

**Response (200):**

```json
{
  "videos": [
    {
      "video_id": "uuid-1234",
      "automation_id": "a1b2c3d4-...",
      "status": "completed",
      "preview_url": "https://automated-content.s3.amazonaws.com/..._preview.png",
      "video_url": "https://automated-content.s3.amazonaws.com/....mp4",
      "slideshow_images": [
        "https://reelfarm-slideshows.s3.amazonaws.com/slide_0.png",
        "https://reelfarm-slideshows.s3.amazonaws.com/slide_1.png"
      ],
      "post_id": "7123456789",
      "tiktok_publish_status": {
        "published": true,
        "title": "Publish Complete",
        "message": ""
      },
      "created_at": "2026-03-24T14:00:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

- `post_id` — TikTok post ID. Present only if the video was published to TikTok.
- `tiktok_publish_status` — Publishing result. `published: true` means the TikTok upload succeeded. `null` if never published.

---

### Get a single video

```
GET /api/v1/videos/{video_id}
```

**Response (200):** Same shape as a single item in the list response (includes `tiktok_publish_status` and `post_id`).

---

### Get TikTok analytics for a video

Returns TikTok post analytics for a published video. The video must have been published (`post_id` must be present).

```
GET /api/v1/videos/{video_id}/analytics
```

**Response (200):**

```json
{
  "post_id": "7123456789",
  "video_id": 12345,
  "title": "5 habits that changed my morning",
  "caption": "morning routine tips",
  "view_count": 15400,
  "like_count": 1230,
  "comment_count": 89,
  "share_count": 234,
  "bookmark_count": 567,
  "tiktok_account_id": "tt_abc123",
  "account_username": "@yourusername",
  "account_name": "Your Name",
  "event": "post.publish.publicly_available",
  "publish_type": "DIRECT_PUBLISH",
  "published_at": "2026-03-20T14:00:00Z"
}
```

| Field | Description |
|-------|-------------|
| `post_id` | TikTok post ID |
| `video_id` | ReelFarm video ID |
| `title` | Post title |
| `caption` | Post caption |
| `view_count` | Total views |
| `like_count` | Total likes |
| `comment_count` | Total comments |
| `share_count` | Total shares |
| `bookmark_count` | Total bookmarks |
| `tiktok_account_id` | TikTok account that published the post |
| `account_username` | TikTok username (e.g. `@handle`) |
| `account_name` | TikTok display name |
| `event` | TikTok webhook event (e.g. `post.publish.publicly_available`) |
| `publish_type` | `DIRECT_PUBLISH` or `INBOX_SHARE` |
| `published_at` | When the post was published |

**Error (404):** Returned if the video doesn't exist or hasn't been published to TikTok yet.

---

### Publish a video to TikTok

Publish a completed video to TikTok using the automation's saved TikTok settings (account, caption mode, visibility, etc.).

```
POST /api/v1/videos/{video_id}/publish
```

**Request body (optional):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `post_mode` | string | _from automation settings_ | `"DIRECT_POST"` (publish immediately) or `"MEDIA_UPLOAD"` (save as draft in TikTok) |

**Constraints:**
- The video must have `status: "completed"`
- The video must be linked to an automation (`automation_id` must not be null)

**Response (202):**

```json
{
  "message": "TikTok publish started",
  "video_id": "uuid-1234",
  "automation_id": "a1b2c3d4-...",
  "status": "processing"
}
```

Publishing is asynchronous. Once TikTok processes the upload, the video's `post_id` field will be populated (visible via `GET /api/v1/videos/{video_id}`).

---

## TikTok

### List connected accounts

```
GET /api/v1/tiktok/accounts
```

Returns connected TikTok accounts for the authenticated user. Only safe fields are returned — no tokens or sensitive data.

**Response (200):**

```json
{
  "accounts": [
    {
      "tiktok_account_id": "tt_abc123",
      "account_name": "Your Name",
      "account_username": "@yourusername",
      "account_image": "https://..."
    }
  ]
}
```

---

### List TikTok posts with analytics

```
GET /api/v1/tiktok/posts
```

Returns all TikTok posts with engagement metrics, aggregated statistics, and resolved account info.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `timeframe` | number\|string | Days to look back: `7`, `30`, `90`, or `"all"` for all time (default `30`) |
| `sort` | string | Sort by: `"recent"` (default), `"views"`, `"likes"`, `"shares"`, `"comments"`, `"bookmarks"` (descending) |
| `tiktok_account_id` | string | Filter by TikTok account (use `GET /api/v1/tiktok/accounts` to find the ID) |
| `limit` | number | Max results (default 20, max 200) |
| `offset` | number | Pagination offset |

**Response (200):**

```json
{
  "posts": [
    {
      "post_id": "7123456789",
      "video_id": 12345,
      "title": "5 habits that changed my morning",
      "caption": "morning routine tips",
      "view_count": 15400,
      "like_count": 1230,
      "comment_count": 89,
      "share_count": 234,
      "bookmark_count": 567,
      "tiktok_account_id": "tt_abc123",
      "account_username": "@yourusername",
      "account_name": "Your Name",
      "event": "post.publish.publicly_available",
      "publish_type": "DIRECT_PUBLISH",
      "published_at": "2026-03-20T14:00:00Z"
    }
  ],
  "statistics": {
    "total_posts": 28,
    "total_views": 450000,
    "total_likes": 34000,
    "total_comments": 2100,
    "total_shares": 5600,
    "total_bookmarks": 12000
  },
  "timeframe": 30,
  "sort": "recent",
  "limit": 20,
  "offset": 0
}
```

**Examples:**

- Most viewed posts of all time: `GET /api/v1/tiktok/posts?timeframe=all&sort=views`
- Most liked posts in the last week: `GET /api/v1/tiktok/posts?timeframe=7&sort=likes`
- Most shared on a specific account: `GET /api/v1/tiktok/posts?sort=shares&tiktok_account_id=tt_abc123`

Each post includes the resolved `account_username` and `account_name` from the `tiktok_accounts` table — no tokens or sensitive account info is exposed.

---

## Collections

### List image collections

```
GET /api/v1/collections
```

**Response (200):**

```json
{
  "collections": [
    {
      "collection_id": 5191,
      "name": "Nature Photos",
      "created_at": "2026-03-10T08:00:00Z"
    }
  ]
}
```

---

### Get images in a collection

Paginated — returns up to 100 images per page.

```
GET /api/v1/collections/{collection_id}/images
```

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `limit` | number | Max results per page (default 100, max 100) |
| `offset` | number | Pagination offset |

**Response (200):**

```json
{
  "collection_id": 5191,
  "images": [
    {
      "image_id": 215115,
      "image_url": "https://...",
      "added_at": "2026-03-15T12:00:00Z",
      "created_at": "2026-03-14T09:00:00Z"
    }
  ],
  "total": 248,
  "limit": 100,
  "offset": 0
}
```

| Field | Description |
|-------|-------------|
| `image_id` | Unique image identifier (use this when referencing images in `image_settings.first_slide.single_image`) |
| `image_url` | Direct URL to the image |
| `added_at` | When the image was added to this collection |
| `created_at` | When the image was originally uploaded |

---

## Slideshow Library

Browse real TikTok slideshow profiles. Search by niche, slide text content, product medium, account region, or audience region. Use this for inspiration, competitive research, or finding proven content patterns.

### List available niches

```
GET /api/v1/library/niches
```

Returns all unique niches with profile counts, sorted by most profiles.

**Response (200):**

```json
{
  "niches": [
    { "name": "fitness", "profile_count": 142 },
    { "name": "spirituality", "profile_count": 87 },
    { "name": "personal finance", "profile_count": 63 }
  ],
  "total": 45
}
```

---

### Search the library

```
GET /api/v1/library
```

**At least one filter is required** (`q`, `niche`, `product_medium`, `region`, or `audience_region`). Unfiltered requests return a `422` error.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Text search across slide text content (case-insensitive). Searches the full text of every slide. |
| `niche` | string | Filter by niche (case-insensitive partial match, e.g. `"fitness"`, `"finance"`) |
| `product_medium` | string | Filter by product medium (e.g. `"digital product"`, `"SaaS"`, `"physical product"`) |
| `region` | string | Filter by account region code (e.g. `"US"`, `"NL"`, `"UK"`) |
| `audience_region` | string | Filter profiles whose audience includes this country code (e.g. `"US"`, `"PH"`) |
| `sort` | string | `"followers"` (default) or `"recent"` |
| `limit` | number | Max results (default 3, max 3) |
| `offset` | number | Pagination offset |

**Examples:**

- Search by niche: `GET /api/v1/library?niche=fitness`
- Search slide text: `GET /api/v1/library?q=morning+routine`
- Combine filters: `GET /api/v1/library?niche=spirituality&region=US`
- Find profiles with US audience: `GET /api/v1/library?audience_region=US`
- Search by product type: `GET /api/v1/library?product_medium=digital+product`

**Response (200):**

```json
{
  "profiles": [
    {
      "profile_id": 8554,
      "username": "everythingofzodiac",
      "nickname": "All About Zodiac",
      "bio": "Your daily zodiac feed",
      "avatar_url": "https://...",
      "follower_count": "42.5K",
      "follower_count_numeric": 42500,
      "niche": "spirituality",
      "product_medium": null,
      "region": "NL",
      "audience_regions": [
        { "count": 20, "country": "Philippines", "percentage": "20.83%", "countryCode": "PH" },
        { "count": 20, "country": "United States", "percentage": "20.83%", "countryCode": "US" }
      ],
      "slideshows": [
        {
          "index": 0,
          "views": "5.0M",
          "likes": "233.1K",
          "bookmarks": "39.4K",
          "image_count": 13,
          "images": ["https://...slideshow_9cf422bb.jpg", "..."],
          "region": "NL"
        }
      ]
    }
  ],
  "total": 87,
  "limit": 20,
  "offset": 0
}
```

---

### Get a single profile

```
GET /api/v1/library/profiles/{profile_id}
```

Returns full profile details including all slideshow images and additional metadata.

**Response (200):** Same fields as the list response, plus:

| Field | Description |
|-------|-------------|
| `following_count` | Number of accounts this profile follows |
| `link_in_bio` | Link in bio URL |

---

## Pinterest

### Search Pinterest for images

Search Pinterest and return image URLs. Results are paginated with a maximum depth of 5 pages.

```
GET /api/v1/pinterest/search
```

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | Yes | Search query (e.g. `"aesthetic coffee"`, `"minimalist outfit"`) |
| `cursor` | string | No | Pagination cursor from a previous response. Omit for the first page. |

**Response (200):**

```json
{
  "images": [
    "https://i.pinimg.com/originals/ab/cd/ef/abcdef123456.jpg",
    "https://i.pinimg.com/originals/12/34/56/123456abcdef.jpg",
    "https://i.pinimg.com/originals/gh/ij/kl/ghijkl789012.jpg"
  ],
  "cursor": "eyJjIjoiYk...",
  "has_more": true,
  "page": 1,
  "total_pages_allowed": 5
}
```

| Field | Type | Description |
|-------|------|-------------|
| `images` | string[] | Array of full-resolution Pinterest image URLs (`images.orig.url` from each pin) |
| `cursor` | string\|null | Opaque cursor to pass as `?cursor=` for the next page. `null` when no more pages are available or the 5-page limit has been reached. |
| `has_more` | boolean | `true` if another page can be fetched |
| `page` | number | Current page number (1-based) |
| `total_pages_allowed` | number | Maximum pages you can paginate through (always `5`) |

**Pagination limit:** You can paginate through a maximum of 5 pages per search. After page 5, `cursor` will be `null` and `has_more` will be `false`. Start a new search with a different or refined query to find more results.

**Example — paginating through results:**

```
Page 1: GET /api/v1/pinterest/search?q=aesthetic+coffee
Page 2: GET /api/v1/pinterest/search?q=aesthetic+coffee&cursor=eyJjIjoiYk...
Page 3: GET /api/v1/pinterest/search?q=aesthetic+coffee&cursor=eyJjIjoiZG...
...up to page 5
```

**Error responses:**

| HTTP Status | Code | When |
|-------------|------|------|
| 422 | `VALIDATION_ERROR` | Missing `q` parameter, invalid cursor, or max pagination depth reached |
| 500 | `INTERNAL_ERROR` | Pinterest search failed |

---

## Account

### Get account info

```
GET /api/v1/account
```

**Response (200):**

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "user_id": "user_abc123",
  "cancelled": false,
  "next_reset_date": "2027-04-01",
  "subscription_tier": "Growth",
  "credits": 142,
  "ai_credits": 50,
  "purchased_credits": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Account display name |
| `email` | string | Account email |
| `credits` | number | Remaining slideshow credits (resets each billing cycle) |
| `user_id` | string | Unique user identifier |
| `cancelled` | boolean | Whether the subscription has been cancelled |
| `next_reset_date` | string\|null | When credits next reset (billing cycle date) |
| `subscription_tier` | string\|null | Current plan tier (e.g. `"Starter"`, `"Growth"`, `"Scale"`, `"Unlimited"`) |
| `ai_credits` | number | Remaining AI credits |
| `purchased_credits` | number | One-time purchased credits (don't reset) |

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "Human-readable error message",
  "code": "INSUFFICIENT_CREDITS"
}
```

**Common error codes:**

| HTTP Status | Code | Meaning |
|-------------|------|---------|
| 401 | `UNAUTHORIZED` | Missing or invalid API key |
| 403 | `FORBIDDEN` | API key valid but insufficient permissions |
| 404 | `NOT_FOUND` | Resource doesn't exist or doesn't belong to you |
| 422 | `VALIDATION_ERROR` | Invalid request body |
| 429 | `RATE_LIMITED` | Too many requests, slow down |
| 402 | `INSUFFICIENT_CREDITS` | Not enough credits to complete this action |

---

## Rate Limits

All API v1 endpoints share a single rate limit of **20 requests per 60-second sliding window**, keyed per user. When the limit is exceeded, the API returns `429 Too Many Requests` with these headers:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed in the window |
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset` | Unix timestamp (ms) when the window resets |
| `Retry-After` | Seconds to wait before retrying |
