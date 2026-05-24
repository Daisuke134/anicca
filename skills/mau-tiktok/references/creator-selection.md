# Creator Selection

## Current Creators (creators.json)

| Name | Lang | Category | Notes |
|------|------|----------|-------|
| ZackD Films | EN | brainrot-comedy | Millions of views. Recommended by Mau article |
| TakeAction | JA | motivation | ZackD同一フォーマット。映像+ナレーション。2.6M再生 |
| コーチジョージ | JA | self-improvement | TikTok 5.6M再生。叱咤フック。危機感ニキ |
| 樺沢紫苑 | JA | mental-health | 33万人。精神科医。Aniccaと親和性最高 |
| ユニグラ | JA | motivation | 23万人。ZackDに最も近い映画的映像+ナレーション |

## Selection Criteria (from Mau article)

1. Consistently gets millions of views per post
2. Target audience watches these videos regularly
3. Video feels like "brainrot" — the shock is part of what makes hooks effective
4. First 3 seconds must be attention-grabbing on their own

## Adding New Creators

To add a creator to the rotation:

1. Open `~/.openclaw/workspace/mau-tiktok/creators.json`
2. Add entry with `name`, `url` (YouTube Shorts page), `lang` ("en" or "ja"), `category`, `notes`
3. Run `scrape-hooks.js --lang <lang> --count 1` to test
