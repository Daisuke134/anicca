# HeyGen Pipeline — exact calls

Assumes `heygen auth login` already saved the key at `~/.heygen/credentials`, and `$HOME/.local/bin` is in PATH.

## Step 1 — Generate voice audio

```bash
VOICE_ID=$(cat ~/anicca-monk-factory/characters/$LANG/voice_id.txt)
SCRIPT_TEXT="$(python3 -c "import json; print(json.load(open('$SCRIPT_JSON'))['full_text'])")"

AUDIO_JSON=$(heygen voice speech create -d "{
  \"voice_id\": \"$VOICE_ID\",
  \"text\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$SCRIPT_TEXT")
}" --wait --timeout 5m)

AUDIO_URL=$(echo "$AUDIO_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['audio_url'])")
curl -sS -o ~/anicca-monk-factory/renders/$TS.mp3 "$AUDIO_URL"
```

Voice is locked per language. Never recreate; never change between videos.

## Step 2 — Generate avatar video

```bash
AVATAR_ID=$(cat ~/anicca-monk-factory/characters/$LANG/avatar_id.txt)

VIDEO_JSON=$(heygen video create -d "{
  \"type\": \"avatar\",
  \"avatar_id\": \"$AVATAR_ID\",
  \"voice_id\": \"$VOICE_ID\",
  \"script\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$SCRIPT_TEXT"),
  \"dimension\": {\"width\": 720, \"height\": 1280}
}" --wait --timeout 20m)

VIDEO_ID=$(echo "$VIDEO_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['video_id'])")
```

Avatar IV engine is the default for prompt-generated avatars. It produces clean lip-sync for 30–90s clips in ~2–6 minutes of processing.

## Step 3 — Download

`--wait` polls until status is `completed`. Output JSON has `video_url` directly.

```bash
DL=$(echo "$VIDEO_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d.get('video_url') or d.get('result',{}).get('video_url',''))")
curl -sS -o ~/anicca-monk-factory/renders/${TS}_raw.mp4 "$DL"
```

## Step 4 — Sanity check

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration \
  -of default=noprint_wrappers=1 ~/anicca-monk-factory/renders/${TS}_raw.mp4
```

Expect: width=720 height=1280 duration ≈ script length.

If duration < 10s or > 90s, something went wrong — regenerate from step 2 with a shorter/longer script.

## Budget Guardrail

Each 30-sec video ≈ $0.25-0.45 on HeyGen Creator. Each 80-sec JP video ≈ $0.60-0.90. Before step 2, check wallet:

```bash
BAL=$(heygen user me get --human 2>&1 | awk '/Remaining Balance:/ {print $3}')
[ "${BAL%.*}" -lt 1 ] && echo "ABORT: HeyGen wallet below \$1" && exit 3
```

## Voice Picking (once per language, at setup)

Run:
```bash
heygen voice list --language en --human | head -40
```
Pick a male voice in the "calm / warm / low" range. Save the ID:
```bash
echo "<the id>" > ~/anicca-monk-factory/characters/en/voice_id.txt
```

For JP: `heygen voice list --language ja --human` — pick older male, low, slow.

Test the pick with one short render before locking. Once locked, never change.
