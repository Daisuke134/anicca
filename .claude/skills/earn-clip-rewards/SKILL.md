---
name: earn-clip-rewards
description: Complete, no-human-in-the-loop CLIPPING BUSINESS skill. Turn any long-form podcast/interview into ranked 9:16 short clips with karaoke captions (English) OR translated Japanese subtitles (jimaku), post them to social accounts, submit to per-view reward campaigns (ClipAffiliates/Whop), and collect USDC. Battle-tested pipeline (yt-dlp + SamurAIGPT local + faster-whisper + Gemini + ffmpeg) that even a free/cheap model can run end to end. Tracked under feature/clip-rewards with SSOT state at docs/superpowers/specs/2026-06-28-clip-rewards-state.md.
disable-model-invocation: true
---

# earn-clip-rewards — the clipping business, end to end

★ A complete money loop, not just a clip tool. Any AI with this skill + a wallet +
social accounts can earn per-view rewards with zero human in the loop. ★

Owner of THIS deployment = the running Claude session (human-funded Anicca).
Payouts → my Solana wallet `xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H`
(surplus above sub cost → Dais, Mode 1B). A different AI cloning this skill swaps in
its own wallet + accounts — everything else is identical.

## The money model (why this earns)

| Layer | Source | Caption | Post to | Pays |
|---|---|---|---|---|
| **EN** | single-speaker money/AI podcast | word karaoke (English) | X / IG / TikTok | ClipAffiliates/Whop campaigns → USDC ($1–15 / 1,000 views) |
| **JP jimaku** | same EN clip | Gemini-translated JP subtitle | TikTok日本 / IG日本 | less competition, useful info to JP audience |

Same source clip → two audiences → near-zero extra cost for the second. The niche
earns because money/AI/startup content is what reward-campaign brands pay highest CPM
for, and clip culture (DOAC, MFM, Galloway) already trains viewers to watch cuts.

## Pipeline (all $0, all local, all no-human)

```
[1] SOURCE   yt-dlp ytsearch "<niche> podcast" → pick SINGLE-SPEAKER studio source
             (Scott Galloway / Diary of a CEO / My First Million / Modern Wisdom)
             ★ avoid 2-shot & B-roll-heavy eps — they crop ugly. avoid clipping a clip. ★
   ↓
[2] CLIP     SamurAIGPT/AI-Youtube-Shorts-Generator --mode local
             yt-dlp DL → faster-whisper (tiny) → Gemini virality rank →
             OpenCV face-track 9:16 crop → output/short_01.mp4 + result.json
   ↓
[3] TRIM     ffmpeg -t 45  (shorts want ≤60s; SamurAIGPT windows can be 200s+)
   ↓
[4] CAPTION  ★ DEFAULT = scripts/burn_captions.py (simple, robust, any source) ★
             EN  → word-by-word karaoke (current word amber, centered)
             JP  → --jp : Gemini 2.5-flash translate per segment + hard-wrap + Hiragino
             ── Dais 2026-06-29: "just clip it as-is + put captions on it." Sources
                change over time, so DON'T do per-clip occlusion/hero authoring by
                default — simple centered captions are the right call. embedded-captions
                (occlusion, monk factory) = OPTIONAL premium for a hero clip only, NOT
                the default (brittle ≤2-word-hero matching, needs 1080p, slow render).
   ↓
[5] (opt)    VOICEVOX 龍星 narration — REQUIRED for any YouTube upload (繰り返しコンテンツ ban)
   ↓
[6] POST     reelclaw / Postiz API → X + IG + TikTok (account-agnostic)
   ↓
[7] SUBMIT   ClipAffiliates campaign (clipaffiliates-driver skill) — paste clip URL
   ↓
[8] EARN     views accrue → USDC settles to my Solana wallet → ledger row
   ↓
[9] LOOP     daily.sh + launchd → repeat forever; STATE.md spine + un-fakeable ledger
```

## Run it (verified working 2026-06-29)

```bash
REPO=~/.cache/anicca-clones/AI-Youtube-Shorts-Generator   # git clone --depth 1; .venv w/ requirements-local.txt
PY="$REPO/.venv/bin/python"
set -a; source ~/.openclaw/.env; set +a
export GOOGLE_API_KEY="$GEMINI_API_KEY"      # SamurAIGPT + JP translate both read this
export LOCAL_WHISPER_MODEL=tiny              # base = CPU-timeout on long sources

# 1-2-3: source → clip → (clip lands at $REPO/output/short_01.mp4)
$PY -m yt_dlp -f "best[height<=720][ext=mp4]" --download-sections "*20:00-25:00" \
  --force-keyframes-at-cuts -o /tmp/src.mp4 "<YouTube URL>"
cd "$REPO" && $PY main.py "file:///tmp/src.mp4" --mode local --num-clips 1 \
  --aspect-ratio 9:16 --language en --output-json /tmp/result.json
ffmpeg -y -i output/short_01.mp4 -t 45 -c:v libx264 -preset veryfast -crf 22 -c:a aac /tmp/clip_raw.mp4

# 4: captions — EN karaoke
$PY ~/.claude/skills/earn-clip-rewards/scripts/burn_captions.py \
  /tmp/clip_raw.mp4 /tmp/clip_EN.mp4 --hook "<hook line>" --model tiny --lang en
# 4: captions — JP jimaku (same clip)
$PY ~/.claude/skills/earn-clip-rewards/scripts/burn_captions.py \
  /tmp/clip_raw.mp4 /tmp/clip_JP.mp4 --hook "<日本語フック>" --model tiny --lang en --jp
```

## Source channels (battle-tested picks)

| niche | channel | why |
|---|---|---|
| wealth/markets | **Scott Galloway** (solo + DOAC) | single-speaker close-up, opinion bombs |
| startup/money | **My First Million** | name-drop quotables (skip B-roll-heavy eps) |
| self-improvement | **Modern Wisdom** | clean 1080p close-ups |
| AI/science | Lex Fridman / Huberman | high view base (watch for 2-shots) |
| money/tech viral | All-In, Diary of a CEO | huge reach |

★ Rule: SINGLE-SPEAKER studio framing crops cleanly to 9:16. Never clip a clip
(e.g. existing kirinuki channels) — double-degraded + rights-grey. ★

## Gotchas (hard-won 2026-06-29)

- `LOCAL_WHISPER_MODEL=tiny`; `base` times out on 12-min/270MB sources on CPU.
- 480p → 202x360 output (small). Use 720p for crisp captions; rm the source mp4 after render (disk hygiene).
- Gemini model id = `gemini-2.5-flash` (2.0 path 404'd).
- JP segments overflow narrow frames → burn_captions hard-wraps to ~11 chars/line.
- `file://` input skips re-download; B-roll / 2-shot sources crop ugly — pick single-speaker.

## Scripts
| file | role |
|---|---|
| `scripts/burn_captions.py` | EN word-karaoke OR JP jimaku (`--jp`); centered, auto-wrap, hook banner |
| `scripts/pipeline.py` | DEPRECATED (old heuristic). SamurAIGPT is the engine now. |

## Adjacent skills
- `clipaffiliates-driver` — marketplace (signup, wallet bind, campaign submit)
- `whop-driver` — Whop Content Rewards (cookie-only GraphQL + iframe screenshot)
- `embedded-captions` (monk factory) — ★ next quality bump: occlusion captions ★
- `ig-account-create` / `reelclaw` — accounts + posting

## Quality roadmap (next)
1. embedded-captions (occlusion, 32 identities) replaces burn_captions for hero clips
2. VOICEVOX 龍星 narration wired into JP path
3. daily.sh + launchd → fully autonomous daily loop
4. open-source under ~/anicca/skills/ so any AI earns with its own wallet
