# Caption Burn

The voice talks for 30–80s. Captions must appear in sync, 2-word UPPERCASE chunks, Green Zone only (never in TikTok UI area).

## Fastest path — HeyGen native captions

HeyGen can generate captions with the video if you pass `caption: true` in `video create`:

```json
{"type":"avatar", "avatar_id":"...", "voice_id":"...", "script":"...", "caption": true, "caption_style": {"font": "Instrument Serif", "color": "#FFFFFF", "outline": "#000000"}}
```

Check `heygen video create --request-schema | grep -i caption` for current options. If native captions look good, skip to Postiz. Otherwise fall back to the ffmpeg path below.

## Fallback — Whisper + drawtext burn

### 1. Transcribe with Whisper

```bash
python3 -m whisper renders/${TS}_raw.mp4 \
  --model base --word_timestamps True --output_format srt \
  --output_dir captions/
```

Produces `captions/${TS}_raw.srt`. Re-chunk to 2-word groups (a Python helper lives in `~/.openclaw/skills/anicca-monk-factory/scripts/rechunk_srt.py`).

### 2. Burn with ffmpeg

```bash
FONT_EN=~/Library/Fonts/TikTokSansDisplayBold.ttf      # or InstrumentSerif-SemiBold.ttf
FONT_JP="/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"

case $LANG in
  en) FONT="$FONT_EN" ;;
  jp) FONT="$FONT_JP" ;;
esac

ffmpeg -y -i renders/${TS}_raw.mp4 \
  -vf "subtitles=captions/${TS}_rechunked.srt:force_style='FontName=Instrument Serif,FontSize=52,PrimaryColour=&HFFFFFF&,Outline=4,OutlineColour=&H000000&,Alignment=2,MarginV=220'" \
  -c:a copy renders/${TS}_final.mp4
```

- **MarginV=220** keeps text out of the bottom TikTok UI area (Green Zone safe)
- **Alignment=2** = bottom-center
- **FontSize=52** for 720×1280 vertical
- Subtitles filter must be LAST in the chain (per video-use rule 1)

### 3. Optional — Remotion 2-word pops

For hero moments (the 1-word reveal like "impermanent" at 6s), Remotion is better:

```bash
cd ~/.openclaw/skills/anicca-monk-factory/scripts
node render_pop_overlay.mjs --in renders/${TS}_raw.mp4 --word "impermanent" --at 6.0 --out renders/${TS}_pop.mp4
```

Details in the remotion skill (already installed at `~/.claude/skills/remotion`).

## Green Zone

TikTok UI eats:
- Top: 0–150px (username, sound name)
- Bottom: 1080–1280px (caption, CTAs, like button)

Text MUST be between y=150 and y=1080. Use `MarginV=200+` for bottom placement; use `MarginV=-800` negative to push to top zone. Test with one render before committing a slot to a new overlay style.

## Verify

Before uploading to Postiz:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 renders/${TS}_final.mp4
# expect close to audio duration

ffmpeg -y -i renders/${TS}_final.mp4 -vf "thumbnail,scale=400:-1" \
  -frames:v 1 renders/${TS}_thumb.png
open renders/${TS}_thumb.png   # visually check caption sits in Green Zone
```
