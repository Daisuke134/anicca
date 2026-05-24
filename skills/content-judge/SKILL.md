---
name: content-judge
description: "Pre-post quality gate. Invoked inline by each factory before Postiz upload. Extracts frames, sends to gpt-5.4-mini vision with the caption + ASS subs, returns OK/NG. NG → caller blocks the Postiz post + Slack alert."
metadata:
  tags: qa, vision, gpt-5.4-mini, pre-post, gate
  requires:
    bins: [ffmpeg, python3]
    env: [OPENAI_API_KEY]
---

# Content Judge — How to use

This skill is **called inline by other skills**, not on a cron. It is the last sanity check before a video goes to Postiz.

## How to invoke

```bash
bash ~/.openclaw/skills/content-judge/scripts/judge.sh <mp4> <ass_or_-> <caption_text> <lang>
```

Returns:
- exit 0 + stdout `OK` → caller may post
- exit 1 + stdout `NG: <reason>` → caller must skip post, Slack notified

Set `CONTENT_JUDGE_ENABLED=true` in `~/anicca-monk-factory/.env` to enable; otherwise the gate is a no-op (returns OK).

## What it checks

1. **Face / image artifacts** — extract 5 evenly-spaced frames, ask gpt-5.4-mini vision: "Any face distortion, mouth glitch, eye misalignment? Anything obviously broken?"
2. **Caption sync** — if .ass provided, parse subtitle timings and match against video duration. Drift > 0.5s of total → NG.
3. **Caption / hashtag policy** — gpt-5.4-mini text check on caption: TikTok-banned tags (#fyp on IG), URL typos, brand violations.

## When called from post.sh

Add this snippet at top of post.sh **after** $MP4 is set, **before** the Postiz upload:

```bash
if [ "${CONTENT_JUDGE_ENABLED:-false}" = "true" ]; then
  JUDGE_OUT=$(bash ~/.openclaw/skills/content-judge/scripts/judge.sh "$MP4" "-" "$CAPTION" "$LANG_ARG" 2>&1)
  echo "$JUDGE_OUT" >&2
  if echo "$JUDGE_OUT" | head -1 | grep -q '^NG'; then
    echo "🚨 content-judge BLOCKED post — see above" >&2
    exit 10
  fi
fi
```

## Cost
- ffmpeg frame extraction: free
- gpt-5.4-mini vision (5 frames + text): ~$0.01 per call
- 30 posts/day = ~$0.30/day
