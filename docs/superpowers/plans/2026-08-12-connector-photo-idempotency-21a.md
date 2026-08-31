# Connector Telegram photo idempotency 21A plan

**Goal:** Close the first restart-safety gap by making evidence-photo delivery provider-idempotent across an OS process loss.

**Architecture:** Reuse OpenClaw Gateway `send`, whose local installed schema accepts `mediaUrl`, `forceDocument`, and required `idempotencyKey`. Keep the existing private 0700 temporary directory and 0600 PNG, but replace the non-idempotent `message send` child process with the same bounded Gateway transport already used for Connector text reports. This slice changes only the transport contract; the evidence chain will supply its stable photo key in 21B.

**Ponytail scope:** exact 2 files, no new service, queue, database, receipt format, or retry loop.

- `apps/mr-bot/lib/outbound-guardian.js`: require a numeric Telegram target and safe idempotency key, call `openclaw gateway call send` with the private local media path, caption, `forceDocument: true`, and the caller key; hide stderr/private values on failure.
- `apps/mr-bot/lib/outbound-guardian.test.js`: RED/GREEN for exact Gateway params, stable-key replay contract, validation-before-spawn, positive message ID, private-file mode/removal, and sanitized failures.

**Estimated production change:** 12–24 LOC. **Estimated test change:** 45–80 LOC.

**Verification:** focused outbound-guardian tests, syntax checks, `git diff --check`, fresh Sol review. No real Telegram send in this slice.

**Deferred to 21B:** bind `connector-evidence-photo:<canonical URL SHA-256>` in `connector-minimal-evidence.js` and prove it in the evidence tests.

**Deferred to 21C:** spawn separate Node OS processes at provider/evidence, Calendar, Telegram message, Telegram photo, and bundle boundaries; resume from durable external ledgers/checkpoints with duplicate effects zero and append-only history unchanged.
