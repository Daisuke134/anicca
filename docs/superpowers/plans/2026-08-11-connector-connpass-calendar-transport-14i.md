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
- Extend only the Connector Calendar URL allowlist with the existing Connpass public identity: HTTPS, no credentials/port/query/hash, host `connpass.com` or one valid DNS-label subdomain, exact path `/event/<positive integer>/`. The optional label is 1–63 characters, starts and ends with ASCII alphanumeric, and permits hyphens only between them.
- Preserve current Luma and Peatix acceptance and all malformed URL rejection.
- Use fixed source title `Connpass`; never copy provider or event input into the source title.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/transport/transport-gog.test.js`
2. `apps/mr-bot/lib/transport/calendar-gog.js`

Soft target: 2 files; production +8–18 LOC; tests +25–45 LOC.

### RED

1. Exact root and one-subdomain identities such as `https://connpass.com/event/400028/` and `https://tokyo-builders.connpass.com/event/400028/` create through the existing adapter, retain the private idempotency property, and pass exact `--source-url` plus `--source-title=Connpass`.
2. Connpass variants with multi-level/invalid host, leading-hyphen label, trailing-hyphen label, 64-character label, port, missing/trailing-extra slash, query, hash, credentials, uppercase path, non-numeric/zero ID, join/complete/search path fail before `run`.
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

- Initial Luna RED was 20/21: only exact Connpass success failed, while malformed variants stayed before `run`. Initial GREEN used the shared canonical helper plus raw equality and passed focused 21/21 and all named adjacent groups.
- Fresh Sol review returned `fix-first`, Critical 0 / Important 1. Adversarial probes showed `-bad.connpass.com`, `bad-.connpass.com`, and a 64-character label reached `gog`, contradicting the valid-subdomain boundary. The plan now requires one RFC-style ASCII DNS label: 1–63 characters, alphanumeric at both ends, internal hyphens only. The same Luna must add those three failing cases before the minimal regex correction.
- Fix RED was focused 20/21 with all three invalid hosts reaching `run` (`actual 3`, expected 0). Final GREEN constrains the optional label to 1–63 ASCII characters, alphanumeric at both ends, with internal hyphens only.
- Luna verification: transport 21/21; minimal evidence/production/runner 61/61; Connpass workflow/provider 20/20; Harness 58/58; native entrypoint 8/8; canonical helper 4/4; changed-file syntax and `git diff --check` PASS. Production is +7 LOC and tests +45 LOC in the planned two files. No external side effect occurred.
- Fresh Sol re-review returned `ship`, Critical 0 / Important 0. Independent focused/canonical 25/25, idempotency/evidence 33/33, and adversarial boundary 10/10 passed. Luma, Peatix, fixed source title, raw/canonical equality, private idempotency, and duplicate-Calendar prevention remain intact. The two native-runtime cursor failures are the unchanged clean-HEAD baseline.
- Code capability is complete. Live acceptance remains pending: one official schedule-unloaded recovery wake must produce the Connpass Calendar readback, positive Telegram message/photo IDs, durable applied bundle, same-run provider handoff, and exact cleanup.
- Live acceptance passed on pushed commit `5d6ca0489`. Official schedule-unloaded wake `wake-bc2b2f00e4eb1aeb237e6743` reused the existing Connpass provider receipt and PNG checkpoint with zero submit actions, created and independently read back one Calendar event, delivered Telegram message `11307` and photo `11308`, stored a new durable Connpass applied bundle, and delivered the every-wake report as Telegram `11309`.
- Bundle count advanced 4→5. The bundle is mode 0600, provider `connpass`, event ref `connpass-event://event/400028`, status `registered`, and retains the exact provider receipt and artifact SHA-256. The artifact hash recomputed exactly and its file is mode 0600. External read-only `gog` verification found the recorded Calendar ID exactly once, `confirmed`, with a provider link, interval, and 64-character private idempotency marker.
- The same wake audit records Luma `32/32/17/10/0`, then Connpass `6/6/6/4/1`; action delta was six observe/navigate/readback rows and zero cache/direct/Harness submit. Exit was 0, process and lock were absent, evidence target leases were zero, all four schedules stayed unloaded, and Git remained clean/upstream. Item 14 acceptance is complete.
