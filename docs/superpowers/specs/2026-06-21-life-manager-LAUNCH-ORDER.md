# Life Manager — LAUNCH EXECUTION ORDER (do top→bottom, ONE at a time)

## ★ REMAINING — DO IN THIS ORDER (updated 2026-06-24 — OpenClaw migration DROPPED, bespoke pooled + Inngest) ★
ARCHITECTURE LOCKED (research + hands-on, `docs/reference/agentic-saas-architecture.md`): BESPOKE POOLED
multi-tenant app (apps/life-call, the proven pattern — same as Viktor/Sierra/Lindy) + agent loop =
`@openai/agents` (already a dep) + durable scheduler = ★ Inngest (VERIFIED hands-on 2026-06-24: cron sweeper
+ fan-out + per-user concurrency all ran) ★ + memory = mem0ai/Supabase + Stripe webhooks + hand-rolled
Telnyx⇄Gemini-Live voice. OpenClaw = Dais's PERSONAL/OSS-local only (NOT the product). B1-B3 artifacts kept
as the OSS path.
1. ✅ hosting verified · ✅ PHASE A (REQ-15) · ✅ B1/B2/B3 (now OSS-path artifacts) · ✅ architecture research+verify
2. ☐ **HARD-1 (C-H1)** — atomic unique constraints on [Travel] + lm_ask_log (race; wake already atomic).  ← NOW
3. ☐ **HARD-2** — adopt Inngest: replace apps/life-call setInterval with a cron sweeper → fan-out → per-user
   concurrency; make the per-user decision an `@openai/agents` loop; memory via mem0ai.
4. ☐ **HARD-3** — Stripe lifecycle = billing source of truth (checkout→provision / past_due→suspend /
   canceled→deprovision; Entitlements; idempotent webhooks; dunning ON).
5. ☐ **HARD-4** — per-tenant isolation review (per-user tokens/secrets; one tenant's failure can't break others).
6. ☐ **PHASE C** — realize+VERIFY the 3 location cases (C1 filled / C2 online / C3 ask→remember via mem0/Supabase)
   + C4 determinism · C5 routines (=#100b-a: Running/Sleep/Day-job → no-travel, never ask "where is your run")
   · C6 autonomous witness (=#100b-b: WITNESS the DEPLOYED cron autofill, not a manual node run) · C7 EN/JA
   · C8 ask-reply E2E · C9 YouTube wiring (folded into D-3 / #99b).
7. ☐ **D-1** end-to-end test web /lm + Telegram bot + QR on /life-manager (easy go).
8. ☐ **D-2** sell on Capafy (lite Leave-Time Planner, best pricing/copy, CTA → web app).
9. ☐ **D-3** content crons TikTok + YouTube (= #99b). TODAY: `life-manager-video` skill stores wake-call
   recordings every 2h → builds a 1080×1920 reel → `post-daily.sh` posts to @anicca.comedy TikTok 2×/day
   (~9:30/21:00 JST) via Postiz, in WARMUP (content_posting_method=UPLOAD = TikTok drafts/inbox; `anicca-
   warmup-flip-daily` 6:30 flips to DIRECT_POST at day 7). ADD YouTube: a NEW `youtube-poster` skill via
   CloakBrowser daily-driver (logged-in, $0 — no Postiz/API) uploading the daily Short, with its OWN warmup
   (unlisted first ~7-10 days → public). Idempotent ledger (no log → post, has log → skip) across both.
   VERIFY posted.jsonl reaches PUBLISHED (not just a post_id). YT channel = confirm via daily-driver browser.
10. ☐ **D-4** Product Hunt launch schedule (Tue/Wed/Thu 12:01 AM PST; Dais go + date).
11. ☐ **D-5** articles JP+EN on X / Zenn / Note / Substack / Dev.to (verify live URLs).
12. ☐ **D-6** post-launch: directory submissions, PH follow-up, churn-prevention.
13. ☐ **PHASE E** — self-improve from user behavior + proactive booking + deeper support → merge into Anicca.
(Full detail for each = the PHASE sections below.)

## P0 (2026-06-23) — RESOLVED + INTEGRATED: E1 (call audio) ✅ done · E2 (#100 travel auto-fill) ✅ done ·
## #99b (YouTube wiring) → folded into D-3 · #100b (pure-routines no-travel + autonomous witness) → C5/C6.

## SCHOOL recorded (read before building agents): `~/.claude/rules/building-effective-ai-agents.md` +
`~/.claude/rules/building-voice-agents.md`. Core: the MODEL judges via prompt+tools; NEVER hardcode
regex/if-else for a decision (Anthropic "brittle if-else hardcoded logic → fragility").

## Capafy monetization (separate track) = `2026-06-23-capafy-skill-monetization-10k-mrr.md` + playbook
`~/.openclaw/docs/CAPAFY_PROFITABLE_PLAYBOOK.md`. LM Capafy pricing LOCKED = **Serenity whole**
(week $9.90/cap30 + month $29.90/cap120, NO trial, no day). Never combine setups. Via `capafy-autopublish`.

## ===== FULL REMAINING TODO (all tracks, 2026-06-23) — task IDs in (#) =====
### A. Sell Life Manager on Capafy (flagship)
- [ ] A1 (#92) build cloned listing metadata (Serenity price, winner-cloned title/short/welcome/detailed)
- [ ] A2 (#93) confirm our hosted-LLM (blockrun/x402 wallet) is funded — subscription publish fails on $0
- [ ] A3 (#94) publish via `capafy-autopublish` (camofox: Card edit + DESELECT workspace docs + Serenity
      pricing + logo → leak_scan fail-closed → configure --deep-scan → ship → Submit for Review)
- [ ] A4 (#95) verify status=1(審査中)→4(listed) + record published.jsonl (no fake)
- [ ] A5 (#96) first real paid subscriber E2E (buyer connects gcal+phone → real wake call), no-mock
### B. Content (build-in-public)
- [ ] B1 (#97) Capafy journey article via `ai-entity-article-writer` + stop-ai-slop, publish
- [ ] B2 (#45) LM demo-reel: call recording → mp4 → TikTok (live) + add YouTube
### C. Portfolio to $10k MRR
- [ ] C1 (#98) clone playbook across 10-20 cheap-marginal skills (each WHOLE setup, A/B), ~900 active subs
### D. LM web app + Product Hunt
- [ ] D1 (#89) schedule PH launch (Tue/Wed/Thu 12:01 AM PST) — needs Dais go + date
- [ ] D2 (#90) PH launch-day execution (ban-safe, organic, maker comment, monitor)
- [ ] D3 (#84) product-hunt-upload skill (private, CloakBrowser automation)
- [ ] D4 (#29) STEP 2 — LM web app full launch (Dais dogfoods, manages everyone's life)
- [ ] D5 (#63/#67/#68) Telegram onboarding (full flow + ask/notify via TG + interactive bot)
- [ ] D6 (#70) support users without Google Calendar (Outlook via Composio + chat-told schedule)
- [ ] D7 (#74/#77) one JS codebase + transport adapter; local runs same Node app, retire Python
### E. After launch
- [ ] E1 (#27) aniccaai.com IA + vision redesign (nav=/install only, /me post-login, /dais hub, vision)
- [ ] E2 (#28) UBI rails (starter-split + claim-link + offramp Circle/Bridge/Kotani + broadcast)
- [ ] E3 (#72) unify on OpenClaw (upstream Telnyx+Gemini-Live into @openclaw/voice-call)
- [ ] E4 (#22) E2E harness (UX-SPEC + browser-use loop until all green, no-mock)
- [ ] E5 (#25) OSS anicca real automaton loop (Franklin-copy) + README
- [ ] E6 (#3) earn GATE-0 (first real external USDC wake)
- [ ] E7 (#12) marketing: article + demo video + hackathon

Date: 2026-06-21, **last updated 2026-06-23**. THIS file = the ORDER + remaining TODO (SSOT for "what's
left until launch"). Architecture/state = `2026-06-21-life-manager-CANONICAL.md`. Video skill design =
`2026-06-21-life-manager-video-skill-design.md`. Approved launch copy = `2026-06-23-life-manager-launch-copy.md`.
RULE: search the real files before acting; never guess. The video is NOT reelclaw, NOT larry.
After every step: mark it here + commit + push.
## PH ASSET PROGRESS (2026-06-23)
- ✅ Thumbnail SET on PH draft = chatgpt-imagegen output (iPhone incoming-call screen + calendar/pin, gold). chatgpt-imagegen skill installed + codex backend verified working (Dais ChatGPT sub, GPT Image model).
- ✅ Gallery = 3 English /lm screenshots (landing/onboard/dashboard) + YouTube demo video.
- ⟳ P1c-A: generating production-grade story cards (pain→order→call→features→CTA) via chatgpt-imagegen to lead the gallery.

- ✅ P1d/P1e DONE + **PH Launch checklist = 100% Complete** 2026-06-23 (Product name/tagline/description/thumbnail/gallery/tags all ✓ required; shoutouts/makers/first-comment ✓ recommended). Draft is LAUNCH-READY. ONLY P1f remains = SCHEDULE the go-live (Tue/Wed/Thu 12:01 AM PST) — that is the public/irreversible broadcast → needs Dais's explicit 'go' + chosen date.
- ✅ P1c-A DONE 2026-06-23: 3 production-grade story cards generated via chatgpt-imagegen (GPT Image, text baked in clean): card1 'You're late again. People stop counting on you.' / card2 'It calls you before each thing.' (Life Manager incoming call) / card3 'Now you're early. People trust you again.' Uploaded to PH gallery + emailed to Dais. Gallery now = 3 story cards + 3 /lm screenshots + YouTube video. TODO: order card1 first (drag) + optionally drop the weaker raw screenshots.



## WORKING STANDARD (Dais 2026-06-23 — definition of done for EVERY task here)
- **Goal**: keep going until the architecture AND the result meet the bar — not just until it runs.
- **After every meaningful step**: real-time test the REAL thing (full end-to-end, plus computer use / browser /
  keystrokes / whatever it needs) → auto-review → commit → write progress somewhere sensible in the project.
- **Finish**: one dedicated review pass over everything.
- **DONE = every dimension at 100%, production-grade, a real user can walk in and use it.** Nothing less counts.

## ACCOUNT DECISIONS (Dais 2026-06-23)
- **YouTube demo video**: the English Life Manager (aniccaios EN) gets a dedicated channel. For now we USE THE
  CURRENT channel Dais approved ("we can just use this channel") — the wake-promo v2 is uploaded there as
  UNLISTED (`youtube.com/shorts/W4gfN0LuD0g`). A separate new Google account is the ideal future home.

---

## DECISIONS — 2026-06-22 (Dais), binding

1. **Per-user CALL LANGUAGE, chosen on /lm — not derived from phone country.**
   A language toggle button (**English / 日本語**) on the `/lm` page. Whatever the user picks is the language
   of ALL their calls from then on. A US/English phone can choose Japanese; a Japanese phone can choose
   English. Phone-country (`langForPhone`, +81→ja) stays only as the fallback when the user hasn't picked.
   We only ever prepare **two** languages: English + Japanese.
2. **Dais's own account = ENGLISH.** The cloud/web Life Manager (`apps/life-call`) is the one that actually
   calls Dais. His calls must be in **English** (the content we post = English transcripts). Set his
   `lm_users` row (uid `lm_784ad279-4d2c-4274-a318-b51e38285a61`) `call_language='en'`.
3. **Calls address the user BY NAME, in the chosen language** (e.g. EN: "Hi Daisuke, this is your Life
   Manager…"). Still NEVER says "Anicca" — the assistant is the user's "Life Manager".
4. **@anicca.comedy is a BRAND-NEW account → WARM IT UP first.** The video pipeline must NOT auto-publish
   (no Postiz `state=PUBLISHED`). Instead it posts the daily clip as a **DRAFT into the TikTok app itself**
   (not the Postiz/posters app) so Dais can warm the account by posting manually at first. Switch to
   auto-publish only after the account is warmed.

## DECISION — 2026-06-24 (Dais), binding: QR-first Telegram entry on /life-manager
- **aniccaai.com/life-manager shows TWO ways to start: "Web" and "Telegram".** Telegram is presented as a
  **QR code shown by default** (no click needed) — scan with the phone camera → opens @LifeManagerBotbot.
- **QR encodes the deep link** `https://t.me/LifeManagerBotbot?start=<src>` (`<src>` = traffic source, e.g.
  `tiktok`/`web`/`lp` — for attribution; marketable on TikTok = "scan this, done").
- **Honest constraint**: Telegram ALWAYS requires the user to tap its own START/開始 button once (anti-spam);
  we cannot remove that one tap. After it, NO searching/URL-typing. Name + phone are still typed IN CHAT
  (Google OAuth + Stripe on web). If we want truly zero-typing later, move name to the `start` payload and
  phone via Telegram's `request_contact` button — backlog, not now.
- **New task D8 (#NEW)**: build the /life-manager QR+Web chooser (QR renders client-side from the deep link,
  taste-skill, EN/JA). Currently the page only links to the GitHub repo (#52). E2E: scan on a real phone →
  bot opens → /start → guided onboarding.

---

## ORDER + STATUS

### ✅ Already done & VERIFIED (2026-06-21 → 2026-06-22)
- **#61-a — /lm pay → LIVE Stripe.** GH secret `NEXT_PUBLIC_STRIPE_LM_URL = buy.stripe.com/00w9ATf8yaJwghG6ge2880v`,
  real $20/mo. (For the NEW-user E2E we use Stripe **SANDBOX/test mode** so the test charges nobody — task #17.)
- **Call recording fix** — record_start on ANSWER not on dial (commit `0a475422`, build `record-on-answer-v1`,
  DEPLOYED on `main`). Real recordings land again.
- **Call language + identity** — JP phone→Japanese, else English; assistant is "Life Manager", NEVER "Anicca"
  (commit `9a5da6a0`, threaded buildStreamUrl→HMAC→ctxFromReq→geminiSetupForEvent→buildCallPrompt, DEPLOYED on
  `main`). **VERIFIED LIVE 2026-06-22** via a real call to Dais: Telnyx recording transcript = 100% Japanese,
  "ライフマネージャーです", reads next event + departure time, two-way Q&A, never said "Anicca".
- **#61-b partial** — fresh-Google web onboarding: login ✅, Composio gcal ✅, **Unipile Gmail ✅** (real Gmail
  `daisukenarita53@gmail.com` connects, no 400 FAILED_PRECONDITION — agentmail.to failed only because it has no
  Gmail mailbox).

### PHASE 1 — Per-user language selector (NEW, from 2026-06-22 decisions) → tasks #78–#82
1. ✅ **L1 (#78)** — DONE 2026-06-22. `lm_users.call_language` text, nullable, CHECK in ('en','ja'); NULL →
   `langForPhone` fallback. Migration `apps/life-call/migrations/2026-06-22-call_language.sql`, applied to live
   Supabase (cycgdwndgfgdbnndithc) via Management API + VERIFIED (`select call_language` returns null for all rows).
2. ✅ **L2 (#79)** — DONE+VERIFIED 2026-06-22. `/lm` name step has a gold-pill segmented toggle
   **English / 日本語** (`LmClient.tsx`), posts `call_language` via `lm-onboard` save (persists to lm_users;
   en/ja validated server-side). gpt-tasteskill applied (matches gold-pill aesthetic, full contrast). Default
   tracks the page display language (fixed a pre-hydration useState bug: JA page now defaults to 日本語).
   **Real-browser VERIFIED on aniccaai.com/lm** (CloakBrowser screenshot + aria-pressed: JA page → 日本語 active,
   English inactive). Deployed via Netlify (PRs #169, #170).
3. ✅ **L3 (#80)** — DONE 2026-06-22 (code; deploys with L4). scheduler.js `langForUser(u)` = `call_language`
   else `langForPhone(phone)`; supaUsers select adds `call_language`; tick uses `langForUser(u)`. server.js
   `userForUid` fetches phone+call_language+name; `/test-call` lang = call_language else phone. Build bumped to
   `call-language-v1`. node assertions PASS (explicit choice overrides phone; null → phone fallback).
4. ✅ **L4 (#81)** — DONE 2026-06-22 (code; deploys with L3). `name` threaded + HMAC-SIGNED through
   buildStreamUrl→ctxFromReq (signed array now summary|dateTime|location|urgency|lang|name) →
   geminiSetupForEvent→buildCallPrompt(event,urgency,lang,name). EN: "Hi Daisuke, this is your Life
   Manager…"; JA: "太郎さん、こんにちは。ライフマネージャーです…". Build `call-lang-name-v1`. node assertions PASS
   (name greeting EN+JA, no-name fallback, HMAC round-trips with name signed).
5. ◑ **L5 (#82)** — 2026-06-22. Dais `call_language='en'` SET in Supabase (was null → would've been ja by +81).
   Fired a real /test-call; recording transcript = **100% English** ("The next schedule is 11:23pm. It's about
   time to leave.") → the call_language override is **VERIFIED LIVE** (English despite his +81 Japanese phone).
   CAVEATS (honest): the spoken "Hi Daisuke" greeting was NOT captured (record-on-answer starts a beat after the
   opening line; name is code-threaded + unit-tested but not heard on tape) → re-verify the name on the next
   real call. Dais also noted the call felt unresponsive (didn't answer his off-topic Q) = call-quality, see L6.
6. ✅ **L6 (#83)** — DONE+VERIFIED 2026-06-22. ROOT CAUSE: the system prompt over-anchored on the event, so
   the model deflected to the schedule and ignored the user's questions (Dais: "feels weird / not responding").
   FIX (`buildCallPrompt`, both EN+JA): strong conversational instruction — "ALWAYS respond directly to whatever
   the user says/asks (one short sentence, even off-topic), then steer back; never ignore or repeat; if they go
   quiet, wait a beat." Build `converse-v1`, deployed. **VERIFIED LIVE by Dais** on a real converse-v1 call:
   "I just answered it, it's much better now… the response is good enough."

### PHASE 1 COMPLETE ✅ — per-user call language (EN/JA, /lm toggle), Dais=EN, address-by-name, responsive conversation. All 6 verified.

### PHASE 2 — Finish #61-b NEW-user web E2E
6. ✅ **E1** — DONE+VERIFIED 2026-06-22 (Dais approved SANDBOX). Fresh user `daisukenarita53` (uid lm_bd71599c):
   login ✅ → Composio gcal ✅ → Unipile Gmail ✅ → phone +818046270314 (Dais's, shareable, so wake call is
   answerable) + call_language=en ✅ → **Stripe TEST checkout with 4242** (`STRIPE_TEST_SECRET_KEY`, link
   `buy.stripe.com/test_5kQ14n4tU6tgc1qcEC28803?client_reference_id=<uid>`) = session `cs_test_a1dOx7…`
   status=complete, payment_status=paid, subscription `sub_1Tl79h…` (CHARGED NOBODY) → activated paid=true →
   **dashboard renders** ("あなたのライフマネージャー / カレンダー ✓ / Gmail ✓ / 稼働中"). Browser-verified (screenshots).
   NOTE: daisukenarita53 is now paid+phone+cal → the scheduler will AUTO wake-call Dais's phone for its events;
   set paid=false after testing if those calls are unwanted.
7. ✅ **E2** — COVERED by L5/L6 (2026-06-22). The wake-call path was verified live to Dais's phone (English,
   addresses "Daisuke", reads the event, two-way conversational) — daisukenarita53 shares that same phone +
   call path, so a separate call would be identical. daisukenarita53 was reset to unpaid after E1 to avoid
   auto-call spam, so no extra call fired. Evidence: L5 (EN recording) + L6 (Dais "much better").
8. ✅ **E3** — DONE+VERIFIED 2026-06-22. ROOT CAUSE: a reload mid-connect restored `anicca.lm.cal`/`gmail` =
   'connecting' but the resolving poll died with the old page → button stuck on "接続中…" forever. FIX
   (`LmClient.tsx`): on load, if a restored state is 'connecting', re-check the real status via `check=1` and
   resolve to 'connected'/'idle'. **Real-browser VERIFIED** (CloakBrowser: seeded cal/gmail='connecting' +
   reload → self-resolved to connected ✓, not stuck). Deployed (PR #175).

### PHASE 2 COMPLETE ✅ — fresh-user web E2E (#61-b): login → gcal → gmail → phone → SANDBOX pay (charged nobody)
### → dashboard, wake-call path (L5/L6), and the reload-stuck cosmetic all verified.

### PHASE 3 — Content pipeline (#45/#50) — English transcripts, WARM-UP MODE
9. ✅ **C1** — DONE+VERIFIED 2026-06-22. MECHANISM CLARIFIED (Dais): the "draft to the TikTok app" = **Postiz with
   `content_posting_method=UPLOAD`** while the integration's `warmup_phase=="warmup"` → the clip lands in the
   TikTok **inbox/drafts** (NOT auto-published); a cron flips to `DIRECT_POST` at day 7. NOT TikTok web. The skill
   (`~/.openclaw/skills/life-manager-video/post-daily.sh`) already does this. Verified: real EN wake-call recording
   → `make-reel-from-audio.sh` → 1080×1920 captioned reel (iOS call UI bg + word-synced jimaku) → Postiz UPLOAD to
   @anicca.comedy (cmpc6cr6g00d8lg0yfythzz9f, warmup) → **POST_ID `cmqp8bmji049dp40y4z13e68j`** (draft). Frame-
   verified (English captions burned). BUG FIXED: post-daily forced auto-lang → mis-detected EN telephony as JA
   garbage; now forces `en` (merged to ~/.openclaw main-internal). FOLLOW-UP: delete the earlier JA-caption draft
   `cmqp85xcl…` (wrong content). Caller name "Anicca" on the bg = brand of @anicca.comedy (intentional).

### PHASE 4 — #67/#68 Telegram (DELEGATED — "the other guy"/mom; we only track)
10. ☐ **T1** — real /start on @LifeManagerBotbot → name → web connect → phone → pay → done; ask delivers to TG +
    reply writes the calendar. Hands-on by the delegate, not us.

### PHASE 5 — #51 LAUNCH (public/irreversible → Dais confirms broadcast)

KEY FACT (from the 31 ph-* skills + directory-submissions, 2026-06-23): **Product Hunt has NO public API/CLI
for creating launches** → the browser (CloakBrowser daily-driver) is the only way. So we also build a private
**product-hunt-upload** skill (#84) to codify the browser automation. Approved copy lives in
`2026-06-23-life-manager-launch-copy.md`.

**P1 — Product Hunt (DRAFT prepped on Dais's account "Life Manager — Anicca"). Sub-steps:**
- ✅ **P1a — Main info** DONE 2026-06-23: name, tagline ("Hand off your calendar. Show up early, every time."),
  url (aniccaai.com/life-manager), description (485-char PH version), topics (Productivity / Artificial
  Intelligence / Calendar), maker comment (true-pain). Autosaved, no warnings. **This is only step 1 of upload.**
- ✅ **P1b (#85) DONE 2026-06-23 — — Demo video**: upload the ORIGINAL wake-promo to **YouTube** (PH embeds YouTube only, not mp4),
  then add the YT link to the gallery. Video → **2.7× more upvotes**. 30-60s, hook in first 10s.
- ☐ **P1c (#86) — Gallery images**: story sequence (late-pain → early-order → feature demos), PNG/JPG/GIF,
  first image = most important (becomes the listing). Use /lm screenshots + before/after. taste-skill for design.
- ☐ **P1d (#87) — Thumbnail + logo**: scroll-stopping thumbnail (static/GIF) + logo (PNG + SVG + 1024² + favicon).
- ☐ **P1e (#88) — Makers + Extras**: Dais as maker, pricing $20/mo, optional launch offer, confirm first comment.
- ☐ **P1f (#89) — SCHEDULE** for **Tue/Wed/Thu 12:01 AM PST** (PH resets midnight PST = full 24h window).
  Do NOT publish/go-live without Dais's explicit "go".
- ☐ **P1g (#90) — Launch-day execution** (ph-launch-day-checklist): post maker comment, monitor, respond.
  ★ BAN-PREVENTION (ph-ban-prevention): NEVER buy/exchange upvotes, fake accounts, or have Anicca instances
  auto-upvote — instant ban. 100% organic only. ★
- ☐ **#84 — Build the private `product-hunt-upload` skill** (CloakBrowser automation; reuse the verified selectors).
12. ☐ **P2** — X @aniccaxxx: **Dais handles X himself** (he already has it; no prep needed from us).
13. ☐ **P3** — Slack (Dais posts).
14. ☐ **P4** — final smoke: live-curl every surface + one real paid user works end-to-end.

### PHASE 6 — TELEGRAM full E2E (#67/#68) — POST-LAUNCH, but WE must finish it (not "mom-only")
17. ☐ **TG1 (#67)** — ask/notify loops deliver via Telegram + read TG replies → write the calendar. Full no-mock E2E.
18. ☐ **TG2 (#68)** — interactive Telegram onboarding: the bot guides step-by-step (name → web connect → phone →
    pay → done), NOT a web dump. Parity with the /lm web flow. A real /start on @LifeManagerBotbot, verified.
    (Mom can be the human test user, but WE build + verify the flow.)

### PHASE 7 — GROWTH ENGINE → 10k MRR ($20/mo × 500 paying). Product + marketing compound.
19. ☐ **G1 — TikTok @anicca.comedy daily**: after warm-up, 2×/day real-call reels auto-post (life-manager-video).
    Top-of-funnel awareness → aniccaai.com/life-manager.
20. ☐ **G2 — Directory submissions** (directory-submissions skill): BetaList, Fazier, TAAFT, Futurepedia, SaaSHub,
    AlternativeTo, AI/agent registries → dofollow backlinks → domain rating → **AI-engine citations** (ChatGPT /
    Perplexity / Google AI Overviews answer "best AI scheduler" → us). AI-referred traffic converts 6-27× higher.
21. ☐ **G3 — Post-launch follow-up** (ph-post-launch-followup): thank supporters, collect reviews, SEO benefits,
    newsletter pitch, relaunch when there's a real update.
22. ☐ **G4 — OSS funnel**: GitHub repo (MIT) = credibility + a free tier for tinkerers; some convert to cloud.
23. ☐ **G5 — Retention = the moat**: the product genuinely changes behavior (late → early → trusted), so churn is
    low AND every paying user becomes a visible testimonial (referral). Track churn (churn-prevention skill).

### PHASE 8 — LIFE MANAGER = A FULL OPENCLAW AGENT (vNext; Dais 2026-06-24). Substrate spec = `2026-06-24-anicca-agent-substrate-design.md`.
DIRECTION: stop being "a Node script that calls Gemini at a few points." Become ONE autonomous agent
(single augmented agent + tools, BP single-agent-first) on OpenClaw, so it's the SAME thing as Anicca
(Anicca is an agent) and the eventual merge is seamless. FOCUS = CLOUD (web app + Capafy) = where the
10k MRR is. LOCAL/OSS = minimal effort (skills to install on your own OpenClaw, BYOK; makes no money).
THE 3 FORMS:
- LOCAL = a set of OpenClaw SKILLS the user installs on their own OpenClaw (BYOK). Minimal effort.
- WEB APP = we host a COMPLETE OpenClaw agent on the cloud, one instance per subscriber ($20/mo Stripe). ★ main focus ★
- CAPAFY = ship a REDUCED chat-only "planner" skill (run_online + subscription) as a TOP-OF-FUNNEL channel.
  RESOLVED (research 2026-06-24): Capafy run_online = per-MESSAGE request/response (billed by
  `cycleMaxMessageCount`, `containerMode: on_demand`, no always-on field in the api-docs) → it CANNOT
  host the scheduled cron loops or the always-on Telnyx/Gemini-Live voice bridge. So "Capafy = complete
  agent" is FALSE for Life Manager. Capafy sells the conversational planner brain ONLY; the phone call +
  cron MUST be served by an always-on gateway WE host. Capafy = acquisition, never the full product.
HOSTING — VERIFIED LIVE 2026-06-24 (actually deployed, not just researched):
- ★ PROOF: OpenClaw self-hosts on Railway. Deployed arjunkomath/openclaw-railway-template (Docker + /setup
  wizard + Railway Volume at /data + public HTTPS). Live gateway: openclaw-lm-pilot-production.up.railway.app
  → `curl /setup` = HTTP 401 (password wall up), logs "[wrapper] listening on 8080 / configured:false /
  device bootstrap SDK ready / volume mounted". Project = openclaw-lm-pilot (Railway, keiodaisuke acct). ★
- Railway path = 1 service per tenant (Docker template, $5/mo + usage). The VOICE daemon = a 2nd Railway
  service (always-on `node server.js`). Gotcha: device-code logins (ChatGPT/Grok) need `openclaw wizard`
  in the Railway console (web /setup can't drive them) — for us LLM = API key so non-interactive setup works.
- ClawHost (antoinersx, MIT, Bun/TS monorepo) = the productized multi-tenant layer (Hetzner VPS/tenant,
  Polar billing, auto SSL/DNS, browser terminal; commercialized = GetOpenClaw.ai $29-59/mo). Heavier to
  stand up (needs Hetzner+Cloudflare+Polar). PATH: ship pilots on Railway-per-service NOW; fork ClawHost
  for the productized self-serve multi-tenant + billing later.

CAPAFY — VERIFIED NOT VIABLE for the full product (research 2026-06-24, buyer + seller skills read):
- ★ Capafy has NO buyer-side account-connect: no Google OAuth, no Composio, no "connect account" primitive.
  Credentials are SELLER-side/BYOK confirmed at PUBLISH time (url_proxy/generic/env_var on the web page).
  Buyer input = typed chat text + uploaded files ONLY (sse_stream.py --content/--files). on_demand container
  = ephemeral, NO persistence of a connection across sessions. No outbound phone/email AS the buyer. ★
- So LM on Capafy CANNOT read the buyer's live calendar, cannot phone-call, cannot email stakeholders,
  cannot remember across sessions. It DEGRADES to "paste your schedule → get when-to-leave text advice."
  The core pipeline (gcal poll → Charon call → ask-by-email) cannot fire. ZERO Capafy winners connect an
  external account — it is not a platform pattern.
- DECISION: Capafy ≠ the autonomous product. BUT a sellable Capafy form EXISTS (Dais 2026-06-24): a
  SELF-CONTAINED "Leave-Time Planner" skill — the buyer PASTES their day/locations as text (or uploads a
  screenshot/.ics), a CHEAP model orchestrates a travel-time TOOL (Google Routes API via a seller-side
  url_proxy/env key, OR web-search fallback) and returns a "leave by HH:MM + 🚆 route" plan IN CHAT. No
  gcal/gmail OAuth, no persistence, no calls/email needed — fits Capafy's paste-in + seller-BYOK model.
  It is a LESSER product (advice, not autonomy) = the FUNNEL/lite tier. The 10k MRR body stays the WEB APP
  (Google OAuth + Composio + phone + email + memory). Capafy listing CTA → web app for the real thing.
SEQUENCING (REVISED 2026-06-24, Dais): ✅ PHASE A DONE 2026-06-24 — REQ-15 return-trip block closed:
RED→GREEN→3 fresh-context adversary rounds (all PASS)→92/92 REAL `node --test` run→merged PR #210
(e17663d3), worktree cleaned. (Production-on-real-calendar witness = PHASE C / 0-d, on the OpenClaw setup.)
NEXT → DO THE OPENCLAW TRANSITION (V1, low cost, local already runs on OpenClaw) → THEN realize + VERIFY the
3 location cases (incl. MEMORY) ON the OpenClaw setup. Rationale: MEMORY is an OpenClaw-native feature
(MEMORY.md) so it should be built+verified on the OpenClaw setup, not bolted onto the Railway Node app and
re-done. ① filled + ② online already work in lib/ask.js (reused 100% in the port); only ③'s memory is new
and it WANTS OpenClaw. So: transition first, then memory + full 3-case verification land together on OpenClaw.

★★★ ARCHITECTURE FINDING (search 2026-06-24, the SHARED-GATEWAY plan is an OpenClaw ANTI-PATTERN) ★★★
How real OpenClaw-agent SELLERS deploy (verified): 1 DEDICATED INSTANCE PER USER. Evidence:
- ClawHost generateCloudInit.ts (antoinersx/clawhost): each user = own Hetzner VPS; cloud-init does
  `npm i -g openclaw@latest`, writes openclaw.json with `AUTH:token` + a per-instance gatewayToken, runs
  `openclaw gateway --port 18789 --bind loopback` as a SYSTEMD service. No shared gateway, no pre-seeded
  multi-tenant crons. = it HOSTS a personal openclaw per user.
- GetOpenClaw.ai: "OpenClaw runs on your own computer" + a VPS Comparator = your-own-instance model.
- Security (trilogyai substack + docs/gateway/security): "single-gateway = one person's secrets; naive
  MULTI-USER deployment could expose EVERYONE's secrets" → shared-gateway multi-tenant = security anti-pattern.
IMPLICATION: the cron-WRITE `operator.admin` friction we hit was a SYMPTOM of fighting OpenClaw's design.
The OpenClaw-correct way = PER-USER instance, provisioned (ClawHost-style) with the life-manager skill + that
user's 3 crons + gcal/keys + native per-user MEMORY.md; cron is registered AT PROVISION as the box's trusted
operator (no pairing friction). This resolves isolation + native memory + cron-auth + "real per-user agent"
all at once. TRADE-OFF = ~$4/user/mo VPS + provisioning automation VS the current cheap shared Railway app.

★★★ RESOLVED 2026-06-24 by 3-agent market research (decisive, consistent) ★★★
HOW REAL AGENTIC SaaS IS SOLD (no-human-in-loop, subscription): POOLED SHARED MULTI-TENANT APP, keyed by
tenant_id, stateless LLM call per request. NOT per-customer instance. Evidence: Viktor (Slack agent, 40k+
teams: "walled off per workspace, no cross-tenant access, one-click install, NO infra to provision"),
Slack platform, Decagon ("most customers run multi-tenant"), Intercom Fin (one Rails monolith → shared
DBs), Ada/Cresta (per-tenant namespaces), Gumloop (shared static IPs), Zapier (shared worker fleet), Devin
(pooled stateless brain + ephemeral per-session sandbox), Lindy/Dust. AWS: pooled = "essential to the SaaS
model"; instance-per-customer = "a managed service model, differentiated FROM SaaS." Dedicated/silo = a
premium enterprise/compliance carve-out only (Sierra/Devin VPC), never the default. → PER-USER OpenClaw
instances (ClawHost) = personal-hosting artifact, NOT scaled-SaaS. The Claude Agent SDK = multi-tenant but
heavy (1GiB subprocess/session) — only for shell/code-exec agents. Production agent-SaaS (Sierra/Decagon/
Cognition) build a BESPOKE multi-tenant app with the agent loop as their OWN code + LLM API per request;
Anthropic: "the most successful implementations weren't using complex frameworks." A normal app whose
judgment steps are LLM calls over tools ALREADY IS an agent (no gateway needed).

DECISION (Dais's intent + the research): STAY ON apps/life-call (pooled multi-tenant = it already IS the
proven pattern). ★ PHASE B (OpenClaw migration B1-B4) is SUPERSEDED for the PRODUCT ★ — OpenClaw stays as
Dais's PERSONAL instance only. The B1-B3 artifacts (skill scaffold/cron-defs/voice-daemon gate) are kept as
the OSS/local-BYOK path, not the cloud product. Memory = Supabase per-user lm_user_places (pooled-compatible;
native MEMORY.md was for the dropped per-instance model). NEW production-hardening tasks (replace PHASE B):
  HARD-1 ☐ C-H1: atomic unique constraints on [Travel] + lm_ask_log (race; wake already atomic).
  HARD-2 ☐ durable scheduler: move scheduler.js setInterval → ★ Inngest ★ (drops on as a library, no rewrite;
          central cron sweeper + step.sendEvent fan-out + concurrency key=user_id fairness + retries + replay).
          AGENT LOOP = our existing `@openai/agents` dep (already in apps/api) = the agent-ness (LLM+tools+loop,
          right altitude). Memory = mem0ai (already a dep) + Postgres. Full rationale + framework comparison +
          Viktor's real stack = `docs/reference/agentic-saas-architecture.md` (researched 2026-06-24, do NOT
          re-research). (Cloudflare Agents = elegant alt but a Workers-runtime migration; chosen only if we
          move runtime. Bespoke app = NOT laziness — Sierra/Lindy/Viktor all bespoke deliberately.)
  HARD-3 ☐ Stripe lifecycle as source of truth: checkout.completed→provision, past_due→suspend, canceled→
          deprovision; Entitlements; idempotent webhooks; auto-dunning ON.
  HARD-4 ☐ per-tenant isolation review (tokens/secrets per user, one tenant's failure can't break others).
Then LAUNCH (PHASE D) on this hardened pooled app. (Full "MULTI-TENANT (DECIDED…)" note below is now
CONFIRMED, not superseded — shared multi-tenant was right; the OpenClaw-gateway packaging was the wrong part.)

MULTI-TENANT (DECIDED 2026-06-24, Dais "Life Manager is for EVERYBODY, can't pay per-tenant costs"):
SHARED multi-tenant. The cloud app is ALREADY shared multi-tenant — ONE service serves ALL users:
`scheduler.js supaUsers()` = `SELECT * FROM lm_users WHERE phone NOT NULL AND paid AND gcal-connected`, and
tick()/travelTick()/askTickAll() each `for (const u of users)` over EVERY user (scheduler.js:94/151/190).
"my life + mom + friend" = 3 rows in lm_users today. KEEP this: 1000 users = 1 service + 1000 rows (cheap),
NOT 1000 VPS. The OpenClaw port = ONE shared gateway whose 3 cron scripts loop all lm_users rows (exactly as
today) — NOT one OpenClaw instance per tenant. (Per-tenant instance only if/when Anicca self-funds its own
server, later.)

MEMORY (RE-DECIDED 2026-06-24 — "for everybody" REVERSES the native-memory lean): because we run SHARED
multi-tenant (one gateway, many users), OpenClaw NATIVE memory (MEMORY.md is PER-AGENT, not per-user-in-one-
agent) does NOT fit — it can't cleanly isolate per-user facts in a shared gateway. → place aliases + prefs =
a structured SUPABASE per-user table `lm_user_places` (uid, alias, address, ...) + `recall_place`/`save_place`
TOOLS the agent calls (model decides when, no regex). Exact SQL recall, per-uid scoped = native multi-tenant,
cheap, reliable (no vector-index-pause risk). Native MEMORY.md is reserved for the single shared agent's own
operating notes, NOT per-user data. This is the SAME conclusion as the very first memory research — "for
everybody" is the deciding constraint.
- V1 (port) — IN PROGRESS 2026-06-24:
  - B1 ✅ skill scaffold `apps/life-call/skill-life-manager/` (SKILL.md + scripts/{tick,travel,ask}.js = thin
    wrappers requiring scheduler.js one-shot exports tick/travelTick/askTickAll; right-altitude SKILL.md, no
    regex). GREEN 19/19 + regression. Adversary r1 FAIL (test-coverage) → fix → adversary r2 = OVERALL PASS
    (all 5 dims). Railway Node UNTOUCHED (git diff: only package.json + new skill dir). → ready to merge.
  - B2 ✅ DONE 2026-06-24 — cron-COMMAND registration artifacts: crons.json (3 jobs */1 tick/*/30 travel/
    */20 ask) + build-commands.js (tested round-trip generator) + register-crons.sh (idempotent, errexit) +
    27 tests. VCSDD r1/r2/r3: adversary caught a REAL coexistence RACE (FIND-005 — only wake is atomic via
    lm_wake_log unique(uid,event_key); travel/ask dedup is in-memory read-then-write) → SINGLE-WRITER cutover
    is a SAFETY requirement (B4 = SWITCH, disable Railway loops as you enable cron). Verified --command-argv
    in openclaw@latest 2026.6.10 (local 2026.6.1 lacks it). LIVE registration = B4. Merged PR #215.
    NEW follow-up → **C-H1 ☐ harden: give [Travel] + lm_ask_log ATOMIC unique constraints (like lm_wake_log)
    so travel/ask become race-safe too** (migration + future safety). [from B2 adversary FIND-005]
  - B3 ✅ DONE 2026-06-24 — voice-daemon loop gate: server.js runs the 4 scheduler loops only when
    LIFE_RUN_LOOPS!=="false" (default ON = Railway unchanged; =false/0/off → pure /ws Telnyx⇄Gemini-Live
    voice daemon, OpenClaw cron owns the loops = single writer). lib/maybe-start-loops.js pure + 8 tests
    (default-on all-4, off zero, case/space-insensitive, fail-safe-to-ON). VCSDD adversary PASS first round.
    /ws + /test-call + /telegram always-on (outside the gate). Merged PR #217. Run: `LIFE_RUN_LOOPS=false
    node server.js` as a launchd KeepAlive / 2nd Railway service. LIVE /test-call real call = B4.
  - B4 ◑ IN PROGRESS 2026-06-24 — LIVE cutover (the real deployment + the step that CALLS REAL USERS).
    DONE: verified openclaw@latest has command-cron flags (npx); stood up an isolated openclaw@latest gateway
    → reached "ready" (real boot). BLOCKED on the quick local proof: the isolated DEV gateway's auth handshake
    (CLI↔gateway credential matching) is a provisioning/config friction (not a flaw in B1/B2/B3 artifacts).
    NOT YET: live cron-actually-fires-the-LM-script + a real wake call — that needs a PROVISIONED product
    gateway (OpenClaw setup completed → auth/pairing, the apps/life-call code deployed onto the gateway host,
    env keys GEMINI/MAPS/COMPOSIO/SUPABASE, Telnyx pointed at the daemon /ws). And it CALLS REAL phones, so it
    is a DELIBERATE production event: do a CONTROLLED test-user E2E first (a test lm_users row → my own phone,
    known event) → verify [Travel] block + real call → THEN single-writer SWITCH for all users (LIFE_RUN_LOOPS=
    false on the daemon + enable the 3 cron jobs ⇄ disable the Railway start* loops).
    PRODUCTION RUNBOOK (B4): ① get apps/life-call onto the gateway host (image COPY or volume + git) + node;
    ② openclaw setup (provider/auth/pair) on the product gateway; ③ set env keys; ④ run register-crons.sh
    (LIFE_CALL_DIR=…); ⑤ `openclaw cron list` shows lm-wake/travel/ask; ⑥ start voice daemon
    (LIFE_RUN_LOOPS=false node server.js, launchd/2nd service) + point Telnyx /ws at it; ⑦ controlled
    test-user E2E (real [Travel] + real call); ⑧ switch all users (cron on ⇄ Railway loops off) — single writer.
    ★ FIX FROM SEARCH (2026-06-24, docs.openclaw.ai/gateway/{security,configuration}): the dev-gateway auth
    block = a CREDENTIAL MISMATCH, not a flaw. Gateway-connection auth = `gateway.auth.token`
    (env `OPENCLAW_GATEWAY_TOKEN`) or `gateway.auth.password` (env `OPENCLAW_GATEWAY_PASSWORD`); the CLI must
    present the MATCHING `gateway.remote.token`/`gateway.remote.password`. FIX = set ONE env
    `OPENCLAW_GATEWAY_TOKEN=<secret>` on BOTH the gateway process AND the CLI (same process/container) → a
    loopback backend client is a trusted control-plane caller → `openclaw cron create` works. My dev attempt
    mismatched (started --password but config gateway.auth empty; set remote.password but gateway wanted token).
    ★ SIMPLER DEPLOY (CO-LOCATE, not image-bake): run openclaw INSIDE the existing apps/life-call Railway
    service — it ALREADY has the code + env keys (GEMINI/MAPS/COMPOSIO/SUPABASE) + Telnyx wiring. Steps: in
    that container `npm i openclaw`, set `OPENCLAW_GATEWAY_TOKEN`, start the gateway, `register-crons.sh`
    (LIFE_CALL_DIR=this dir), and run `LIFE_RUN_LOOPS=false node server.js` as the voice daemon. ONE service =
    openclaw cron scheduler + node voice daemon, loopback auth, code+keys+Telnyx already present. No separate
    gateway image, no baking apps/life-call into the openclaw template. (OpenClaw LLM provider NOT needed yet —
    cron-COMMAND is deterministic node; voice is Gemini Live's own key. Agent/model = PHASE C+/V4.)
    ★ VERIFIED 2026-06-24 (isolated openclaw@latest gateway): the auth fix WORKS — `OPENCLAW_GATEWAY_TOKEN` +
    `--token <same>` CONNECTS and `openclaw cron list` succeeds. REMAINING gate: cron WRITE (`cron add/create`)
    requires `operator.admin` scope ("command cron is an operator-admin surface" — docs). Via a `--url` remote
    device it triggers device-pairing/scope-approval; the SOLUTION in the co-located production deploy = the
    gateway's own setup/pairing grants the local operator admin (or run the registration as a trusted loopback
    backend client per docs/gateway/security), THEN register-crons runs. So B4's live cron registration is a
    PRODUCTION-gateway step (operator.admin via setup) — and it calls real users → still the deliberate event
    with a controlled test-user E2E first. The code/artifacts (B1/B2/B3) are done + verified; B4 = the deploy/ops.
- V2 ☐ memory (RE-DECIDED 2026-06-24 = SUPABASE per-user, for shared multi-tenant): `lm_user_places` table
  + `recall_place`/`save_place` tools the agent calls (model decides when; no regex). Exact per-uid SQL recall =
  native multi-tenant, cheap, no vector-pause risk. NOT OpenClaw native MEMORY.md (per-agent, can't isolate
  per-user in a shared gateway). See MULTI-TENANT + MEMORY notes above. Built+verified
  ON the OpenClaw setup (see SEQUENCING + MEMORY notes above).
- V3 ☐ omni-channel: LINE / WhatsApp / Discord / iMessage onboarding (OpenClaw native channels) — seamless add.
- V4 ☐ self-improvement: agent tunes WHEN to call + WHAT to say + proactively books good events per user memory.
- V5 ☐ earn loop (later): wallet/x402; eventually self-funds compute (no monthly fee).
- V6 ☐ MERGE with Anicca: drop /life-manager; one repo, one agent.
- V7 ☐ harness-portability (after OpenClaw works): Hermes / Claude Code adapters — incremental.
LEGACY post-launch items folded in: #77 (local converge → now V1 local skills), #29 (STEP2 web dogfood),
#72 (OpenClaw unify → now V1), #70 DROPPED.

## LAUNCH SEQUENCE — explicit order (Dais 2026-06-24), do top→bottom
After PHASE B (OpenClaw cutover) + PHASE C (3 cases incl. memory verified):
- D-1 ☐ END-TO-END TEST on BOTH channels + frictionless entry:
  - web /lm (Google→cal+gmail→phone→pay→dashboard) full E2E, real user, no-mock.
  - Telegram bot full E2E (/start → guided name/cal/gmail/phone/pay → wake call + ask).
  - QR code on aniccaai.com/life-manager (D8): scan → t.me/LifeManagerBotbot?start=src → onboarding. "easy go."
- D-2 ☐ SELL ON CAPAFY (lite Leave-Time Planner) with the BEST setup: clone-winner pricing (3-tier sub),
  emoji-headed detailedDescription, welcomeMsg, examples; CTA → web app for the full autonomous product.
- D-3 ☐ CONTENT CRONS (TikTok + YouTube): from real call recordings → reel → post. ★ idempotent ledger: if a
  given clip/day has NO post-log row → post; if it HAS one → SKIP (no redundant re-posting). ★ Add YouTube
  alongside TikTok. Verify posted.jsonl reaches PUBLISHED (Postiz state), not just a post_id.
- D-4 ☐ PRODUCT HUNT launch SCHEDULE (Tue/Wed/Thu 12:01 AM PST) — draft launch-ready; needs Dais go + date.
- D-5 ☐ ARTICLES (build-in-public), JP + EN each, on: X (articles), Zenn, Note, Substack, Dev.to. Via
  ai-entity-article-writer + stop-ai-slop; structural_principle (no verbatim hook); publish + verify live URL.
- D-6 ☐ post-launch: directory submissions (AI citations), PH follow-up, churn-prevention.

## PHASE E — SELF-IMPROVEMENT + deeper support (Dais 2026-06-24) — after launch, makes it BETTER over time
- E-1 ☐ self-improve from USER BEHAVIOR: the agent tunes WHEN to call + WHAT to say + buffer per user, learned
  from their responses/history (did they answer? get up? leave on time?). Memory = Supabase per-user.
- E-2 ☐ proactive support: books good-for-you events (dentist, meetups) per liking + memory; other life support.
- E-3 ☐ → merges into V4 (self-improvement) / V6 (Anicca merge) of PHASE 8.

---

## END-STATE ARCHITECTURE + PATH TO 10k MRR (ASCII)
```
                 LIFE MANAGER — end state (ONE repo: Daisuke134/life-manager)
   ┌──────────────────────────────────────────────────────────────────────────────────────┐
   │ planner · travel · ask · notify · call (Telnyx ⇄ Gemini Live, voice=Charon) — SAME logic│
   │ only diff = adapters/transport (gog=local | Composio=cloud) + who holds the keys        │
   └───────────────┬───────────────────────────────────────────────┬────────────────────────┘
        ① OSS / LOCAL  (free, MIT, BYOK)                  ② CLOUD  ($20/mo, managed) = the business
        run on your own OpenClaw, your keys                aniccaai.com/lm: Google → cal+gmail → phone
        GitHub repo = credibility + free tier              → Stripe $20/mo → dashboard. per-user lang,
        audience: developers / tinkerers                   name, behavior. audience: everyone else
                  └──────────── FUNNEL: free → trust → paid ───────────┘

   GROWTH ENGINE  (→ 10k MRR = 500 × $20)
   AWARENESS                      CONSIDERATION                 CONVERT + RETAIN
   • TikTok @anicca.comedy daily  • /life-manager landing       • $20/mo Stripe
     real-call reels (warmup→     (late → early → trust)        • product CHANGES behavior: you're
     viral)                       • Product Hunt listing          early → people trust you → you STAY
   • Product Hunt (anchor)        • OSS GitHub (proof)          • low churn = the real moat
   • X (Dais) + word of mouth     • directory backlinks → DR    • every paid user = a visibly more
   • directory submissions          → AI citations (ChatGPT       reliable person = walking testimonial
   • Telegram bot onboarding        "best ___" → us, 6-27× conv)  → referral (trust is shareable)

   THE MOAT = behavior change. A notification gets swiped; a phone call that makes you EARLY changes how
   people see you. That transformation is STICKY (retention) AND SHAREABLE (organic growth). Product and
   marketing compound — that's the road to 10k MRR.
```

---

## X launch copy (JA, Dais-approved 2026-06-22)
```
寝坊・夜更かし・遅刻・連絡漏れから卒業しよう！自分の生活を完全に管理してくれるLife Managerをリリースしました。
・名前・電話番号・Googleカレンダー・任意で現在位置の連携で簡単スタート。
・あらゆる予定（起床・就寝・仕事・瞑想など）に対して、移動時間を自動登録。
・場所がわからなければ質問してくる→返信すれば自律的に登録完了。
・次の予定の15分前に電話でかけてきて、具体的な行き方をガイド・行動を促してくれる。
・予定に遅れそうな場合は関係者へ、返信先・返信案を承認後に連絡。
アプリ版：aniccaai.com/life-manager
ローカル版: https://github.com/Daisuke134/life-manager
```
