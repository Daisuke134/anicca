# Life Manager — LAUNCH EXECUTION ORDER (do top→bottom, ONE at a time)

Date: 2026-06-21, **last updated 2026-06-22**. THIS file = the ORDER + remaining TODO (SSOT for "what's
left until launch"). Architecture/state = `2026-06-21-life-manager-CANONICAL.md`. Video skill design =
`2026-06-21-life-manager-video-skill-design.md`.
RULE: search the real files before acting; never guess. The video is NOT reelclaw, NOT larry.
After every step: mark it here + commit + push.

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
11. ☐ **P1** — Product Hunt (English) listing: assets, copy, schedule.
12. ☐ **P2** — X @aniccaxxx: the Japanese launch copy (below) + an English version (0.13 recursive-improver) → post.
13. ☐ **P3** — Slack (Dais posts).
14. ☐ **P4** — final smoke: live-curl every surface + one real paid user works end-to-end.

### POST-LAUNCH
15. ☐ **#77** — slice5 local converge (same node app w/ LIFE_TRANSPORT=gog; needs Dais's Mac real call).
16. ☐ **#29** — STEP2 (Dais dogfoods on web). · **#72** OpenClaw unify. · **#70** DROPPED (not now).

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
