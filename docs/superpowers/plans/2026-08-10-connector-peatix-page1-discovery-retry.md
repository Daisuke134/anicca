# Connector Peatix Page-1 Discovery Retry Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Edit only the two owned Peatix workflow files. This is a read-only discovery repair; do not touch Submit, identity, evidence, reporting, browser ownership, or scheduling.

**Goal:** Recover one measured transient Peatix page-1 search navigation/read failure on the same supplied owned page so the official Connector can reach already-proven eligible candidates.

**Architecture:** Extract the existing single search-page transaction without changing its URL, response predicate, JSON contract, or ordering. For page 1 only, retry that exact transaction once on `PEATIX_SEARCH_NAVIGATION_FAILED` or `PEATIX_SEARCH_READ_FAILED`. Schema/identity/row contract failures remain immediate fail-closed. The retry uses the same page and produces no external write.

**Tech Stack:** Node.js CommonJS, `node:test`, Playwright-compatible supplied page API.

## Ponytail gate and measured contract

- **Reuse:** existing official search URL, waiter-before-navigation ordering, exact `/search/events?p=1&size=20` predicate, JSON reader, same owned page, five-page cap, global order/dedup, and safe stage codes.
- **Measured official failure:** three official wakes reached Peatix discovery but produced no Peatix audit/action; the final discovery action durations were 30,827ms, 13,201ms, and 13,591ms. Dashboard/event/ticket readback remained 0.
- **Measured recovery evidence:** a dedicated same-page Connpass→Peatix transition returned UI HTTP200 and exact JSON page 1 / 20 rows in 4,298ms, proving the source/parser contract remains valid and the official failures are transient page-1 navigation/read boundaries.
- **Do not build:** generic retry framework, retry for detail pages/providers/page 2–5, delay/backoff, new page/session/target, browser restart, cache, Submit, form logic, report transport, schedule, or timeout expansion.
- **Plan size:** two files; target production delta under 35 LOC and test delta under 45 LOC.

## Global constraints

- Retry at most once and only page 1.
- Retry only safe navigation/read failures. `PEATIX_SEARCH_ROWS_CONTRACT_FAILED` and every detail/candidate/Calendar failure remain zero-retry.
- Recreate the waiter before each navigation attempt; never reuse a rejected promise.
- Preserve exact same page object, search URL, response predicate, row order, deduplication, five-page/100-result cap, and stage code after final failure.
- Record no URL query values, rows, titles, identity, raw response, or exception.
- No external write, browser creation/close, target creation, or schedule mutation.

---

### Task 1: Add one bounded same-page page-1 retry

**Files:**
- Modify: `apps/mr-bot/lib/connector-peatix-workflow.test.js`
- Modify: `apps/mr-bot/lib/connector-peatix-workflow.js`

- [x] **Step 1: Add focused failing recovery tests**

Make page 1 fail once with `waitForResponse` rejection, then return one valid short JSON page on the second exact same-page attempt. Repeat for one navigation rejection. Assert two waiters/two navigations, the same page, one returned binding/audit, and no other effect.

- [x] **Step 2: Add zero-extra-retry regressions**

Assert a second page-1 navigation/read failure surfaces the same safe code after exactly two attempts. Assert row-contract failure is attempted once. Assert page 2 failure remains attempted once and preserves all earlier ordering only internally, without returning partial candidates.

- [x] **Step 3: Run focused RED**

```bash
node --test apps/mr-bot/lib/connector-peatix-workflow.test.js
```

Expected: recovery tests fail because production attempts page 1 only once.

- [x] **Step 4: Implement the minimum transaction helper and retry gate**

Move only the current waiter→goto→response→rows transaction into a private helper. Wrap page 1 with a two-attempt loop for the two measured safe codes. Keep all row accumulation outside the retry transaction so a failed attempt cannot duplicate candidates.

- [x] **Step 5: Run focused and required integration GREEN**

```bash
node --test apps/mr-bot/lib/connector-peatix-workflow.test.js \
  apps/mr-bot/lib/connector-minimal-production.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js \
  skills/connector/test/native-entrypoint.test.js \
  skills/connector/test/minimal-production-contract.test.js
node --check apps/mr-bot/lib/connector-peatix-workflow.js
git diff --check
```

Expected: all pass, no network or external write.

- [x] **Step 6: Report exact RED/GREEN evidence to Sol**

Do not commit or push. Sol performs fresh review, commits/pushes the approved two-file implementation, updates the SSOT, then runs one official foreground wake with scheduling still unloaded.
