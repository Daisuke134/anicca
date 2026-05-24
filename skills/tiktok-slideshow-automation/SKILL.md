---
name: tiktok-slideshow-automation
description: Automate English-language TikTok slideshow content creation, hook extraction, image sourcing, slide generation, captioning, scheduling, and draft-based publishing via Postiz. Use when building or repeating a complete TikTok slideshow pipeline from viral reference posts, especially for English-only audiences.
---

# TikTok Slideshow Automation

## Goal
Build TikTok slideshow posts end to end: research, hooks, images, slides, caption, schedule, publish as draft.

## Exact flow
1. Read `references/flow-visual.md` and `references/file-structure.md`.
2. Find a reference post and save it in `reference.md` or `reference.json`.
3. Extract hook, structure, CTA pattern, and visual style.
4. Write English-only hook variants and a 6-slide plan in `slides.json`.
5. Save prompt inputs in `prompts.json`.
6. Source images and generate `output/slide_01.png` through `output/slide_06.png`.
7. Write `caption.txt`, `hashtags.txt`, and `schedule.json`.
8. Upload to Postiz as a TikTok draft and store the result in `upload.json`.
9. Review the draft manually.
10. Publish at the audience's evening peak.

## Rules
- Target English-only audiences unless the user explicitly asks otherwise.
- Use the same visual style across all slides in one post.
- Keep the hook preserved, do not dilute it.
- Prefer draft publishing for safety and manual final review.
- Do not invent a new content format when a reference post already defines the structure.
- Save reusable inputs in files before or during execution.
- Use the target audience's local evening peak for posting.

## What to produce
- `reference.md` or `reference.json`
- `prompts.json`
- `slides.json`
- `caption.txt`
- `hashtags.txt`
- `schedule.json`
- `output/slide_01.png` through `output/slide_06.png`
- `upload.json`

## When choosing post timing
Use the audience's local evening peak for English-only audiences, then convert to the scheduler timezone. If no audience geography is known, default to US evening hours. See `references/posting-time.md`.

## References
Read the files in `references/` for the concrete pipeline, prompts, timing rules, and file layout.