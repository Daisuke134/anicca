---
name: ig-reels-poster
description: Publish a VIDEO Reel (mp4, 9:16) to an Instagram account via the CloakBrowser daily-driver (no Postiz). Browser-direct flow that differs from the carousel poster: 新規投稿 → upload 1 mp4 → IG auto-detects リール → cover/thumbnail + trim step (video-only) → 次へ → caption → シェア. ★ Default --dry verifies the whole flow up to (not incl.) publish, then discards — proves it works WITHOUT posting. --live publishes (only when the account is warmed). ★ Sibling of ig-account-poster (that one = photo carousel; this one = video Reels).
---

# ig-reels-poster

★ Video Reels poster. Companion to `ig-account-poster` (carousel/slideshow, built by
another agent — do NOT touch it). The two flows DIFFER: a video upload adds an
IG "リール" confirmation + a cover-frame/trim step that image carousels don't have. ★

## Flow (browser-direct via CDP daily-driver)

```
新規投稿 (Create) → file input ← set 1 mp4 (9:16) →
  IG detects video → "リール" notice (auto / click 続行 if shown) →
  次へ  (★ cover-frame select + trim — video-only step ★) →
  次へ  →
  caption textarea ← paste caption →
  シェア  (★ --live only; --dry stops here and discards ★)
```

## Run

```bash
PY=/opt/homebrew/bin/python3
$PY ~/.claude/skills/ig-reels-poster/scripts/post_reel.py \
   --video ~/clips/final/galloway_HD_EN.mp4 \
   --caption-file /tmp/cap.txt \
   [--dry|--live]
```

- `--dry` (DEFAULT, safe): walks every step up to but NOT including the final シェア
  click, screenshots each, then discards. Proves the flow works without posting.
- `--live`: actually clicks シェア. Only when the account is warmed (ig-account-warmer)
  and verify_clip.sh passed.

## Account targets (2-account plan)

| handle | niche | lang | money path |
|---|---|---|---|
| (EN, to create) | AI / money / startup clips | English | ClipAffiliates/Whop → USDC |
| (JP, to create) | same clips, JP jimaku | 日本語 | TikTok日本/IG日本 reach |

## Pipeline position

`earn-clip-rewards/scripts/daily.sh` calls `poster.sh`, which routes mp4 → THIS skill
per account. Always gate on `earn-clip-rewards/scripts/verify_clip.sh` BEFORE --live.

## Gotchas (IG web video upload)
- IG web composer accepts mp4 via the hidden `input[type=file]` — use cdp.py `setfile`.
- Video adds a cover/thumbnail step; the carousel poster skips it. Don't reuse its post.py.
- 9:16 video may show a crop/fit toggle — pick "元のサイズ/Original" so the 9:16 isn't cropped.
- --dry must NEVER click the final シェア (the safety contract).
