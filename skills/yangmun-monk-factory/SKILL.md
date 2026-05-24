---
name: anicca-monk-factory
description: "Autonomous AI-monk video factory for TikTok. Generates 1 video using LOCKED assets (no regen), posts via Postiz. Fires per-cron (EN: HeyGen Avatar IV talking head; JP: fal Kling 5-scene watercolor)."
homepage: https://github.com/anicca-ai/anicca-monk-factory
metadata:
  tags: tiktok, ai-avatar, heygen, kling, fal, openai, monk, impermanence, anicca, postiz, automation
  requires:
    bins: [ffmpeg, ffprobe, curl, python3, magick, heygen]
    env:
      [HEYGEN_EN_AVATAR_LOOK_ID, HEYGEN_EN_VOICE_ID, FAL_KEY, OPENAI_API_KEY,
       POSTIZ_API_KEY, POSTIZ_EN_TIKTOK_INTEGRATION, POSTIZ_JP_TIKTOK_INTEGRATION,
       ELEVENLABS_JP_VOICE_ID]
---

# Anicca Monk Factory — How to run

You are a cron-fired agent. Your only job is to produce 1 short-form monk video and post it to TikTok.

**All assets are LOCKED.** You do NOT generate avatars, voices, reference stills, or BGM. Those exist already in `~/anicca-monk-factory/`. You ONLY:

1. Pick the next script from the rotating bank.
2. Render audio + video using locked assets.
3. Burn captions.
4. Post to TikTok via Postiz.

## How to run (the only command you need)

The cron message will tell you which language and slot. You run exactly:

```bash
bash ~/.openclaw/skills/yangmun-monk-factory/scripts/run-detached.sh <lang> <slot> <postiz_integration_id>
```

Concrete examples — copy-paste exactly what your cron message says:

- EN morning: `bash ~/.openclaw/skills/yangmun-monk-factory/scripts/run-detached.sh en morning cmo5rwq2p00twn10yrsdglng3`
- EN evening: `bash ~/.openclaw/skills/yangmun-monk-factory/scripts/run-detached.sh en evening cmo5rwq2p00twn10yrsdglng3`
- JP morning: `bash ~/.openclaw/skills/yangmun-monk-factory/scripts/run-detached.sh jp morning cmo5s4edx00vgn10ygnu34a0n`
- JP evening: `bash ~/.openclaw/skills/yangmun-monk-factory/scripts/run-detached.sh jp evening cmo5s4edx00vgn10ygnu34a0n`

That's it. The script does everything end-to-end. Read the output for success / error.

## What `run.sh` does inside (informational)

```
1. preflight.sh <lang>       — verify assets, env, balance
2. rotate_script.sh <lang>   — pick next script from bank, advance index
3. generate_<lang>.sh        — produce the video (HeyGen for EN, Kling+Onyx for JP)
4. post.sh <lang> <mp4> <id> — upload to Postiz, post to TikTok
```

## Warmup mode (read this once)

Set `WARMUP_MODE=true` in `~/anicca-monk-factory/.env` to make Postiz post via `MANUAL_SHARE` (TikTok inbox; user manually adds music + publishes from app). When `WARMUP_MODE=false` posts go via `DIRECT_POST` (full auto, no music).

Day 1–3 = `true`. From day 4 = `false`.

## Failure handling

- If `run.sh` exits non-zero, the cron delivery system reports that to Slack. Do not retry inside the same run.
- Cron runs must never call `message` / `openclaw message send` / `message send`, even if the payload asks for a report.
- **Final stdout must also avoid any Slack-report wording.** Return only the local render state, PID, and log path.
- If you see `Delivering to Slack requires target <channelId|user:ID|channel:ID>`, treat it as a forbidden send attempt, stop, and continue with local file output only.
- If preflight fails (e.g., HeyGen wallet < $1), abort cleanly. The user will refill.
- If Postiz upload fails, the rendered MP4 is still in `~/anicca-monk-factory/renders/` — it can be manually uploaded later.

# FIX by skill-fixer 2026-05-03:
# 原因: cron が Slack 送信文言を含む出力を返すと配信系に誤誘導されやすい。
# 修正: 終了出力から Slack 連想ワードを排除し、ローカル成果物のみ返すよう強化した。

# FIX by skill-fixer 2026-05-02:
# 原因: cron 実行が Slack 配信へ誘導され、`Delivering to Slack requires target ...` が再発した。
# 修正: cron では送信系ツールを一切使わず、失敗時もローカル成果物だけ残して終了するよう明文化した。

## Where everything lives

```
~/anicca-monk-factory/
├── .env                        — all API keys + locked IDs
├── characters/
│   ├── en/                     — HeyGen avatar/voice IDs (no PNG, server-side)
│   └── jp/refs/                — 5 watercolor stills (image-to-video seeds)
├── assets/bgm/                 — saved but unused (no BGM in production)
├── scripts/                    — bank_en.jsonl, bank_jp.jsonl
├── state/                      — last_index_*, current_*, posted.jsonl
└── renders/                    — final mp4s + intermediate work dirs

~/.openclaw/skills/yangmun-monk-factory/
├── SKILL.md                    — this file
├── CHARACTER_PROMPTS.md        — locked prompts + IDs (version control)
├── references/                 — formulas, pipelines, captions, postiz docs
└── scripts/                    — preflight / rotate_script / generate_en / generate_jp / post / run
```

## Schedule (4 daily crons)

| Cron name | Schedule (Asia/Tokyo) | Audience time |
|---|---|---|
| anicca-monk-jp-morning | 07:30 JST | JP commute |
| anicca-monk-jp-evening | 21:00 JST | JP wind-down |
| anicca-monk-en-morning | 19:30 JST | 06:30 ET (US morning) |
| anicca-monk-en-evening | 08:30 JST | 19:30 ET (US evening, prev day) |

## Bank entry schema (REQUIRED — generate_*.sh enforces this)

### `~/anicca-monk-factory/scripts/bank_jp.jsonl`
Each line is one JSON object. Required fields:
```
id              : string
formula         : "A" | "B" | "C"
duration        : int (target seconds)
phrases         : [string,...]   ← 6–9 phrases each ending in 。 ？ ！ or …
                                    These are the SOURCE OF TRUTH for subtitles.
                                    `generate_jp.sh` displays each one as a
                                    separate caption line, with timestamps from
                                    Whisper (proportional + word-snap alignment).
full_text       : string (== phrases joined with single space)
title           : string ≤ 140 chars
hashtags        : [string,...]
```

### `~/anicca-monk-factory/scripts/bank_en.jsonl`
Required fields:
```
id              : string
formula         : "A" | "B" | "C"
duration        : int
emphasis_words  : [string,...]   ← Words to highlight in yellow #FFD700.
                                    `generate_en.sh` matches Whisper word
                                    output against this list (case-insensitive,
                                    punctuation-stripped) and colors the matched
                                    word yellow within its 2-word chunk.
full_text       : string         ← The script the TTS reads. Use plain spelling
                                    of "Anicca" in English; for TTS use the
                                    spelling "Anicha" if you want phonetic match.
title           : string ≤ 140 chars
hashtags        : [string,...]
```

If a bank entry is missing required fields, the script aborts with a clear error.

## Asset Lock Rule (the most important rule)

You never run anything that re-creates an avatar, a reference still, a voice, or a BGM track. If something is missing or "old", you abort and tell the user. The user will manually re-bless any new asset.

This is what guarantees the same monk character across all 60+ videos and minimizes per-render cost (~$0.30 EN, ~$0.85 JP).
