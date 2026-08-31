# Connector OS-process durable continuation 21C plan

**Goal:** Prove Item21 across real Node OS process boundaries: provider registration, evidence receipt/artifact, Calendar, Telegram message, Telegram photo, and final bundle each survive restart with duplicate external effects zero.

**Architecture:** Run the existing `runMinimalConnectorWake` and `createMinimalEvidenceChain` in short-lived child Node processes. The helper uses one temp state directory plus separate durable fake-provider, object-store, Calendar, and Telegram ledgers. Each adapter writes its external effect before the selected child terminates. The next fresh process re-reads the ledger/checkpoints and resumes the production chain. This is a test harness only; production orchestration and schemas do not change.

**Ponytail scope:** exact 2 new test-only files, production LOC 0.

- `apps/mr-bot/lib/connector-minimal-restart-child.js`: bounded child fixture using one fixed Peatix candidate, real runner/evidence chain, durable 0600 JSON ledgers, and allowlisted crash stages. It never prints candidate/private values.
- `apps/mr-bot/lib/connector-minimal-restart.test.js`: parent sequence that spawns a new `process.execPath` child at each stage and checks exit/status plus durable totals.

Implementation is closed in three additions to the same two test-only files: 21C1 proves provider readback plus evidence checkpoint, 21C2 adds Calendar plus message/photo effects, and 21C3 adds the blocked bundle boundary and final reused rerun. Each addition is independently RED/GREEN/reviewed before the next; the full acceptance below remains unchanged.

### Implementation-ready fixture map

Use one parent-owned temp root. `restart-ledger.json` starts at mode 0600 with `provider_count=1`, all downstream counts 0, Submit/cache/direct/Harness 0, and empty Calendar/message/photo identities. Seed `action-history.jsonl` with one safe line; later processes may only append, so the original bytes must remain an exact prefix.

The child accepts exactly `stateDir` plus one allowlisted stage. It constructs one fixed Peatix candidate and calls the real `createMinimalEvidenceChain` directly. Provider registered pre-readback and Submit/cache/direct/Harness 0 are already proven by the composed runner test; the new OS-process fixture is restricted to the missing external-effect/checkpoint crash windows identified by fresh review.

- evidence store `record`: when absent, atomically stores the receipt/artifact identity and increments once; stage `evidence_effect` exits 42 after that write but before returning. On later processes it returns the existing identity without increment.
- Calendar `findConnectorEvents`: returns the ledger event by the existing idempotency value. `createConnectorEvent` atomically stores/increments once; stage `calendar_effect` exits 43 after write but before return.
- `sendMessage` and `sendPhoto`: ledger-map by the exact caller idempotency key. First call stores one positive ID/count then stage exit 44/45 before return; replay of the same key returns the stored ID without increment.
- page fixture implements only the Peatix path used by production evidence: mutable `url/goto`, `evaluate`, `screenshot` with a valid PNG over 5000 bytes.
- The fixed input passes `providerState={status:"registered"}` from the durable provider ledger; no submit interface exists in this helper.

Parent spawn order is `evidence_effect`, `calendar_effect`, `message_effect`, `photo_effect`; assert exit codes 42–45 and distinct numeric PIDs. Then create/chmod `applied-bundles` to 0500 and spawn `none`, expecting the real chain to reject with all external counts already one; restore 0700. Spawn `none` again for `completion_disposition=created`, then once more for `reused`. Assert one bundle, provider/evidence/Calendar/message/photo/bundle counts each one, message/photo keys distinct, all ledger/checkpoint/bundle files 0600, and stdout JSON contains only PID/disposition.

**Required stages and proof:**

1. `provider_readback`: provider ledger already has one registration; child exits after official registered readback. Next process performs cache/direct/Harness Submit 0.
2. `evidence_checkpoint`: real evidence receipt/artifact checkpoint is durable; next process reads it instead of recording/capturing again.
3. `calendar_effect`: Calendar adapter persists one event, then child exits before returning; next process finds the same idempotency identity and creates 0 duplicates.
4. `telegram_message_effect`: gateway fixture persists the exact message key and ID, then exits before local checkpoint; replay of the same key returns the same ID and increments external send count 0.
5. `telegram_photo_effect`: same proof for the Item21B photo key.
6. `bundle_boundary`: all external checkpoints exist while bundle write is blocked; after restoring only the bundle directory, a new process writes one bundle without replaying any external effect.
7. Final completed rerun reads the exact bundle/Calendar and returns reused disposition; all external totals remain exactly one.

**Safety assertions:** provider registration/evidence/Calendar/message/photo/bundle counts all 1; cache/direct/Harness/final provider mutation all 0; message/photo keys distinct and stable; append-only history seed byte-identical; receipt/checkpoint files remain 0600; bundle exactly one; child output contains no raw URL, title, Telegram target, or private values.

**Estimated test change:** helper 150–230 LOC, parent 90–150 LOC. The larger test-only size is accepted because it replaces six in-memory simulations with actual process isolation and creates no production abstraction.

**Verification:** focused restart test, evidence/runner/guardian focused suites, syntax checks, `git diff --check`, fresh Sol review. No real provider, Calendar, Telegram, browser, or launchd mutation.
