# Connector Current-Wake Telegram Priority Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Edit only the two owned minimal-operations files. Preserve append-only reports/deliveries and the existing OpenClaw Telegram transport.

**Goal:** Guarantee that an older pending Telegram report cannot prevent the current wake from obtaining its required positive provider ID, while retaining bounded durable backlog recovery.

**Architecture:** Keep report persistence and delivery receipts unchanged. After persisting the current report, deliver the current wake first when it lacks a receipt. Once the current receipt exists, attempt at most one oldest historical pending report as best-effort. A historical transport failure leaves it pending and never invalidates the current result. A current transport failure remains a hard failure because no positive current ID exists.

**Tech Stack:** Node.js CommonJS, `node:test`, append-only JSONL, existing `notifyOpenClaw` transport.

## Ponytail gate and measured contract

- **Reuse:** existing safe report schema/message, append-only report/delivery files, provider-ID parser, dedupe by wake ID, OpenClaw Telegram sender, and mode-0600 state.
- **Measured failure:** wake `d5ba...` left a durable report without delivery. Later wake `5219...` reached `reportWake`, but the code iterated the older pending report first; its 10-second gateway timeout threw before the current report was attempted. The current wake therefore had no delivery despite its own work being complete.
- **Measured transport health:** an immediate standalone OpenClaw Telegram send succeeded with positive ID `10604`, and a different current wake delivered ID `10607`; the blocker is ordering/backlog coupling, not missing credentials.
- **Do not build:** new queue/outbox, direct Bot API, retry delay/backoff, gateway restart, parallel sends, report deletion/rewrite, new schedule, browser changes, discovery changes, or application evidence changes.
- **Plan size:** two files; target production delta under 35 LOC and test delta under 55 LOC.

## Global constraints

- Persist/validate current report exactly as today before delivery.
- If current delivery is absent, attempt current first exactly once. Failure must throw and leave the report pending.
- After current receipt exists, select at most one oldest undelivered historical report and attempt it once.
- Historical failure is swallowed only after current receipt exists; the report remains pending with no fabricated receipt.
- Historical success appends the normal immutable positive delivery receipt.
- Never resend a wake with an existing receipt. Never delete, edit, reorder, or truncate JSONL history.
- Return only the current wake's real positive provider ID.
- Messages/state remain privacy-safe and contain no target/token/private event data.

---

### Task 1: Prioritize current wake and bound backlog recovery

**Files:**
- Modify: `apps/mr-bot/lib/connector-minimal-operations.test.js`
- Modify: `apps/mr-bot/lib/connector-minimal-operations.js`

- [x] **Step 1: Add a focused failing current-first test**

Seed one older pending report. On the later wake, make the sender succeed for the current report and fail for the old one. Assert send order is current then old, result carries the current positive ID, current delivery exists, old delivery does not, and the old report remains unchanged.

- [x] **Step 2: Add bounded recovery and hard-current-failure regressions**

Seed two historical pending reports and assert only one is attempted after current success. A later call/wake can recover the next. Assert current send failure still rejects and appends no current delivery. Assert duplicate current `reportWake` never resends current and may attempt at most one backlog item.

- [x] **Step 3: Run focused RED**

```bash
node --test apps/mr-bot/lib/connector-minimal-operations.test.js
```

Expected: current-first/bounded assertions fail because production iterates all pending reports oldest-first and propagates historical failure.

- [x] **Step 4: Implement the minimum delivery helper and ordering**

Create a private helper that sends one validated report and appends its delivery receipt. Use it for current first, then one historical pending report inside a best-effort catch. Keep the existing receipt map and current return contract.

- [x] **Step 5: Run focused and required integration GREEN**

```bash
node --test apps/mr-bot/lib/connector-minimal-operations.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js \
  apps/mr-bot/lib/connector-minimal-production.test.js \
  skills/connector/test/native-entrypoint.test.js \
  skills/connector/test/minimal-production-contract.test.js
node --check apps/mr-bot/lib/connector-minimal-operations.js
git diff --check
```

Expected: all pass, no network or external write.

- [x] **Step 6: Report exact RED/GREEN evidence to Sol**

Do not commit or push. Sol performs fresh review, commits/pushes the approved two-file implementation, updates the SSOT, then runs one official foreground wake with scheduling still unloaded.
