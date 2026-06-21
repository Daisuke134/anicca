# Life Manager — LAUNCH EXECUTION ORDER (do top→bottom, ONE at a time, never skip)

Date: 2026-06-21. THIS is the execution order. Do #1, finish it, then #2. Do NOT jump ahead.
Reason this file exists: jumping around / forgetting happens when the order isn't written down. It is now.
Companion: full architecture/state = `2026-06-21-life-manager-CANONICAL.md`. This file = the ORDER only.

## RULE
- Search FOREVER before acting (read the real files; never guess). 
- The marketing video is NOT reelclaw and NOT larry — see #5; saying "reelclaw/larry" again = wrong.
- After every step: update this file (mark ✅) + commit + push.

## ORDER (current top = do this next)

1. **#61-a — flip /lm pay to LIVE Stripe ($20/mo real).** Set GH Actions secret
   NEXT_PUBLIC_STRIPE_LM_URL = the LIVE link `https://buy.stripe.com/00w9ATf8yaJwghG6ge2880v` + rebuild →
   pay button charges real money. Live webhook secret already in Netlify. DONE = /lm bundle contains the
   live link + a real subscribe works. GATE: needs Dais's explicit "go live" (real charging).
2. **#61-b — full NEW-user onboarding E2E (web).** A fresh Google account → /lm login → Composio gcal +
   Unipile gmail connect → phone → pay → dashboard → real wake call fires. DONE = a never-seeded user got
   a real Charon call. GATE: a fresh Google account (agent cannot create Google accounts) → Dais provides
   a 2nd Google / does it on his phone, OR the first real launch user is the proof.
3. **#67-real — Telegram full E2E (real delivery).** A real Telegram user does /start on @LifeManagerBotbot
   → name in chat → web connect (carries name) → phone in chat → pay → done; then an ask question delivers
   to Telegram and a typed reply writes the calendar. DONE = real bot messages received + reply lands.
   GATE: a real Telegram user (Dais /start on his phone) + the same fresh-Google gcal connect as #61-b.
4. **#70 — users WITHOUT Google Calendar.** Outlook via Composio + agentic "tell me your schedule" chat
   fallback so a non-gcal user still gets wake calls. DONE = an Outlook (or chat-told) user is scheduled +
   called. ★ AGENT CAN DO THIS SOLO — no Dais gate. ★
5. **VIDEO SKILL (the daily TikTok content) — NOT reelclaw, NOT larry. BUILD a new skill.**
   Concept (Dais's, recorded here so it's never forgotten): we ALREADY have the demo OUTPUT + the SCRIPT in
   the Life Manager files. The ongoing content engine = RECORD Dais + Anitra talking every day → store the
   recording + TRANSCRIPT locally in files → use that as fresh daily content (put transcripts on it) → that
   is why there is new content every day → auto-post to **@anicca.comedy on TikTok** (account already
   decided). TODO: (a) FIND + read the existing LM demo output + script files (search forever), (b) build a
   skill that turns a daily recording+transcript into the video, (c) OpenClaw cron → daily auto-post to
   @anicca.comedy, (d) E2E verify a real post (URL + frame + audio). This is #45/#50 — do it AFTER 1-4.
6. **#51 — LAUNCH: Product Hunt + X.** After 1-5. Public/irreversible → Dais confirms before broadcasting.

## Parallel / post-launch (not in the critical path)
- #74 slice5 (local converge, needs Dais's Mac real call) · #29 STEP2 · #72 OpenClaw unify (post-launch).

## ORDER (corrected by Dais 2026-06-21 — #70 DROPPED, not now)
1. **#61-a** flip /lm pay to LIVE Stripe — GATE: Dais "go live" (real $20 charging).
2. **#61-b** full NEW-user web onboarding E2E — GATE: a fresh Google account (agent can't create one).
3. **#67-real** Telegram full E2E (real delivery) — GATE: real /start + same fresh Google.
4. **#45/#50 demo-reel skill** — ★ FOUND the existing demo OUTPUT (verified by transcript 2026-06-21):
   `~/Desktop/anicca_wake_promo_v1.mp4` (52s) + `anicca_wake_promo_v2.mp4` (34.7s) = Anicca/Charon voice
   wake-call demo (JA). v2 transcript: "ダイス、聞こえてる? 8時7分、またやっちまったって後悔する苦しみ、
   今日で終わりにしよう。さあ起きるぞ … 面白さより堅実だ。今すぐ行動しろ。立て。顔笑ってこい … 苦しみを
   終わらせるためだ。寝坊して自己嫌悪に陥る毎日を、今日で終わりにする". This IS the format. Posting infra =
   Postiz API (POSTIZ_API_KEY). Remotion skill = `skills/remotion`. The #12 product-demo storyboard =
   `docs/superpowers/specs/anicca/marketing/demo-video-plan.md` (separate, Dais-go for upload). NEXT for
   #45/#50: build a skill that takes a real Charon wake-call recording → transcript (whisper) → captioned
   reel → daily auto-post to @anicca.comedy. NOT reelclaw, NOT larry. ── ORIGINAL note kept below ──
   FIND the existing LM demo VIDEOS + SCRIPT files first (search forever),
   then build a skill: record Dais+Anitra talking daily → transcript → daily fresh video → auto-post to
   @anicca.comedy (TikTok). Posting infra = Postiz API (POSTIZ_API_KEY, multipart upload, type:"now").
   NOT reelclaw, NOT larry. ← agent can do most of this solo.
5. **#51** LAUNCH Product Hunt + X (after 1-4; Dais confirms broadcast).
6. **#77** slice5 local converge (needs Dais's Mac real call).
7. **#29** STEP2 (Dais dogfoods on web).

## STATUS (2026-06-21)
- ☐ 1 #61-a (Dais go-live)  ☐ 2 #61-b (fresh Google)  ☐ 3 #67-real (real /start)
- ⟳ 4 #45/#50 — FINDING the demo videos + script files NOW (then build the skill)
- ☐ 5 #51 launch  ☐ 6 #77  ☐ 7 #29
- #70 DROPPED.
