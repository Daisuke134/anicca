# Life Manager — LAUNCH EXECUTION ORDER (do top→bottom, ONE at a time)

Date: 2026-06-21. THIS file = the ORDER only. Architecture/state = `2026-06-21-life-manager-CANONICAL.md`.
Video skill design = `2026-06-21-life-manager-video-skill-design.md`.
RULE: search the real files before acting; never guess. The video is NOT reelclaw, NOT larry.
After every step: mark it here + commit + push.

## ORDER + STATUS
1. ✅ **#61-a — /lm pay → LIVE Stripe.** DONE+VERIFIED 2026-06-21: GH secret NEXT_PUBLIC_STRIPE_LM_URL =
   `buy.stripe.com/00w9ATf8yaJwghG6ge2880v`, rebuilt, bundle confirms real $20/mo. Live webhook secret in Netlify.
2. ☐ **#61-b — full NEW-user web onboarding E2E.** fresh Google → /lm login → Composio gcal+gmail → phone →
   pay → dashboard → real wake call. GATE: a fresh Google account (agent can't create one) → Dais 2nd Google,
   or the first real launch user is the proof.
3. ☐ **#67-real — Telegram full E2E (real delivery).** real /start on @LifeManagerBotbot → name → web connect
   → phone → pay → done; ask delivers to TG + reply writes the calendar. GATE: real /start + same fresh Google.
4. ⟳ **#45/#50 — life-manager-video skill.** Skill BUILT: `~/.openclaw/skills/life-manager-video/make-reel.sh`
   (whisper JA SRT → ffmpeg burn captions → 1080×1920 reel). First output `anicca_wake_promo_v2-captioned.mp4`
   SELF-VERIFIED (frame: phone-UI "Anicca" + burned captions; audio ok; 34.7s) + EMAILED to keiodaisuke@gmail.com
   (gmail id 19ee97ed85104557). AWAITING Dais approval. THEN: (a) daily-call capture source (Telnyx recording),
   (b) 2×/day cron (09:30 + 21:00 JST, distinct clips) auto-post to @anicca.comedy via Postiz, (c) verify real
   POST_ID + frame + audio per post.
5. ☐ **#51 — LAUNCH: Product Hunt + X.** After 1-4. Public/irreversible → Dais confirms broadcast.
6. ☐ **#77 — slice5 local converge** (run same node app w/ LIFE_TRANSPORT=gog; needs Dais's Mac real call).
7. ☐ **#29 — STEP2** (Dais dogfoods on web).

#70 DROPPED (not now). Post-launch: #72 OpenClaw unify.
