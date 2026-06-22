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
1. ☐ **L1 (#78)** — `lm_users.call_language` column ('en'/'ja', nullable; NULL → `langForPhone` fallback).
2. ☐ **L2 (#79)** — `/lm` language toggle button (English / 日本語) persists `call_language`. (gpt-tasteskill UI +
   verify rendered in a real browser.)
3. ☐ **L3 (#80)** — scheduler.js tick() + server.js `/test-call` read `call_language` and OVERRIDE the phone
   default when threading lang through the signed bridge URL.
4. ☐ **L4 (#81)** — `buildCallPrompt` addresses the user BY NAME in the chosen language.
5. ☐ **L5 (#82)** — set Dais `call_language='en'`; fire a real call; VERIFY via recording transcript: 100%
   English, addresses "Daisuke", reads next event, never "Anicca".

### PHASE 2 — Finish #61-b NEW-user web E2E
6. ☐ **E1** — A3 continue (daisukenarita53): enter phone → Stripe **SANDBOX** pay (charges nobody) → reach dashboard.
7. ☐ **E2** — trigger a wake call to the test user; VERIFY (recording) correct language + by name + reads next event.
8. ☐ **E3** — fix the "接続中…" reload cosmetic (cal/gmail localStorage stuck in 'connecting' with no poll resume).

### PHASE 3 — Content pipeline (#45/#50) — English transcripts, WARM-UP MODE
9. ⟳ **C1** — life-manager-video skill: capture the day's REAL wake-call (Telnyx recording) → **English** transcribe
   → captioned reel (jimaku, moving call-UI bg, transparent audio, TikTok export). **Post as a DRAFT into the
   TikTok app for warm-up — NOT Postiz `state=PUBLISHED`.** Verify the draft actually lands in the TikTok app.
   (Skill already BUILT + first reel self-verified + emailed to Dais; what changes here = draft-to-TikTok-app, not
   auto-publish.) After warm-up: switch to 2×/day auto-post + verify real POST_ID per post.

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
