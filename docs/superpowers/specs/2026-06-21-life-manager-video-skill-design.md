# life-manager-video skill — design (daily Charon wake-call → captioned reel → @anicca.comedy)

Date: 2026-06-21. Scope = JUST the video skill (#45/#50). Order/launch = `2026-06-21-life-manager-LAUNCH-ORDER.md`.
Status: DESIGN (do NOT build until LAUNCH-ORDER #1-3 are cleared; this is #4).
NOT reelclaw. NOT larry. A NEW skill named `life-manager-video`.

## ★ CORE (Dais 2026-06-21): CONTINUOUSLY record→download→STORE every real wake call ★
The content source is NOT a test call (a /test-call = "Anicca — test call", no real conversation → useless
for TikTok). The source = the REAL DAILY wake calls: Life Manager phones Dais before each event, Dais talks
back, Charon answers. dial.js ALREADY records every call (Telnyx record_start, mp3). What's missing + the
job: a recorder that CONTINUOUSLY pulls every new Telnyx recording → downloads the mp3 → STORES it locally
forever (`~/.openclaw/state/lm-video/recordings/<created>-<id>.mp3` + a manifest). Then each day a NEW
original video is built from that day's real conversation (same phone-call background, same whisper-caption
method) and posted. Never reuse an old clip. So:
  STORE pipeline (always-on): Telnyx recordings list/webhook → download new mp3 → local store + manifest.jsonl
  DAILY video: pick the latest REAL conversation (Dais actually spoke) → whisper JA → captions over the
  fixed phone-UI background → reel → post (2×/day, distinct clips) → verify.
Test calls must be FILTERED OUT (skip recordings whose transcript is just the test greeting).

## The asset we already have (the TEMPLATE)
`~/Desktop/anicca_wake_promo_v1.mp4` (52s) + `v2.mp4` (34.7s) = Anicca/Charon voice phoning Dais awake (JA),
verified by whisper. v2 transcript: "ダイス、聞こえてる? 8時7分、またやっちまったって後悔する苦しみ、今日で
終わりにしよう。さあ起きるぞ … 面白さより堅実だ。今すぐ行動しろ。立て。顔笑ってこい … 苦しみを終わらせる
ためだ。寝坊して自己嫌悪に陥る毎日を、今日で終わりにする". This visual+audio style = the format to reproduce daily.

## How the skill works (1 run = 1 daily post)
```
① CAPTURE   the day's REAL Charon wake call (Dais talking with Anicca) → audio file (+ start time, event).
            Source options (decide at build): (a) Telnyx call recording on the wake call, OR (b) the
            call-bridge saves the PCM/Opus of each call to storage. Store locally:
            ~/.openclaw/state/lm-video/<date>/call.(wav|opus) + meta.json.
② TRANSCRIBE  whisper (model small, --language ja) → transcript.txt + word/segment timings (for captions).
③ RENDER    Remotion (skills/remotion) composition `WakePromo.tsx`: phone-call mockup + animated waveform
            (driven by the real audio) + the transcript burned in as timed captions, 1080×1920 (vertical
            for TikTok) + a 1080×1080/landscape cut. Audio track = the real call audio. Deterministic
            (timings/props passed in, no new Date()/random — HARD render rules).
④ POST      Postiz API (POSTIZ_API_KEY): multipart upload the mp4 → create post type:"now" to the
            @anicca.comedy TikTok integration (id TBD — look it up via Postiz integrations once, store it).
            Optionally IG/X too. Caption from a small JA hook + #hashtags (no fabricated claims).
⑤ VERIFY    (HARD 0.31 / 0.24) Postiz returns releaseURL → poll the post state=PUBLISHED + fetch the
            public URL; extract a frame (caption visible) + confirm the audio stream exists (silent = fail).
            Append to a ledger ~/.openclaw/state/lm-video/history.jsonl (date, url, transcript hash).
⑥ CRON      OpenClaw cron — TWICE a day (Dais 2026-06-21): e.g. 09:30 JST (after the morning wake call)
            + 21:00 JST (evening). Each post = a DIFFERENT real clip/segment so the two daily posts are
            distinct. Fresh every day because the source is that day's real conversation. No rotation.
            FIRST DELIVERABLE (Dais's explicit ask): make ONE video NOW from today's/yesterday's real
            Dais×Anicca transcript using this skill, self-verify (frame+audio+captions), then EMAIL the
            mp4 to keiodaisuke@gmail.com for his approval BEFORE the auto-post cron goes live.
```

## ★ CAPTION STYLE = monk-factory real-time word-synced jimaku (Dais 2026-06-21) — NOT static SRT ★
Static burned SRT was WRONG. The original `anicca_wake_promo_v2.mp4` was made with the ai-monk-factory
real-time-transcription method (`~/.openclaw/skills/anicca-monk-factory-v3/scripts/burn-captions.sh` +
`build_ass.py`): whisper `--word_timestamps` → an `.ass` of small word-synced chunks, CENTER, white text
with ONE YELLOW keyword (the promo's "8時7分" was yellow), heavy font (TikTok Sans Display Black 90),
Alignment=5, outline 3. life-manager-video MUST reuse this exact engine (JA-adapted: phrase chunks, no
uppercase) burned over the phone-call UI background so it matches the promo Dais perfected. Replace the
static make-reel-from-audio caption step with build_ass.py word-synced .ass.

## DEPLOY + RECORDING BUGS TO FIX FIRST (B, Dais 2026-06-21)
- **Deploy**: Railway serves STALE code — deployments report SUCCESS but /health stays on an old marker
  (slice4) even though the latest commit (real-event /test-call patch) is on origin/main. `railway up`
  fails (github-source conflict); serviceInstanceDeployV2 returned a deploy id but live didn't update. FIX
  before any call (else /test-call still says the hardcoded "test").
- **Recording**: no Telnyx recordings since 2026-06-18 — record_start (dial.js, `.catch(()=>{})` swallows
  errors) isn't capturing recent calls. FIX + verify a fresh call records before relying on it for content.

## BUILD STATUS (2026-06-21)
- ✅ **STORE pipeline** — `~/.openclaw/skills/life-manager-video/store-recordings.py` downloads every
  Telnyx wake-call mp3 → `~/.openclaw/state/lm-video/recordings/` + manifest.jsonl. 34 backfilled.
  Continuous cron `lm-video-store-recordings` every 2h. (Today's MECA call recording not yet in Telnyx —
  appears after processing; the cron catches it.)
- ✅ **make-reel.sh** (mp4 → whisper SRT → ffmpeg caption burn → 1080×1920) — proven on the old promo.
- ⏳ **audio→reel generator** — NEXT: stored mp3 (real call) + fixed phone-UI background (showwaves
  waveform + "Anicca" caller) + burned captions → reel. (make-reel currently needs an mp4; add an
  mp3→reel path.)
- ⏳ **categorize** — transcribe each stored call → tag UTILITY (Charon nudges, user acts) vs BLOOPER
  (no answer / confusion, e.g. the 歯医者 call where Dais didn't respond). Post both kinds.
- ⏳ **post cron** — 2×/day to @anicca.comedy via Postiz (resolve integration id once) + verify POST_ID.
- ⚠️ in-call wording: Charon must NEVER say "test" (Dais) — every call is real + postable.

## Build steps (when we reach #4) — each: code → test → no-mock E2E (a real post) → verify → push
1. **capture**: pick + wire the recording source (Telnyx call recording is the least-invasive — flip the
   wake call's `record` param, fetch the recording URL after hangup). Save audio + meta locally.
2. **transcribe**: whisper wrapper → transcript + segment timings JSON.
3. **render**: Remotion `WakePromo.tsx` matching the promo style; props = audio path + caption segments;
   output vertical + landscape mp4. (Reuse `skills/remotion` + `remotion-best-practices`.)
4. **post**: Postiz upload + type:"now" to @anicca.comedy; resolve the integration id once + store it.
5. **verify**: releaseURL → PUBLISHED + frame + audio + ledger.
6. **cron**: `~/.openclaw/cron/jobs.json` daily 09:30 JST; fire once on install to confirm a real POST_ID.

## Honesty / guardrails
- Real call audio + real transcript only — never a fabricated conversation (HARD 0.24).
- @anicca.comedy is the decided account. Verify the real published URL before claiming done (HARD 0.31).
- Posting is outward-facing but it's the agent's OWN content channel on the agent's standing plan →
  no per-post Dais approval needed (this is a designed autonomous content channel, like the other
  reelclaw/honne daily crons). Dais edits copy only if he wants.

## Open decisions (resolve at build, not now)
- Capture source: Telnyx call-recording (preferred) vs bridge-saves-audio.
- @anicca.comedy Postiz integration id (look up once).
- Caption styling (font/position) to match the promo.
