# KokuchPro Canonical Candidate Contract Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact new workflow production/test files.

**Goal:** Convert one previously unknown event site's public detail facts into a canonical, strict-free Tokyo offline candidate without browser or external effects.

**Architecture:** Add a pure KokuchPro workflow contract with two exports: canonical URL/binding validation and deterministic detail normalization. Accept only exact HTTPS `www.kokuchpro.com` event URLs with a lowercase 32-hex event key and optional positive occurrence ID. Normalize only a single explicit zero-JPY available ticket, exact free fee scheme, open/not-full registration, Tokyo offline venue, and an event starting inside today's 14-day Tokyo window. Everything else returns no candidate or fails closed on identity/shape corruption. Default browser readers, action/readback, factory/router/native/evidence are deferred.

**Files / soft target:**

- Create `apps/mr-bot/lib/connector-kokuchpro-workflow.js` — about 70–100 LOC.
- Create `apps/mr-bot/lib/connector-kokuchpro-workflow.test.js` — about 90–140 LOC.

## Grounding

- Official filtered listing: <https://www.kokuchpro.com/s/area-%E6%9D%B1%E4%BA%AC%E9%83%BD/charge-0/?et=0&start_date=2026-08-12&end_date=2026-08-26&enabled=1&sort=date> — title states `【無料】2026年8月12日 〜 2026年8月26日の東京都` and lists public event URLs plus `募集中`.
- Official detail: <https://www.kokuchpro.com/event/89a92aac6c9a221ec337481b51c1bbef/> — independently exposes 2026-08-20 19:00–20:30, Tokyo venue/address, `料金制度 無料イベント`, one `無料` ticket, `募集中`, and `申込む`.
- Official paid counterexample: <https://www.kokuchpro.com/event/97accb85cbf2870c2f3b989b3d4e0e94/3847918/> — exposes `料金制度 有料イベント` and `￥1,000` while other body text can contain “無料”; body keyword alone is rejected.
- Existing TECH PLAY/Peatix workflow contracts provide the local pattern for canonical binding, Tokyo time window, strict ticket state, and identity mismatch fail-closed. No new dependency/framework is needed.

### Task 1: Add canonical binding and strict candidate normalization

**Files:**

- Create: `apps/mr-bot/lib/connector-kokuchpro-workflow.js`
- Create: `apps/mr-bot/lib/connector-kokuchpro-workflow.test.js`

- [x] **Step 1: Write RED pure contract tests**

  Cover root and occurrence URLs, exact derived refs, one valid public detail, and fail-closed variants for protocol/host/auth/port/query/hash/path/case, identity drift, paid or ambiguous ticket, online/non-Tokyo, closed/full, malformed times, and outside-window dates.

- [x] **Step 2: Run RED**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-kokuchpro-workflow.test.js
  ```

  Expected: module-not-found or missing-export failure only.

- [x] **Step 3: Implement the smallest pure GREEN contract**

  Reuse `zonedSlotInstant` for the Asia/Tokyo 14-day boundary. Keep the accepted detail schema explicit and private-free. Freeze returned binding/candidate.

- [x] **Step 4: Run GREEN and adjacent checks**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-kokuchpro-workflow.test.js lib/connector-techplay-workflow.test.js lib/connector-peatix-workflow.test.js
  node --check lib/connector-kokuchpro-workflow.js
  git diff --check
  ```

- [x] **Step 5: Report without committing**

  Write RED/GREEN counts, exact schema and failure boundaries, diff LOC, and concerns to the SDD report. Sol reviews, commits, and pushes.

## Acceptance checklist

- [x] Canonical root and occurrence identity are exact, stable, and private-free.
- [x] A candidate exists only for exact free/zero-JPY/single-ticket/open/not-full/Tokyo/offline/14-day facts.
- [x] Body/title `無料` text cannot override paid or ambiguous structured facts.
- [x] Identity corruption throws; ordinary ineligibility returns no candidate.
- [x] No network, browser, action, readback, profile, Calendar, evidence, factory/router/native/launchd behavior.

## Result

Luna implemented the pure two-file contract at 107 production LOC. Initial focused tests were 7/7. Fresh Sol found URL/identity alias conflicts, a Tokyo substring false positive, and semantic ISO date rollover; round 1 added exact fail-closed guards and regressions. Final KokuchPro+TECH PLAY tests are 26/26, syntax/diff checks pass, and fresh Sol re-review reports no Critical/Important findings. Code commits: `beb3baa1b`, `dc633d1a0`.
