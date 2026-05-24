# Character Prompts — version control (永続記録、変更時は git diff で残す)

## EN avatar — anicca_en_monk_v2_yangmun (LOCKED 2026-04-27)
- HeyGen avatar_group_id: `6cb526e71b0f4e6a8d55a660ea69b359`
- HeyGen avatar look_id: `5a52533987c74ad4aadedfa881ce4554`
- Engine: `avatar_iv`
- Local files: `~/anicca-monk-factory/characters/en/icon_v2.png` (400×400), `icon_v2_full.png` (2048×2048)
- Profile pic for TikTok: copied to `~/Desktop/anicca-monk-demo/10_en_monk_icon_V2_yangmun.png`

### Prompt used
```
Photorealistic portrait of an elderly Theravada Buddhist monk, late 70s to 80s,
Southeast Asian features, fully shaved bald head with deep wisdom wrinkles around
eyes, gentle warm half-smile, wearing bright saffron orange Theravada robe over
the left shoulder, seated cross-legged inside a traditional warm-lit temple interior
with wooden floor and paper screen behind, small wooden lectern in foreground
holding an ancient palm-leaf scripture, single candle flame to the left casting
golden warm light on his face, soft warm cinematic 85mm lens shallow depth of
field, vertical 9:16 portrait composition, head and shoulders centered, calm wise
eyes looking warmly at camera, ultra detailed skin texture and robe fabric,
professional thumbnail framing
```

### Voice (LOCKED)
- HeyGen voice_id: `828b59f834fd4c7188da322b6d9b6c75` (David Castlemore)
- Settings: default speed × 0.9 (slow for authority — Shalev rule)

## JP profile icon — anicca_jp_anime (LOCKED 2026-04-19)
- Generated via fal-ai/nano-banana, watercolor anime chibi monk
- Local file: `~/anicca-monk-factory/characters/jp/icon_anime.png` (400×400)
- Profile pic for TikTok: `~/Desktop/anicca-monk-demo/02_jp_monk_icon_anime.png`

### Prompt used (nano-banana)
```
Watercolor Studio Ghibli style chibi young Japanese Buddhist monk boy, shaved head,
brown gray hemp kosode robe with a simple obi sash, traditional zori sandals, sitting
on a wooden temple veranda with cherry blossom petals falling, distant pagoda silhouette,
gentle morning light, soft pastel watercolor brush textures, kind half-smile,
hands gently clasped, circular profile-icon framing on white background, ultra clean
outlines, painterly soft shadows, isshin.mindstructure aesthetic
```

## JP scene reference set (TO LOCK after generation)
- 6 poses for character consistency across all video scenes
- Will be saved at `~/anicca-monk-factory/characters/jp/refs/pose_{01-06}.png`
- Each pose seeded with the icon_anime.png as reference image
- Poses:
  01_idle (standing, slight bow)
  02_sitting (lotus on veranda)
  03_gassho (hands together prayer)
  04_walking (mountain path)
  05_smile (close-up smile)
  06_contemplate (looking at sky)

## JP voice (LOCKED 2026-04-28)
- **Provider: OpenAI TTS** (better JP than ElevenLabs Adam)
- Model: `tts-1-hd`
- Voice: `onyx` (deep authoritative male, native JP support)
- Speed: `0.92` (slow for monk authority — Shalev rule)
- API endpoint: `POST https://api.openai.com/v1/audio/speech`
- Cost: ~$15/1M chars, JP-01 ~280 chars = $0.004 per video
- **Reason for switch from ElevenLabs**: Adam (`pNInz6obpgDQGcFmaJgB`) is English-native, JP came out unnatural. OpenAI Onyx is naturally deep + handles JP cleanly.

## JP scene reference set (LOCKED 2026-04-28)
5 reference scenes saved at `~/anicca-monk-factory/characters/jp/refs/test_pose_{01-05}.jpg` (720×1280). Same chibi watercolor monk character across all scenes.

### Pose 01 — temple veranda lotus pose
```
Watercolor Studio Ghibli style chibi young Japanese Buddhist monk boy, fully shaved bald head, brown gray hemp kosode robe with simple obi sash, traditional zori sandals, sitting in lotus position on a wooden temple veranda with paper-screen shoji door behind him, soft morning light, distant pagoda silhouette, cherry blossom petals falling, gentle half-smile with closed eyes, hands resting palms-up on knees, soft pastel watercolor brush textures with painterly soft shadows, clean black outlines, vertical 9:16 portrait composition full body visible, isshin.mindstructure aesthetic
```

### Pose 02 — mountain path with sakura
```
Watercolor Studio Ghibli style chibi young Japanese Buddhist monk boy, fully shaved bald head, brown gray hemp kosode robe with simple obi sash, traditional zori sandals, standing on a winding stone mountain path lined with cherry blossom trees in full bloom, looking up at sky with peaceful smile, distant misty mountains, soft pastel watercolor brush textures with painterly soft shadows, clean black outlines, vertical 9:16 portrait composition full body visible, isshin.mindstructure aesthetic
```

### Pose 03 — bamboo zen garden meditation
```
Watercolor Studio Ghibli style chibi young Japanese Buddhist monk boy, fully shaved bald head, brown gray hemp kosode robe with simple obi sash, traditional zori sandals, sitting cross-legged in a moss-covered Japanese zen garden with stone lanterns and raked white sand, eyes closed in meditation, slight smile, soft morning sunlight filtering through bamboo, soft pastel watercolor brush textures with painterly soft shadows, clean black outlines, vertical 9:16 portrait composition full body visible, isshin.mindstructure aesthetic
```

### Pose 04 — river crossing
```
Watercolor Studio Ghibli style chibi young Japanese Buddhist monk boy, fully shaved bald head, brown gray hemp kosode robe with simple obi sash, traditional zori sandals, walking by a clear shallow river with stepping stones, water reflections, surrounded by green ferns and small wildflowers, looking forward with calm expression, soft afternoon light, soft pastel watercolor brush textures with painterly soft shadows, clean black outlines, vertical 9:16 portrait composition full body visible, isshin.mindstructure aesthetic
```

### Pose 05 — sunset gassho
```
Watercolor Studio Ghibli style chibi young Japanese Buddhist monk boy, fully shaved bald head, brown gray hemp kosode robe with simple obi sash, traditional zori sandals, standing on top of a grassy hill at golden sunset, hands together in gassho prayer, distant temple roofs and pagoda silhouettes, warm orange sky with scattered clouds, soft pastel watercolor brush textures with painterly soft shadows, clean black outlines, vertical 9:16 portrait composition full body visible, isshin.mindstructure aesthetic
```

### Kling v2.5-turbo motion prompts per scene
```
Pose 01 → "gentle subtle breathing motion, soft eyes closing and opening slowly, sakura petals drifting down softly"
Pose 02 → "slight head tilt up looking at sky with peaceful smile, gentle wind in robe, cherry petals drifting"
Pose 03 → "meditative breathing motion, soft eye movement, dappled sunlight gently shifting through bamboo"
Pose 04 → "standing still by the stream, gentle water reflection movement, soft breeze, calm gaze"
Pose 05 → "hands together in gassho prayer, slight bow forward, sunset light shifting warmly"
```

Endpoint used: `fal-ai/kling-video/v2.5-turbo/standard/image-to-video`, duration `5s`, aspect_ratio `9:16`. ~$0.125 per clip.

## BGM (DROPPED 2026-04-28)
- **Decision: no BGM at all.** Narration alone, like Yang Mun's actual production style. Removed after user feedback that -18dB was too loud and music distracts from the monk's voice.
- File `~/anicca-monk-factory/assets/bgm/anicca_theme.mp3` kept on disk for future option but not used in production renders.

## BGM (LOCKED 2026-04-27)
- Source: Mixkit royalty-free `01_calm_184sec.mp3` (free for commercial use, no attribution)
- Track ID at Mixkit: 114
- Used for both EN + JP, baked at -28dB so narration sits on top
- Local: `~/anicca-monk-factory/assets/bgm/anicca_theme.mp3`

## Postiz integrations
- EN @anicca.monk TikTok: `cmo5rwq2p00twn10yrsdglng3`
- JP @anicchasan TikTok: `cmo5s4edx00vgn10ygnu34a0n`

## API keys (in `~/anicca-monk-factory/.env`, NOT in git)
- HEYGEN: stored at `~/.heygen/credentials` via `heygen auth login`
- POSTIZ: in `.env`
- APIFY: in `.env`
- FAL_KEY: in `.env`
- ELEVENLABS_API_KEY: in `.env`
- RESEND_API_KEY: in `.env` (re_448g2KGm_*)
- SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY: in `.env`
- STRIPE_SECRET_KEY (live): in `.env`
- STRIPE_SECRET_KEY_TEST: in `.env` (sk_test_*)
- KLING_ACCESS_KEY + KLING_SECRET_KEY: in `.env` (fallback only, primary is fal Kling)

## Asset Lock Rule
**Never re-generate any of the above without explicit user approval and a new version label (vN+1).** Cron generates ONLY the per-video script render — never re-creates avatars, voices, refs, BGM, or fonts.

archetype: talking-head
