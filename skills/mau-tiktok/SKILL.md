---
name: mau-tiktok
description: "Automated viral hook scraping + CTA stitching pipeline for TikTok/YouTube/Instagram. Scrapes 1 viral YouTube Short per cron, trims first 3s as hook, stitches with pre-made CTA v7 video (9s total), posts to 3 platforms. Runs 4x/day via OpenClaw cron."
metadata:
  tags: tiktok, youtube, instagram, video, marketing, automation, postiz, ffmpeg, yt-dlp
  requires:
    bins: [ffmpeg, ffprobe, yt-dlp, node]
    env: [POSTIZ_API_KEY]
---

# mau-tiktok — Viral Hook + CTA Video Automation (v7)

Source: Mau ([@maboroshi_app](https://x.com/maboroshi_app)) — 7M views, 61K subscribers, fully automated.
Method: "Grab the first 3 seconds of a proven viral video as hook, stitch a CTA, post everywhere."

## Pipeline

```
scrape-hooks.js → trim-and-stitch.js → post-to-postiz.js
    (1 hook DL)      (3s trim + CTA)      (3 platform posts)
```

**Final video = 9 seconds (hook 3s + CTA 6s)**

## CRITICAL RULES FOR CRON EXECUTION

| Rule | Why |
|------|-----|
| **Fix broken scripts/config when reality and SKILL.md diverge** | This automation is expected to run unattended. If posting breaks because script/config drifted, repair the implementation instead of asking Dais |
| **NEVER ask for approval to run the scheduled pipeline** | Cron/skill runs are pre-authorized internal execution. Do not send "Once approved, I'll run it" or similar |
| **NEVER regenerate CTA videos** | `cta_en_final.mp4` and `cta_ja_final.mp4` are pre-made finals |
| **Always pass --lang and --count 1** | Each cron handles one language, one video |
| **Run scripts sequentially** | Step 1 → Step 2 → Step 3, in order |

## Cron Execution (EXACT STEPS)

## Disk Safety

Before step 1, ensure the workspace has room for the hook download and final export:

```bash
mkdir -p ~/.openclaw/workspace/mau-tiktok/tmp
find ~/.openclaw/workspace/mau-tiktok/output -type f | sort | tail -n +51 | xargs -r rm -f
find ~/.openclaw/workspace/mau-tiktok/hooks/raw -type f | sort | tail -n +51 | xargs -r rm -f
find ~/.openclaw/workspace/mau-tiktok/hooks/trimmed -type f | sort | tail -n +51 | xargs -r rm -f
```

After posting, delete the just-used raw hook, trimmed hook, and any temporary render artifacts so the next cron cannot fail with ENOSPC.


When triggered by cron, execute these 3 commands in order:

```bash
cd ~/.openclaw/skills/mau-tiktok/scripts

# Step 1: Download 1 new hook
node scrape-hooks.js --lang {LANG} --count 1

# Step 2: Trim to 3s + stitch with CTA
node trim-and-stitch.js --lang {LANG} --count 1

# Step 3: Post to all platforms
node post-to-postiz.js --lang {LANG}
```

Replace `{LANG}` with `en` or `ja` based on the cron message.

**That's it for normal runs. If the pipeline is broken, fix the scripts/config to match this SKILL and then continue. Do not stop at an approval request or hand the problem back to Dais.**

## Workspace

```
~/.openclaw/workspace/mau-tiktok/
├── cta_en_final.mp4          # CTA v7 (EN) — NEVER regenerate
├── cta_ja_final.mp4          # CTA v7 (JA) — NEVER regenerate
├── creators.json             # Scrape targets (ZackD EN + seeyou JA)
├── config.json               # Integration IDs + captions
├── used_hooks.json           # Duplicate prevention
├── post-log.json             # Post results log
├── hooks/
│   ├── raw/{lang}/           # Full downloaded YouTube Shorts
│   └── trimmed/{lang}/       # First 3 seconds, 1080×1920
└── output/
    ├── en/                   # Final stitched videos (EN)
    └── ja/                   # Final stitched videos (JA)
```

## Cron Schedule (4x/day)

| Time (JST) | Cron Name | Lang | Platforms |
|------------|-----------|------|-----------|
| 08:00 | mau-tiktok-ja-morning | ja | TikTok aniccajp6 + IG anicca.jp + YT JA専用 |
| 08:15 | mau-tiktok-en-morning | en | TikTok anicca.en7 + IG anicca.ai + YT @anicca-ai |
| 17:00 | mau-tiktok-ja-evening | ja | TikTok aniccajp6 + IG anicca.jp + YT JA専用 |
| 17:15 | mau-tiktok-en-evening | en | TikTok anicca.en7 + IG anicca.ai + YT @anicca-ai |

**Daily total: 4 videos × 3 platforms = 12 posts/day**

## Posting Integration IDs

| Lang | Platform | Account | Integration ID |
|------|----------|---------|----------------|
| EN | TikTok | anicca.en7 | `cmmtt62wq01lqn50yehk1f6dy` |
| EN | Instagram | anicca.ai | `cmmzzg2es0539p30ycb94ayx0` |
| EN | YouTube | @anicca-ai | `cmn8ymq6c02oio70y5ea1trv8` |
| JA | TikTok | aniccajp6 | `cmmytdj1101w1p30ytx8lj0fw` |
| JA | Instagram | anicca.jp | `cmmzujxpa04ujp30yxqpg1vci` |
| JA | YouTube | JA専用 | `cmn1oukj9012nnq0yqhouc3ib` |

## Error Handling

| Error | Action |
|-------|--------|
| yt-dlp download fails | Script logs error and exits. Next cron will retry |
| No new hooks (all used) | Script logs "0 downloaded" and exits |
| CTA file missing | Script exits with error message |
| Postiz upload fails | Script exits, does not attempt platform posts |
| Platform post fails | Other platforms still post. Results logged to post-log.json |

## Cleanup

After every successful run, remove temporary downloads and stale renders from `hooks/raw`, `hooks/trimmed`, and `output` before exiting.

