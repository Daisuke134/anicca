## Task 8: Retire legacy browser onboarding authority

**Base:** `dcfd280f4`

**Production files (three):**

- `apps/landing/netlify/functions/lm-onboard.js`
- `apps/landing/app/lm/LmClient.tsx`
- `apps/landing/app/lm/LmBody.tsx`

**Test ownership:**

- `apps/mr-bot/test/onboarding-resume-contract.test.js`
- `apps/mr-bot/test/calendar-connect-signature-contract.test.js` only if an unchanged-preservation assertion is needed
- `apps/mr-bot/lib/billing.test.js` only for the Stripe-only paid-writer contract

### Acceptance

1. Every known legacy `lm-onboard` action (`google-start`, `google-callback`, `exchange`, `save`, `telegram-link`) returns JSON `410 Gone` before reading credentials, parsing authority payloads, calling providers, or writing state. Unknown actions remain non-effectful.
2. `calendar-connect.js` and Railway `/panel/onboarding/calendar/*` remain unchanged; the only user Calendar consent path is the authenticated Railway Mini App.
3. `/lm` always renders one handoff to `https://t.me/LifeManagerBotbot?start=lp`. Query `tg`, `uid`, `sig`, `name`, or payment values never select a different experience or enter a request body/link.
4. Landing production code contains no Supabase Google login import/call, `localStorage`/`sessionStorage` identity, legacy onboarding fetch, raw `tg` binding, uid/signature profile mutation, test-call authority, or client-built Stripe `client_reference_id` URL.
5. Only the existing signed Stripe webhook may write `paid`; retired Netlify endpoints and landing code contain no paid-state writer.
6. Preserve the public localized Mr.bot shell and unrelated landing routes; no new dependency, persistence, or auth mechanism.
7. RED proves 410 plus zero `fetch` for all retired actions and static landing authority removal. GREEN includes onboarding, Calendar signature, panel/auth, and billing focused contracts plus the landing type/build check available in the repository.
8. Commit: `refactor(mr-bot): retire legacy onboarding authority` (do not push).
