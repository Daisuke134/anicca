# Connector evidence recovery Item 12A plan

## Goal

Persist and validate one provider ticket/PNG pointer so a recreated evidence chain resumes after interruption without another screenshot or provider-evidence write, while the existing Calendar idempotency path independently reads or creates exactly one event.

## Current evidence

- Item 10B and Item 11 are accepted by official Peatix bundle `applied-bundle:cb4be9afc9d0d55212c84908b7483dfd964ea6b5eefaff7a20c89b180e9759b0`.
- The live recovery sequence already proved provider Submit zero and Calendar event one, but it repeated receipt rendering/evidence writes and Telegram delivery because no evidence-stage checkpoint existed.
- Existing provider evidence stores already expose `record`, `readExternalReceipt`, and `readArtifact`; Calendar already uses one private SHA-256 idempotency property and independent readback. These are the reusable recovery authorities.
- Existing runner regression already proves a parent `registered` pre-readback invokes cache/direct/Harness Submit zero. This slice changes no runner or provider code.

## Ponytail full gate

- Reuse the current evidence store readers, Calendar idempotency/readback, mode-0600 state root, receipt validators, and atomic rename pattern.
- Add no database, service, queue, retry loop, provider abstraction, browser action, runner dependency, or schedule.
- Do not add a Calendar checkpoint. The existing private idempotency find/create/independent-readback path is the Calendar recovery authority; duplicating it would permit stale Calendar state.
- This is Item 12A only: provider ticket/PNG pointer plus existing Calendar recovery. Telegram message/photo and final bundle checkpointing are the next 12B slice and are not claimed here.
- Store only provider/event refs, canonical URL hash, artifact/receipt refs and SHA, provider status, and first-observed timestamp. Never persist Calendar data, title, venue, attendee, Telegram target, raw page, screenshot bytes, or private profile in the pointer.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-minimal-evidence.test.js`
2. `apps/mr-bot/lib/connector-minimal-evidence.js`

Soft target: 2 files; production +65–110 LOC; tests +65–95 LOC. Broad flow rewrite is forbidden; preserve the current evidence/Calendar/Telegram/bundle sequence and add only the pointer branch.

Final size: 2 files; production +109/-59 LOC and tests +128/-2 LOC. Production remains inside the soft target. Tests exceed it because the required fail-closed recovery matrix now fixes fourteen independent corruption/identity/symlink cases without weakening any case; no production scope or additional abstraction was added.

### RED

1. After a valid provider receipt/PNG is stored and Calendar fails, recreating the chain from the same state validates `readExternalReceipt` and `readArtifact`, then skips receipt render, screenshot, and `record` while completing through Calendar/Telegram/bundle.
2. If Calendar create succeeds but its first independent readback is unavailable or representation-mismatched, recovery uses the provider pointer, finds the one existing private-idempotency event, and never creates a second event.
3. Every recovery, including after prior Calendar success, independently reads Calendar and requires one matching event before Telegram/bundle; deletion or ID mismatch fails and never trusts local pointer state as Calendar authority.
4. The provider pointer is mode 0600, atomic, exact-schema, and contains no title, venue, attendee, target, ticket ID, URL, screenshot bytes, Calendar receipt, or private value.
5. Corrupt JSON, extra keys, wrong provider/event/hash, invalid receipt/artifact ref, artifact SHA mismatch, missing provider receipt, or invalid PNG fails before page render, Calendar, Telegram, or bundle.
6. Existing first-pass Luma and Peatix flows remain unchanged and all existing partial failures still write no bundle.
7. A checkpoint file symlink or any symlinked checkpoint path component fails before reading outside the state root or performing any page/Calendar/Telegram/bundle effect.
8. The initial provider `record` result must satisfy the same deterministic provider ID identity as recovery: SHA-256 of tenant, event reference, observed timestamp, and artifact SHA. A syntactically valid forged receipt fails before pointer/Calendar/Telegram/bundle.

### GREEN

- Derive a checkpoint identity from provider, exact event reference, and validated canonical event URL; store the URL only as its SHA-256 idempotency value.
- After provider evidence succeeds, atomically persist one exact provider pointer with stable first-observed timestamp and validated refs/SHA.
- Before the first pointer write, recompute and require the provider receipt ID from tenant, exact event ref, observed timestamp, and raw-byte artifact SHA; use the same validator on first-pass and recovery paths.
- On restart, validate the pointer, provider receipt, artifact bytes/signature/SHA, and identity before skipping page receipt render/screenshot/store.
- Resolve the checkpoint root and file with `lstat`-based component checks; reject symlinks at the checkpoint directory or file before any read/write or downstream effect.
- Always run the existing Calendar find/create/independent-readback sequence. If Calendar already exists after a crash, reuse the one provider event; create remains zero on recovery. No Calendar data is persisted in the pointer.
- Keep Telegram and final bundle behavior otherwise unchanged in this slice.

## Verify

- Focused evidence suite, minimal runner pre-registered no-submit regression, minimal production, Peatix workflow/provider/Harness, native entrypoint, changed-file syntax, `git diff --check`.
- Fresh Sol review for checkpoint corruption, privacy, identity binding, artifact validation, Calendar duplication, crash ordering, Luma non-regression, and absence of provider Submit paths.
- The corruption matrix must cover invalid JSON/extra keys, file and parent symlinks, wrong provider/event/URL hash, forged receipt identity, missing receipt, artifact ref/SHA/bytes mismatch, and invalid PNG, all with zero downstream effects.
- Update SSOT, commit, and push. Item 12 remains open until 12B adds Telegram/photo/final-bundle recovery and the full four-boundary fixture matrix passes.

## Result

- Luna reproduced the initial forged-receipt failure, then made the first-pass and recovery paths require the same deterministic provider receipt identity. Checkpoint file and root-relative path components are rejected with `lstat` when symlinked.
- The recovery matrix covers invalid JSON, extra keys, wrong provider/event/URL hash, forged and malformed receipt refs, malformed and mismatched artifact refs, missing receipt, artifact byte/SHA mismatch, internally consistent non-PNG bytes, and file/parent symlinks. Every case keeps page, Calendar, Telegram, and bundle effects at zero.
- Provider evidence recovery validates the stored receipt and raw artifact bytes, then skips receipt rendering, screenshot, and provider `record`. Calendar remains an independent live find/create/readback authority; a create/readback crash recovers with total Calendar create one.
- Luna focused/adjacent suites passed. Sol independently reran the frozen relevant suite at 43/43, changed-file syntax, and `git diff --check`. The unchanged Peatix date fixture remains 19/20 and native provider-order baseline remains 15/17; neither failing file is changed by this slice.
- Fresh Sol review found the initial three Important issues, then one missing recovery-matrix case group. After Luna fixed or characterized all findings, final re-review returned `ship`.
- Item 12A is complete. Item 12 remains open for 12B Telegram message/photo/final-bundle recovery and the complete four-boundary acceptance matrix. Production schedule remains unloaded.
