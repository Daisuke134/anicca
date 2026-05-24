---
name: 4.7-slideshow-factory
description: TikTok slideshow factory — Find viral hooks → Pinterest images → Node Canvas slides → Postiz Drafts. Article-compliant pipeline (Alex Nguyen / Apr 17 2026, 1.8M views). General-purpose; works for any niche/persona, not tied to one app. Triggered by cron (Anicca OpenClaw or manual). YOU (the LLM running this) ARE THE ANALYZER — no OpenAI/Vision API calls; you read images and analyze hooks directly using your own multimodal capabilities.
---

# 4.7 Slideshow Factory — Opus 4.7 Native Playbook

You are running this skill. Follow these steps EXACTLY in order. Each numbered step is either:
- **Run a deterministic bash/node script** (you Bash it), or
- **Think and write JSON** (you read inputs, analyze, write output)

You are Claude Opus 4.7. You can read images directly. You can analyze TikTok slideshow visuals natively. You do NOT call any OpenAI or Anthropic API — your own intelligence IS the analyzer.

## ⚙️ Environment

`~/.openclaw/.env` provides:
- `APIFY_API_TOKEN` — TikTok hook discovery + Pinterest fallback
- `POSTIZ_API_KEY`, `POSTIZ_TIKTOK_INTEGRATION_ID` — TikTok Drafts publish
- `FAL_KEY` — (NOT used in this skill — Pinterest is the image source per article)
- No OpenAI / Anthropic key needed — you are the model.

Source the env at the start of any bash you run:
```bash
set -a; source ~/.openclaw/.env; set +a
```

## 📁 Output structure

Per run, create:
```
output/<NICHE>/<YYYY-MM-DD>_<SLOT>/
├── tiktok-hooks.json           ← Step 1 output (apify scrape)
├── viral-slideshows/*.jpg      ← Step 1 first-images of viral slideshows
├── analysis.json               ← Step 2 — YOU write after thinking
├── pinterest/image_01..06.jpg  ← Step 3 (filtered)
├── slides/slide_01..06.png     ← Step 4 (Canvas)
├── caption.txt                 ← Step 5 — YOU write
├── hashtags.txt                ← Step 5 — YOU write
├── postiz-receipt.json         ← Step 6 (Postiz)
└── metadata.json               ← Final summary
```

Bundle the slides+caption+metadata to `~/Downloads/4.7-Slideshow-<NICHE>-<RUN_ID>/` for human review.

---

## STEP 1 — Find Viral TikTok Hooks (deterministic)

Run:
```bash
WORK_DIR="$HOME/.openclaw/skills/4.7-slideshow-factory/output/<NICHE>/<RUN_ID>"
mkdir -p "$WORK_DIR"
bash ~/.openclaw/skills/4.7-slideshow-factory/scripts/01-discover-tiktok-hooks.sh "$WORK_DIR"
```

The script returns up to 20 viral posts (`tiktok-hooks.json`) and downloads up to 5 first-images of viral slideshows (`viral-slideshows/*.jpg`).

You should pick the niche hashtags BEFORE running by editing the `HASHTAGS_JSON` line in `01-discover-tiktok-hooks.sh` — OR pass them as env (TODO: parameterize). For now use the niche relevant to the persona/app being marketed.

---

## STEP 2 — YOU analyze hooks (Opus 4.7 native, NO API)

This is the core article step ("Extract Hooks with Claude Opus 4.7"). You do this yourself.

**Inputs**:
- `tiktok-hooks.json` — top 20 viral posts (text, view count, hashtags, slideshow image URLs)
- `viral-slideshows/*.jpg` — actual viral slideshow first-images. Use the Read tool to view them.

**Tasks** (article Step 2 prompts, applied by YOU):

1. **Identify** the dominant hook patterns from the top 5 viral posts (read both `.text` field AND first-images).
2. **Explain why each works**: curiosity / pain point / surprise / relatability / FOMO / empathy.
3. **Break down structure** for the strongest 1-2 (e.g. "number + outcome", "negative framing", "identity targeting").
4. **Generate 7 hook variations** for the target niche:
   - Each ≤8 words
   - Format: question OR strong statement
   - Avoid generic openers ("Did you know", "Imagine if")
   - Each must trigger one of: curiosity / FOMO / empathy
5. **Pick 1 winning hook** to use today.
6. **Write 3 supporting points** (one per slide):
   - Each ≤12 words, actionable, specific
7. **Write 1-2 dynamic Slide 2 lines** ("intro" — hook補強型, 1-2 short lines following the article's "Most people X. Here's why that's a trap." pattern).
8. **Write CTA stack** (3 short lines for slide 6, article-style: "Save this / Follow for more X / every week →"). **STRICT RULES** for CTA text:
   - NO emojis (🔖 ❤️ 🌿 etc) — TikTokSansDisplayBlack has no emoji glyphs → renders as tofu (□ + X) or stray dots/marks
   - NO trailing punctuation marks (no `.`, `!`, `?`, `…`, `,`, `:`, `;`)
   - NO decorative symbols (no ★ ✓ ◯ • ∙ etc)
   - ONLY plain ASCII letters + space + the closing arrow `→` on the LAST line ONLY
   - Each line should look like `Save this` / `Follow for the real way` / `every week →` — clean and naked
   - If you accidentally include any decoration, the rendered slide will show a stray mark/dot — REJECT and rewrite
9. **Visual style analysis**:
   - palette (e.g. "warm earth tones", "moody monochrome")
   - lighting (e.g. "golden hour", "dark cinematic")
   - aesthetic (e.g. "minimal zen", "luxury bold")
   - mood (single descriptive word)
10. **10 Pinterest search queries** (article: "10 Pinterest search queries"):
    - 2-4 words each
    - Aesthetic-focused, not topical
    - Match visual mood
11. **Save** as `analysis.json`:

```json
{
  "niche": "<niche>",
  "viral_input_post_count": 20,
  "hook_pattern_analysis": {
    "dominant_patterns": ["..."],
    "why_they_work": "..."
  },
  "hook_variations": [
    {"hook": "...", "emotion": "curiosity|FOMO|empathy", "structure": "...", "reasoning": "..."},
    ... 7 total
  ],
  "chosen_hook": "...",
  "intro": ["line 1", "line 2"],
  "point_1": "...",
  "point_2": "...",
  "point_3": "...",
  "cta_lines": ["Save this 🔖", "Follow for more ...", "every week →"],
  "visual_style": {
    "palette": "...",
    "lighting": "...",
    "aesthetic": "...",
    "mood": "..."
  },
  "pinterest_queries": ["...", ... 10 total]
}
```

Also append the 7 variations to `~/.openclaw/skills/4.7-slideshow-factory/state/hook-library.jsonl` (one JSON object per line).

---

## STEP 3 — Pinterest images (deterministic, with article filters)

Run:
```bash
bash ~/.openclaw/skills/4.7-slideshow-factory/scripts/03-pinterest-download.sh \
    "$WORK_DIR/analysis.json" \
    "$WORK_DIR/pinterest"
```

The script:
- Uses top 3 Pinterest queries from `analysis.json`
- Renders Pinterest search via playwright-cli, extracts pin URLs
- For each pin: curl → og:image → highest-res `i.pinimg.com/1200x/...`
- **Article filters applied**:
  - 9:16 portrait priority (or landscape that crops)
  - Bold/high-contrast (rejects pastels via byte-per-pixel heuristic)
  - Minimum 600×600 dimensions
- Fallback without filter if too few pass

Verify 6 images downloaded. If <3, re-run or extend queries.

---

## STEP 4 — Canvas slides (deterministic, article values)

Run:
```bash
node ~/.openclaw/skills/4.7-slideshow-factory/scripts/04-generate-slides.js \
    --theme-json "$WORK_DIR/analysis.json" \
    --images-dir "$WORK_DIR/pinterest" \
    --output-dir "$WORK_DIR/slides"
```

Script values (article-compliant):
- 1080×1920 PNG
- OVERLAY_OPACITY 0.52
- shadowBlur 12, shadowOffsetY 4, shadowColor rgba(0,0,0,0.75)
- lineHeight = size × 1.2
- TikTokSansDisplayBlack (TikTok-native bold sans, replaces article's Montserrat)
- 6 slides: HOOK / Intro (Problem-Setup) / Point 1 / Point 2 / Point 3 / CTA
- No persona/app handle hardcoded — CTA is dynamic from `analysis.json.cta_lines`

Verify slide_01..06.png exist and are 1080×1920.

---

## STEP 4.5 — VISUAL VERIFICATION (Opus 4.7 multimodal, NO OCR)

You are the verifier. Use the Read tool on each Pinterest image and each generated slide. Check:

**Pinterest images (`pinterest/image_01..06.jpg`)** — article Step 3 rules:
- ✅ Portrait or square (rejects extreme landscape) — already filtered, but double-check visually
- ✅ Bold colors / high contrast — pastels and washed-out images REJECTED on sight
- ✅ Minimal pre-existing text in image (no headlines, watermarks, logos, busy text) — YOU look and decide
- ✅ Vibe matches the chosen hook emotion (mindful → moody/zen, finance → lifestyle, etc.)

If any image fails, mark it for replacement. Re-run `03-pinterest-download.sh` with **fresh Pinterest queries** OR delete bad image(s) and add fallback queries.

**Generated slides (`slides/slide_01..06.png`)** — quality gate:
- ✅ Text not wrapping into the next line block (no overlap with the line below)
- ✅ Text not overflowing canvas margins (left/right padding respected)
- ✅ No tofu boxes (□ + X) — emojis must NOT appear in any text
- ✅ Background image visible enough through overlay (not pitch black)
- ✅ Hook readable on slide 1 (font size appropriate for length)
- ✅ Numbers (01/02/03) prominent on point slides
- ✅ CTA on slide 6 has all 3 lines visible and not overlapping

If any slide fails:
1. Identify which slide + which issue
2. Fix the underlying cause (e.g. shorten text in `analysis.json`, swap a Pinterest image, adjust `04-generate-slides.js` y-positions)
3. Re-run `04-generate-slides.js`
4. Re-verify

**Repeat until all 6 slides pass all 7 checks.** Do NOT proceed to Step 5 with broken output.

This step is the most important. The cron is autonomous — there's no human review before TikTok Drafts push. You are the only quality gate.

---

## STEP 5 — Caption + hashtags (Opus 4.7 native, NO API)

YOU write:
1. A 1-2 line TikTok caption (≤120 chars, 1-2 emojis, ends with curiosity hook)
2. 8 hashtags optimized for FYP reach: mix of broad (#mindfulness, #fyp) + niche (#buddhisttips)

Save:
- `$WORK_DIR/caption.txt` — caption text only
- `$WORK_DIR/hashtags.txt` — hashtags space-separated on one line

---

## STEP 6 — Postiz → TikTok Drafts (deterministic, article Step 6)

**Article rule (Step 6)**: NEVER direct-post via API. Always push to TikTok Drafts. Human taps Post in app.

Run:
```bash
bash ~/.openclaw/skills/4.7-slideshow-factory/scripts/06-postiz-publish.sh \
    "$WORK_DIR/slides" \
    "$WORK_DIR/caption.txt" \
    "$WORK_DIR/hashtags.txt"
```

Script handles:
- Upload each slide to Postiz CDN
- Create post with `content_posting_method: "UPLOAD"` → pushes to TikTok app Inbox
- `privacy_level: "SELF_ONLY"` until human Posts manually
- Saves `postiz-receipt.json`

Result: slides land in TikTok Drafts. Human (Daisuke) opens TikTok app, sees the draft, taps Post at peak time.

---

## STEP 7 — Bundle to ~/Downloads + report

Bundle for human review:
```bash
DEST=~/Downloads/4.7-Slideshow-<NICHE>-<RUN_ID>
mkdir -p "$DEST"
cp "$WORK_DIR/slides/"*.png "$DEST/"
cp "$WORK_DIR/caption.txt"   "$DEST/"
cp "$WORK_DIR/hashtags.txt"  "$DEST/"
cp "$WORK_DIR/analysis.json" "$DEST/"
cp "$WORK_DIR/postiz-receipt.json" "$DEST/" 2>/dev/null || true
```

Write `metadata.json` to `$WORK_DIR` capturing the full run for viral replication:
```json
{
  "run_id": "<id>",
  "niche": "<niche>",
  "generated_at_utc": "<ts>",
  "tiktok_input_count": 20,
  "viral_slideshow_images_analyzed": <N>,
  "chosen_hook": "...",
  "hook_variations_count": 7,
  "pinterest_queries_used": [...],
  "pinterest_images_downloaded": <N>,
  "slide_count": 6,
  "caption": "...",
  "hashtags": "...",
  "postiz_post_id": "...",
  "tiktok_handle": "<persona>",
  "published_to_drafts": true,
  "next_action_for_human": "Open TikTok app → Drafts → Post"
}
```

---

## STEP 8 — Slack-ready stdout (for cron delivery)

Final stdout line that cron delivery posts to #metrics:

```
📲 4.7-slideshow [<NICHE>] "<chosen_hook>" → TikTok Drafts (6 slides)
   caption: "<first 60 chars>..."
   review: ~/Downloads/4.7-Slideshow-<NICHE>-<RUN_ID>/
   next: open TikTok app → Drafts → Post
```

If any step fails, emit `❌ FAILED at step <N>: <one-line error>` and the last 3 stderr lines.

---

## Per-niche / persona usage

This skill is **general-purpose**. For each cron / niche:
- Edit `01-discover-tiktok-hooks.sh` `HASHTAGS_JSON` to target the niche, OR pass via env (future work)
- Set the niche in WORK_DIR / DEST naming
- Configure `POSTIZ_TIKTOK_INTEGRATION_ID` per persona's TikTok account

Currently configured personas (from `~/.openclaw/.env`):
- `POSTIZ_TIKTOK_INTEGRATION_ID` → "{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}" (@your-tiktok-handle) for Anicca iOS app marketing
- Add more as needed

---

## Failure modes & guardrails

| Failure | Response |
|---------|----------|
| Apify TikTok scrape returns 0 posts | Emit FAILED, suggest checking APIFY_API_TOKEN + hashtags |
| <3 Pinterest images pass filter | Script auto-falls back to no-filter; if still <1, FAILED |
| Postiz upload fails | Emit FAILED with response body, suggest re-auth |
| TikTok integration disabled | Detect via `postiz integrations:list`, emit FAILED |

Never:
- Direct-post to TikTok (article rule, ban risk)
- Hardcode any persona handle in slides (CTA must come from analysis.json)
- Call external LLM APIs (you are the LLM)
- Reuse the same hook from hook-library.jsonl (dedupe)
