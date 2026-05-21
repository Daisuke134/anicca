---
name: anicca-music-factory
description: Generate AI meditation/ambient music for Anicca's Spotify catalog using apiframe.ai (Suno V5). Use when the user says "make music", "generate a track", "create meditation song", "音楽作って", "瞑想音楽生成", or wants to add to the Anicca Sounds / 無常 Mujō / Bodhi Frequencies catalog before manual DistroKid upload.
---

# Anicca Music Factory

Manual on-demand skill that generates AI music for Anicca's Spotify monetization catalog. Targets the meditation/ambient niche where passive listening drives long stream times and high per-track royalties.

Strategy reference: see `strategy.md` in this directory for the full Spotify monetization playbook copied from the Telisha Jones / James 99 case studies.

## Personas (artist names)

| Persona | Niche | Suno tags | Target market |
|---------|-------|-----------|---------------|
| **Anicca Sounds** | English meditation, deep ambient | `meditation, ambient, deep relaxation, soft drone` | Western Spotify |
| **無常 Mujō** | Japanese / Tibetan, traditional instruments | `tibetan singing bowls, koto, shakuhachi, zen meditation` | JP + global meditation |
| **Bodhi Frequencies** | Binaural / healing frequencies | `528hz, binaural beats, brainwave entrainment, healing` | Sleep / focus listeners |

Pick one persona per generation run. Multiple personas = wider Spotify algorithmic reach (article law #5).

## Authentication

Requires apiframe.ai API key in environment.

```bash
# Read from ~/.openclaw/.env
export APIFRAME_API_KEY="<key from ~/.openclaw/.env>"
```

If `APIFRAME_API_KEY` is unset, source the env file first:

```bash
source ~/.openclaw/.env
```

**NEVER hardcode the key in any file. NEVER echo it. NEVER commit it.**

## API Reference (apiframe.ai → Suno V5)

Base URL: `https://api.apiframe.pro`

### 1. Generate music (POST /suno-imagine)

```bash
curl -X POST https://api.apiframe.pro/suno-imagine \
  -H "Authorization: $APIFRAME_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "deep ambient meditation, tibetan singing bowls, slow drone, impermanence theme, 8 minutes",
    "model": "V5",
    "make_instrumental": true,
    "title": "Returning to Stillness",
    "tags": "meditation, ambient, tibetan bowls, healing"
  }'
```

Response:
```json
{ "task_id": "abc123..." }
```

Suno V5 generates **2 variations per call** (audio_a + audio_b). Pick the better one or release both.

### 2. Poll for completion (POST /fetch)

```bash
curl -X POST https://api.apiframe.pro/fetch \
  -H "Authorization: $APIFRAME_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "abc123..."}'
```

Poll every 15 seconds until `status == "finished"`. Typical completion: 30-90 seconds.

Response (finished):
```json
{
  "status": "finished",
  "task_type": "suno",
  "percentage": 100,
  "songs": [
    {
      "song_id": "da7f...",
      "lyrics": "[Instrumental]",
      "duration": 179.84,
      "audio_url": "https://cdn.apiframe.pro/songs/...-1.mp3",
      "image_url": "https://musicfile.kie.ai/...jpeg"
    },
    {
      "song_id": "bb34...",
      "lyrics": "[Instrumental]",
      "duration": 154.92,
      "audio_url": "https://cdn.apiframe.pro/songs/...-2.mp3",
      "image_url": "https://musicfile.kie.ai/...jpeg"
    }
  ]
}
```

Suno V5 returns 2 variations in `songs[]` array (typical duration: 2:30-3:30 each). For longer tracks (8+ minutes), call the `EXTEND` endpoint with the chosen song_id.

## Output structure (versioned, never overwrite)

```
/Users/anicca/anicca-project/music-factory/
└── {persona-slug}/                    # anicca-sounds | mujo | bodhi-frequencies
    └── {YYYY-MM-DD}/                  # 2026-04-28
        └── v{N}/                      # v1, v2, v3, ... (NEVER overwrite)
            ├── metadata.json          # title, tags, prompt, persona, ISRC-pending
            ├── audio_a.mp3
            ├── audio_b.mp3
            └── cover.jpg              # downloaded from Suno
```

`metadata.json` schema:
```json
{
  "persona": "Anicca Sounds",
  "title": "Returning to Stillness",
  "tags": "meditation, ambient, tibetan bowls",
  "prompt": "deep ambient meditation, tibetan singing bowls...",
  "model": "V5",
  "instrumental": true,
  "duration_a_seconds": 240,
  "duration_b_seconds": 245,
  "generated_at": "2026-04-28T14:00:00+09:00",
  "task_id": "abc123...",
  "distrokid_uploaded": false,
  "spotify_url": null,
  "isrc": null,
  "stream_count_30d": null
}
```

## Workflow when invoked

When the user says "make music" / "音楽作って" / "generate meditation track":

### Step 1 — Confirm persona + theme

Ask the user (one question only) which persona to use, OR pick by inference:
- "瞑想" / "ambient" → Anicca Sounds
- "和" / "tibetan" / "koto" → 無常 Mujō
- "528hz" / "binaural" / "frequency" → Bodhi Frequencies

If unclear, default to **Anicca Sounds** (broadest market).

### Step 2 — Generate prompt + title

Use the persona's tag set + Anicca's impermanence theme. Examples:

| Persona | Prompt template |
|---------|----------------|
| Anicca Sounds | `"deep ambient meditation, soft synth pads, slow drone, contemplating impermanence, 8 minutes, no vocals"` |
| 無常 Mujō | `"tibetan singing bowls, shakuhachi flute, zen garden, slow tempo, mujō meditation, 7 minutes"` |
| Bodhi Frequencies | `"528hz healing frequency, binaural beats, ambient pads, deep relaxation, 10 minutes"` |

Title: short, evocative, English (better Spotify search). Examples: "Returning to Stillness", "Empty Mountain", "528 Hz Awakening", "Mujō", "The River That Was".

### Step 3 — Call apiframe Suno

POST `/suno-imagine` with the params above.
Get `task_id`.

### Step 4 — Poll until finished

Poll `/fetch` every 15 seconds. Hard timeout: 5 minutes.

### Step 5 — Download + save

```bash
PERSONA_SLUG="anicca-sounds"  # or mujo / bodhi-frequencies
DATE=$(date +%Y-%m-%d)
BASE="/Users/anicca/anicca-project/music-factory/${PERSONA_SLUG}/${DATE}"
mkdir -p "$BASE"

# Find next version number
N=1
while [ -d "$BASE/v$N" ]; do N=$((N+1)); done
DIR="$BASE/v$N"
mkdir -p "$DIR"

curl -L "$AUDIO_URL_A" -o "$DIR/audio_a.mp3"
curl -L "$AUDIO_URL_B" -o "$DIR/audio_b.mp3"
curl -L "$IMAGE_URL"   -o "$DIR/cover.jpg"
# Write metadata.json
```

### Step 6 — Report

Tell the user:
- Where the files are
- Title, persona, tags
- Next manual step: upload to DistroKid → Spotify

## Cost reference

| Plan (apiframe.ai) | Price | Credits/month | Suno V5 songs/month |
|---------------------|-------|----------------|---------------------|
| Free | $0 | 20 | ~4 (testing only) |
| Basic | $19/mo (yearly $39 first month) | 1,000 | ~200 |
| Starter | $99/mo | 5,500 | ~1,100 |

Source: https://apiframe.ai/pricing (verified 2026-04-28)

Each Suno V5 IMAGINE call = ~5 credits (2 audio variations). Confirm exact cost in apiframe dashboard after first call.

## Distribution (manual phase)

After generation, the user uploads manually to **DistroKid → Spotify**:

1. Login: https://distrokid.com (Musician plan $24.99/year)
2. Upload → New Single
3. Artist name = persona (Anicca Sounds / 無常 Mujō / Bodhi Frequencies)
4. Song title = from `metadata.json`
5. Audio file = `audio_a.mp3` (or `audio_b.mp3`)
6. Cover = `cover.jpg`
7. Genre = Ambient / New Age / Meditation
8. Confirm "I declare this is AI-generated" (Spotify 2025 rule)
9. Submit → typical 1-3 days to appear on Spotify

Update `metadata.json` after upload:
```json
{ "distrokid_uploaded": true, "isrc": "...", "spotify_url": "..." }
```

## Automation upgrade trigger

When the user reports **>$500/month Spotify royalties**, upgrade this skill to:
- Cron: 04:00 JST daily
- Playwright DistroKid auto-upload
- Spotify for Artists API analytics ingest
- Slack #metrics report

Until then: stay manual. Don't burn money on cron-generated unsold catalog.

## Article strategy (Spotify monetization laws)

See `strategy.md` for full analysis. Core laws:

| # | Law |
|---|-----|
| 1 | Pick passive-listening niches (meditation, sleep, lo-fi). Avoid pop. |
| 2 | Volume > quality. 80-track catalog earns more than 8. |
| 3 | Consistent release cadence (weekly). Spotify rewards "active artist". |
| 4 | Doubling down on hits. When one track gets traction, generate similar. |
| 5 | Multiple personas. Each persona = different niche = wider reach. |

## Compliance notes

- **Spotify AI disclosure (2025)**: All AI-generated tracks must be declared. DistroKid has a checkbox.
- **Suno lawsuit (ongoing)**: Major labels suing. Apiframe.ai uses Suno via API; legal risk passes through. Monitor news.
- **Spotify removed 75M AI tracks in 2025**: Most were spam/duplicate. Original tracks with proper metadata survive.

## Files in this skill

| File | Purpose |
|------|---------|
| `SKILL.md` | This file. Main instructions Claude reads when invoked. |
| `strategy.md` | Full article + 5 monetization laws + Anicca brand alignment. |
| `scripts/generate.sh` | Bash script implementing the full flow (Step 1-6 above). |
