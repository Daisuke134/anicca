---
name: viral-textualizer
description: Find viral video → snaptik download → frame-by-frame text extraction → variation generator. Pipeline: agent-{{profile.lateness.stakeholders.channel}} TT search → snaptik.app/en2 mp4 download → ffmpeg keyframe extract → Claude vision OCR + transcript via whisper → JSON {hook, body, cta, voiceover} → variations for reelfarm/4.7-slideshow factory. Use when manually triggered as `bash scripts/textualize.sh <tt_url>` or via `comedy-trend-copy` cron.
metadata:
  tags: scraping, viral, copying, frame-extraction, vision, whisper, variations
  requires:
    bins: [agent-{{profile.lateness.stakeholders.channel}}, ffmpeg, whisper, jq, curl]
    env: [ANTHROPIC_API_KEY]
---

# viral-textualizer

Copy any viral video — frame by frame, transcript, then generate variations.

## Pipeline

```
[viral TT URL]
    │
    ▼
1. snaptik.app/en2 ({{profile.lateness.stakeholders.channel}}) → mp4 download
    │
    ▼
2. ffmpeg keyframe extract (every 0.5 sec OR shot change)
    │
    ▼
3. For each frame:
   a. Claude Vision: extract on-screen text overlay
   b. Save: frame_NNN.png + frame_NNN_text.json
    │
    ▼
4. ffmpeg audio extract → whisper → transcript.json
    │
    ▼
5. Compose:
   {
     "hook":      "first 3 sec on-screen text (slide 1-2)",
     "body":      ["middle frames text (slide 3-5)"],
     "cta":       "last 2 sec on-screen text + voice CTA (slide 6)",
     "voiceover": "full whisper transcript",
     "duration":  N seconds
   }
    │
    ▼
6. Generate 5 variations:
   - hook固定 / body shuffled
   - hook variant / body 同
   - same template, different angle
    │
    ▼
7. Output: ~/.openclaw/workspace/comedy/variations/<source-id>/{1..5}.json
   → consumed by reelfarm or 4.7-slideshow-factory
```

## Cron

This is a **library skill** — invoked by other crons. Anicca-comedy-trend-copy uses it to auto-textualize seed videos.

## Cost

| Step | Tool | Cost |
|----|----|----|
| download | snaptik via {{profile.lateness.stakeholders.channel}} | $0 |
| frame extract | ffmpeg | $0 |
| OCR per frame | Claude vision | ~$0.002 × 30 frames = $0.06/video |
| audio transcript | whisper local | $0 |
| variation gen | Claude prompt | ~$0.01/variation × 5 = $0.05 |
| **Total per video** | — | **~$0.11** |

50 videos/month = $5.50/mo
