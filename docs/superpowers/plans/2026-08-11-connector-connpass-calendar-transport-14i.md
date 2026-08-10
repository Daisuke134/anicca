# Connpass Calendar transport 14I plan

## Goal

Allow the already-verified Connpass canonical event identity through the existing Google Calendar evidence adapter, without weakening URL validation or changing Luma and Peatix behavior.

## Measured boundary

- Official schedule-unloaded wake `wake-78fa52609051935647435ecd` recovered the existing Connpass registration with zero Submit action.
- It durably stored provider receipt `provider-receipt://connpass/099d85e8805915cdbbeca81b658bc0b88f5ff2bc8a99965d37fbd9a166db7cd4` and PNG artifact SHA-256 `10f34f8b37d8351a2a0c729e38ee76528b0b308b9a64e6ec06f2bdfe5e8a839e` in evidence checkpoint `63f9…`.
- No Calendar event, Telegram delivery, or applied bundle was created; the wake terminated `evidence_completion_failed`.
- Code inspection identifies the exact next boundary: `calendar-gog.js` accepts only Luma and strict Peatix identities in `connectorCanonicalUrl()`, so a valid Connpass canonical URL is rejected before the Google Calendar create call.

## Ponytail full gate

- Reuse `canonicalEventUrl`, the existing gog adapter, fixed provider source titles, private idempotency property, Calendar receipt validation, and evidence checkpoint recovery.
- Add no provider registry, abstraction, service, state schema, retry, migration, or new renderer.
- Extend only the Connector Calendar URL allowlist with the existing Connpass public identity: HTTPS, no credentials/port/query/hash, host `connpass.com` or one valid subdomain, exact path `/event/<positive integer>/`.
- Preserve current Luma and Peatix acceptance and all malformed URL rejection.
- Use fixed source title `Connpass`; never copy provider or event input into the source title.

## Implementation slice

Luna owns only:

1. `apps/life-manager/lib/transport/transport-gog.test.js`
2. `apps/life-manager/lib/transport/calendar-gog.js`

Soft target: 2 files; production +8–18 LOC; tests +25–45 LOC.

### RED

1. Exact root and one-subdomain identities such as `https://connpass.com/event/400028/` and `https://tokyo-builders.connpass.com/event/400028/` create through the existing adapter, retain the private idempotency property, and pass exact `--source-url` plus `--source-title=Connpass`.
2. Connpass variants with multi-level/invalid host, port, missing/trailing-extra slash, query, hash, credentials, uppercase path, non-numeric/zero ID, join/complete/search path fail before `run`.
3. Existing Luma and Peatix tests remain green with their fixed source titles.

### GREEN

- Return the existing validated `{ url, sourceTitle }` pair for Connpass only when raw input and canonical output exactly match the accepted public identity.
- Accept root or one subdomain exactly as the shared canonical helper already defines.
- Keep description, source URL, private idempotency property, gog argv, Calendar provider receipt, and all other transport behavior unchanged.

## Verify

- Focused transport tests, minimal evidence/production/runner, Connpass workflow/provider/Harness, native entrypoint, changed-file syntax, and `git diff --check`.
- Fresh Sol review for URL canonicalization, subdomain scope, argv injection, Luma/Peatix non-regression, arbitrary source-title leakage, and duplicate Calendar creation.
- SSOT result update, commit, push, clean preflight, then one official schedule-unloaded recovery wake. Acceptance is Connpass Submit 0, evidence checkpoint reuse, Calendar create/readback exactly once, Telegram message/photo positive IDs, durable Connpass applied bundle, same-run Luma→Connpass handoff lineage, and exact cleanup.

## Result

Pending Luna TDD implementation and live acceptance.
