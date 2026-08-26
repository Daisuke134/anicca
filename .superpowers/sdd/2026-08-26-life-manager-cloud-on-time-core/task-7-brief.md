## Task 7: Implement server-owned onboarding state and mobile UI

This task is executed as two reviewed atomic slices. Task 7A must be approved before Task 7B begins.

### Task 7A: Server-owned onboarding state API

**Production files:** Modify `lib/panel-api.js`; add one additive migration under `migrations/`.

**Test files:** Modify `lib/panel-api.test.js`; add a focused migration contract test only if needed.

1. Add failing API tests for the fixed progression: Calendar → home → Telegram notifications → phone → explicit call consent → payment → dashboard. Use the Telegram profile name; only when the stored name is empty, prepend a required `name` step whose bounded non-empty save returns to Calendar.
2. Derive every response from the authenticated Telegram panel session plus server rows. Reject or ignore any body/query `uid`; it is never an authority.
3. Enforce prerequisites on every mutation. An out-of-order action returns a conflict and performs zero writes.
4. `home.save` writes a non-empty bounded home address. `notifications.enable` writes `notifications_enabled=true` and explicitly preserves `call_enabled=false`.
5. `phone.save` writes a normalized bounded phone number and leaves calls off. `phone.skip` advances without a phone. A call step exists only when a phone is present; `call.enable` requires an explicit action and a current phone, while `call.skip` keeps calls off.
6. Payment is optional in onboarding: `payment.skip` may advance to dashboard but never writes `paid`. The API returns the configured, server-owned Stripe Payment Link for the payment step. Only the existing signed Stripe webhook may write `paid=true`.
7. Use existing `lm_users`, `lm_panel_preferences`, panel sessions, and `tg_onboard_stage`; add no new table or framework. Make each state transition tenant-scoped and atomic in SQL so concurrent/out-of-order requests cannot bypass prerequisites.
8. Prove another valid browser session for the same Telegram user sees the same state; prove actor isolation, client→paid prohibition, phone→call prohibition, and concurrent duplicate safety.
9. Run focused API/migration tests plus panel auth and billing tests.
10. Commit: `feat(life-manager): add telegram onboarding state api`.

### Task 7B: Telegram-native mobile onboarding UI

**Production files:** Modify panel UI/auth routing only.

**Test files:** Modify `lib/panel-ui.test.js` and focused panel auth tests.

1. Render the server-returned Task 7A step at `/panel/onboarding`; do not infer progression in the browser.
2. Add contract tests at 375px for exactly one primary action, escaped copy, resumability, optional phone/call/payment skips, and no Google/Supabase login control.
3. Use the existing panel session and CSRF/idempotency contracts for mutations.
4. Calendar connection uses the existing session-scoped calendar-consent endpoint. Dashboard entry uses existing panel rendering.
5. Run focused UI/auth/API tests and a real HTTP flow.
6. Commit: `feat(life-manager): add telegram native onboarding ui`.

### Original combined acceptance checklist

**Files:** Modify `lib/panel-api.js`, `lib/panel-api.test.js`, panel UI assets, `lib/panel-ui.test.js`.

1. Add failing API tests for this fixed progression: Calendar → home → Telegram notifications → phone → explicit call consent → payment → dashboard.
2. Test that server state resumes on another browser session for the same Telegram user, out-of-order writes are rejected, body uid is ignored, phone save leaves calls off, and unverified clients cannot set paid.
3. Add UI contract tests at 375px for one primary action, skippable optional phone/call/payment steps, escaped copy, and no Google/Supabase login control.
4. Implement the minimal state adapters using existing tenant/profile fields and existing panel auth; no new table or framework.
5. Run API/UI tests plus billing/auth tests; mutation-check phone→call and client→paid prohibitions.
6. Commit: `feat(life-manager): add telegram native onboarding state`.
