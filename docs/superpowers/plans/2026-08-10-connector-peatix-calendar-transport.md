# Peatix Calendar transport plan

## Goal

Allow the already-supported Peatix canonical event identity through the existing Google Calendar evidence adapter, without weakening URL validation or changing the Luma path.

## Measured boundary

- Official schedule-unloaded wake `wake-b9c68c36c0ff24c5a9117b52` on pushed commit `083b7a2cb` reached Peatix discovery, navigation, and parent `registered` readback with zero submit action.
- The repaired renderer persisted a valid Peatix provider receipt and PNG artifact for `peatix-event://event/5075819`.
- No Calendar event, Telegram delivery, or applied bundle was created; the wake exited 2.
- Code inspection identifies the exact next boundary: `calendar-gog.js` accepts only Luma hosts in `connectorCanonicalUrl()` and hard-codes `--source-title=Luma`, so an exact Peatix canonical event URL is rejected before the Google Calendar create call.

## Ponytail full gate

- Reuse `canonicalEventUrl`, the existing gog adapter, private idempotency property, Calendar receipt validation, and evidence-chain retry behavior.
- Add no provider registry, abstraction, service, state schema, retry, or migration.
- Extend only the Calendar adapter's allowlist with the already-supported exact Peatix public identity: HTTPS, no credentials/port/query/hash, host `peatix.com`, path `/event/<positive integer>`.
- Preserve current Luma acceptance and every existing malformed URL rejection.
- Derive the public Calendar source title from the validated provider identity (`Luma` or `Peatix`); never copy arbitrary input into the title.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/transport/transport-gog.test.js`
2. `apps/mr-bot/lib/transport/calendar-gog.js`

Soft target: 2 files; production +8–18 LOC; tests +20–35 LOC.

### RED

1. Exact `https://peatix.com/event/5075819` creates through the existing adapter, retains the SHA-256 private idempotency property, and passes exact `--source-url` plus `--source-title=Peatix`.
2. Peatix variants with `www`, subdomain, port, trailing slash, query, hash, credentials, non-numeric/zero ID, or ticket/sales/search path fail before `run`.
3. Existing Luma create still uses `--source-title=Luma`; existing malformed URL tests remain green.

### GREEN

- Return a validated `{ url, sourceTitle }` pair from the Connector-only canonical URL gate.
- Accept existing Luma hosts exactly as today and strict Peatix identity only.
- Use the validated pair for description, source URL, and source title; keep all other gog argv and receipt checks unchanged.

## Verify

- Focused transport tests, minimal evidence/production/runner, Peatix workflow/provider/Harness, native entrypoint, changed-file syntax, and `git diff --check`.
- Fresh Sol review for URL canonicalization, argv injection, Luma non-regression, arbitrary source-title leakage, and duplicate Calendar creation.
- SSOT update, commit, push, clean preflight, then one official schedule-unloaded wake. Acceptance remains pre-submit registered, Peatix clicks 0, Calendar create/readback 1, Telegram message/photo positive IDs, durable applied bundle, exact cleanup.

## Result

- Luna measured RED at 18/19: exact Peatix create failed with `Connector calendar invalid`; all twelve malformed variants already failed before `run`.
- GREEN changes only `calendar-gog.js` and its test. The Connector-only gate returns a validated URL and fixed source title, accepts only raw-exact `https://peatix.com/event/<positive integer>` for Peatix, preserves existing Luma behavior, and keeps every other gog argument and receipt check unchanged.
- Luna focused transport was 19/19 and all named adjacent groups passed; Sol independently ran the expanded transport/evidence/minimal/Peatix/Harness/native-entrypoint set at 135/135. Changed-file syntax and `git diff --check` passed.
- Fresh Sol review found no Critical or Important issue and returned `ship`. No browser, provider, Calendar, evidence, Telegram, state, profile, launchd, or schedule side effect occurred during implementation and test.
- Live acceptance remains the next step after push: official schedule-unloaded wake, registered pre-readback, Peatix clicks zero, Calendar create/readback one, positive Telegram message/photo IDs, durable applied bundle, and exact cleanup.
