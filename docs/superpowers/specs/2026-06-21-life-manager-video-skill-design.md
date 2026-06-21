# life-manager-video skill — design (daily Charon wake-call → captioned reel → @anicca.comedy)

Date: 2026-06-21. Scope = JUST the video skill (#45/#50). Order/launch = `2026-06-21-life-manager-LAUNCH-ORDER.md`.
Status: DESIGN (do NOT build until LAUNCH-ORDER #1-3 are cleared; this is #4).
NOT reelclaw. NOT larry. A NEW skill named `life-manager-video`.

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
