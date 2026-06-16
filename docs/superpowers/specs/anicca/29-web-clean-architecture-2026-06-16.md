# 29 — Web clean architecture + correct flows (Dais 2026-06-16, after browser E2E found real bugs)

Trigger: Dais drove the live site and found bugs curl never caught. **curl ≠ validation; real browser E2E as
a user (2 personas JP+EN, sandbox pay) is the only proof** ([[feedback_browser_e2e_as_real_user_mandatory]]).

## Architecture (fixed)
- **Auth = Supabase** (Google sign-in; provider enabled, client `727660390518-9l71…`).
- **ALL service connections = Composio** (one provider for everything Anicca↔X):
  - Life Manager: connect each user's **Google Calendar + Gmail** (+ **Telegram** via composio toolkit if available — docs.composio.dev/toolkits/telegram).
  - Anicca: connect the user's **Gmail** so Anicca sends each-wake updates + a daily report to the user.
- Frontend taste = **taste-skill**; UI/UX = **ui-ux-pro-max**. Refactor BOTH the SaaS (`apps/landing`) and the OSS (`~/anicca`) with clean code/architecture.

## Three products (separate)
1. **Anicca** (cloud `/install`→`/me`, + OSS local) — the self-funding earner. Cloud card = Anicca ONLY.
2. **Life Manager** (`/lm` cloud, + OSS local) — gcal/gmail/telegram, 15-min calls. A SEPARATE product. NOT bundled in the Anicca cloud card.
3. (Marketing is content, not a product.)

## Correct flows (each MUST be browser-verified end to end)
- **/install** → Cloud card (Anicca only, no Life Manager) **Get Started** → **onboarding** (Supabase Google login) → **/me** → a **pay** button (Stripe **SANDBOX**) shown AFTER /me. NOT straight to Stripe.
- **/me** = **PRIVATE**. Anonymous visitor sees ONLY a Google login wall — NEVER any dashboard/wallet content. Logged-in user sees their own instance + the pay button. (Bug today: /me shows the wallet-connect dashboard openly.)
- **/lm** → Google login → Composio connects gcal + gmail (+ telegram) → connected state shown → user **REACHES the private LM dashboard** (in the same tab; the dashboard must be reachable — bug today: after login the original page is gone and nobody can reach the dashboard).
- **Localization**: EN version = all English, JA version = all Japanese, completely separate. Every surface (install/me/lm/life-manager/onboarding) localized. Guide users to BOTH the web app and the local (OSS) version.

## OSS (~/anicca)
- README is outdated: remove the **~/.hermes / Hermes-pivot** content (the Hermes pivot was withdrawn; it runs **automaton** now per `specs/00-MASTER.md`). Rewrite clean, separate EN + JA, guiding to web + local. Refactor the repo with clean architecture.

## Validation (HARD 0.31 + the new rule)
For EVERY flow: drive a real browser (agent-browser/camofox/qa-use) through the WHOLE journey as a user, as
**two personas (one JP, one EN)**, paying in **Stripe sandbox** (nobody charged). If UX/UI is broken or ugly,
iterate with taste + ui-ux-pro-max until it visibly works. No curl-only "validated".
