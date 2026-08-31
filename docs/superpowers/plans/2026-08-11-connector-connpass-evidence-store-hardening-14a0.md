# Connector Connpass evidence store hardening Item 14A0 plan

## Goal

Make the reused Connpass evidence store self-authenticating before the minimal applied-bundle wiring ships. A receipt read must prove the exact tenant/event/time/artifact tuple that generated its provider ID, and the artifact marker must contain no unverifiable event identity.

## Review evidence

- Fresh Item 14A review found that `readExternalReceipt` returned only `kind/provider_id/observed_at`; event and artifact fields were treated as optional by the evidence validator.
- A stored receipt could therefore change `event_ref` or `artifact_sha256` to another syntactically valid value while keeping the old provider ID, and reuse validation would not detect it.
- The artifact marker redundantly stored an `event_ref` that `readArtifact(tenantId, ref)` could validate only syntactically, not against the caller's expected event.

## Ponytail full gate

- Harden the existing store. Add no new store, schema version, index, database, migration, lock, or abstraction.
- Receipt files keep the existing five exact fields. On read, require exact keys and recompute provider ID from canonical tenant, event ref, exact observed time, and artifact SHA.
- Remove the unverifiable event ref from newly written artifact markers; the marker becomes exact `{sha256}` and is bound to immutable object bytes by the same SHA.
- No production Connpass evidence exists yet, so no legacy marker migration is required. Luma/Peatix stores and minimal evidence wiring are outside this slice.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connpass-evidence-store.test.js`
2. `apps/mr-bot/lib/connpass-evidence-store.js`

Soft target: 2 files; production `+15–30 LOC`; tests `+25–45 LOC`.

### RED

1. After a valid record, rewrite the receipt with a different valid event ref, different valid artifact SHA, stale provider ID, extra/missing key, or invalid exact timestamp. Every read must reject.
2. Rewrite the artifact marker with an extra event identity, wrong SHA, extra/missing key, or replace immutable object bytes. Every read must reject.
3. A valid read returns exact `kind`, `provider_id`, `observed_at`, `event_ref`, and `artifact_sha256`; artifact bytes remain exact.

### GREEN

- Factor one provider-ID calculation used by both record and read.
- Validate exact receipt keys, fields, and recomputed ID before returning all five fields.
- Persist and require exact marker keys `sha256`; verify marker SHA, ref SHA, and object bytes digest are identical.

## Verify

- Focused Connpass store RED/GREEN, all provider-store regression, syntax, and `git diff --check`.
- Fresh Sol review for tuple binding, exact schemas, immutable bytes, path/tenant safety, and no unrelated behavior.
- Update SSOT, commit, and push this prerequisite before restoring the frozen Item 14A minimal-evidence diff.

## Result

- Luna RED reproduced both gaps: a valid receipt read returned only three fields, and a semantic `event_ref` rewrite with the stale provider ID was accepted.
- GREEN keeps the slice to the two owned files. Receipt reads now require the exact five-key schema and recompute the provider ID from tenant, event, observed time, and artifact SHA. Artifact markers require exact `{sha256}` and verify the immutable object bytes against the same digest.
- Focused Connpass tests pass 2/2; serialized Connpass/Luma/Peatix store regression passes 6/6; syntax and `git diff --check` pass.
- Fresh Sol review: `ship` (Critical 0, Important 0). No live Connpass evidence existed, so no migration was required. Item 14A wiring remains a separate frozen slice.
