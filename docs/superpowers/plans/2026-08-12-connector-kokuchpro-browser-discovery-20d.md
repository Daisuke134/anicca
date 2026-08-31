# Connector KokuchPro browser discovery 20D implementation plan

> **Execution:** Ponytail `full` has removed registration, auth, factory/router/native wiring, evidence, and pagination beyond the first official result page from this slice. Implement only with Superpowers TDD. Sol owns the plan, verification, SSOT, commit, and push; Luna owns production/test edits; a fresh Sol reviews the bounded diff.

**Goal:** Turn the Item 20C pure KokuchPro contract into a bounded same-owned-page discovery workflow that reads the official Tokyo/free/active/14-day listing, validates each official detail independently, and returns only Calendar-free candidates.

**Architecture:** Extend the existing KokuchPro workflow with one factory. The default listing reader navigates the already-owned page to the exact official filter URL and accepts the first official result page: exactly 1–40 `.event_list .event_item` cards, at most 20 unique canonical occurrence/root URLs per card and 800 total. This preserves the multiple dated occurrences that the official UI nests in one result card while remaining bounded. The default detail reader navigates that same page to each binding, bounded-flattens every top-level JSON-LD array and `@graph`, requires exactly one schema.org Event, then reads the explicit fee/ticket table and emits only public structured fields. The workflow records `within_window_count` after valid identity/time/window parsing but before free/Tokyo/offline/open/ticket eligibility, then Calendar-gates only eligible candidates. It never creates a page/session/target, fills a field, submits, authenticates, or persists state.

**Ponytail size gate:**

- Modify `apps/mr-bot/lib/connector-kokuchpro-workflow.js` — about 80–100 production LOC.
- Modify `apps/mr-bot/lib/connector-kokuchpro-workflow.test.js` — about 110–150 focused test LOC.
- Exact two files; no new module, abstraction, dependency, credential path, native wiring, or external effect.

**Measured official evidence:**

- Filter page: <https://www.kokuchpro.com/s/area-%E6%9D%B1%E4%BA%AC%E9%83%BD/charge-0/?et=0&start_date=2026-08-12&end_date=2026-08-26&enabled=1&sort=date> — official heading independently states free, Tokyo, and the exact window; the live DOM shows `336件中 1件から40件まで`, exactly 40 result cards and 48 unique canonical occurrence/root URLs because two recurring cards each expose five dated occurrences.
- Filter page 2 with the same query plus `page=2` — live DOM preserves the heading and shows `336件中 41件から80件まで`; pagination is deliberately deferred because one unknown-site proof only needs a bounded first page.
- Detail: <https://www.kokuchpro.com/event/89a92aac6c9a221ec337481b51c1bbef/> — one schema.org Event exposes exact URL, `OfflineEventAttendanceMode`, Tokyo Place/address, zero-JPY InStock Offer, and zoned start/end; the explicit table independently says `料金制度 無料イベント` and one `無料 / 募集中` ticket.
- Direct `/entry/` navigation redirects to the official login page and says membership is required. This slice performs no login/action; the next slice lets the bounded Harness classify that exact auth boundary.

## Task 1: Add the bounded same-page discovery workflow

**Files:**

- Modify: `apps/mr-bot/lib/connector-kokuchpro-workflow.js`
- Modify: `apps/mr-bot/lib/connector-kokuchpro-workflow.test.js`

**Step 1 — RED**

Add focused tests proving:

1. The default listing reader uses the exact Tokyo/free/offline/open/date-window URL on the supplied page, accepts only exact canonical KokuchPro event links from 1–40 official result cards, deduplicates in card/DOM order, and rejects redirect, over-40 cards, over-20 unique bindings in one card, over-800 total rows, or malformed results.
2. The default detail reader requires the same canonical page identity, exactly one schema.org Event for that URL, offline mode, zero-JPY InStock offer, exact free fee row, and exactly one free/open ticket row. It returns bounded public fields only.
3. The workflow filters malformed/ineligible/out-of-window rows, calls Calendar gating once per eligible candidate, keeps only Calendar-free candidates, and emits frozen audit counts.
4. Listing/detail/Calendar/audit exceptions map to explicit safe stage codes; no action or private value is produced.
5. `runDirectAction` remains a deterministic safe failure requiring Harness; `readProviderState` remains unavailable until the action/readback slice.
6. A within-window paid/ineligible detail increments `within_window_count` but not `eligible_count`; an out-of-window otherwise eligible detail increments neither.
7. JSON-LD Events are counted across top-level objects, top-level arrays, and each bounded `@graph`; a hidden second Event fails closed even when a separate canonical Event is valid.

Run:

```bash
cd apps/mr-bot
node --test lib/connector-kokuchpro-workflow.test.js
```

Record the expected RED failure in the report before production edits.

**Step 2 — GREEN**

Implement the minimum factory/default readers and safe-stage mapping. Reuse the Item 20C canonical/normalization contract and the existing provider Calendar overlap/idempotency pattern. Keep every browser operation on the passed page.

Run:

```bash
cd apps/mr-bot
node --test lib/connector-kokuchpro-workflow.test.js
node --test lib/connector-kokuchpro-workflow.test.js lib/connector-techplay-workflow.test.js
node --check lib/connector-kokuchpro-workflow.js
```

**Step 3 — report, review, verify**

Write the SDD report with RED/GREEN evidence, files, LOC, commands, and known limits. Sol creates a review package from the exact base/head diff and dispatches a fresh Sol reviewer. Critical/Important findings return to the same Luna for RED→GREEN repair. After approval, Sol reruns focused/adjacent tests, updates the Connector SSOT, commits, fetches, pushes, and verifies remote equality.
