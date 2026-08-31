# Connector Doorkeeper discovery 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Doorkeeperの東京一覧をsame owned pageで読み、無料・受付中・対面・14日窓・Calendar非衝突候補だけを返すprovider workflowと、厳格な親readbackを追加する。

**Architecture:** 既存Meetup workflow interfaceを再利用し、Doorkeeper固有部分だけを新しい1 moduleへ隔離する。一覧カードで日付・東京会場を先に絞り、残ったdetailだけSchema.org Event JSON-LDとvisible `申し込む`で検証する。direct submitは実装せず、後続sliceで既存bounded Browser Harnessへ接続する。

**Tech Stack:** Node.js CommonJS、`node:test`、Playwright互換page interface、既存Calendar busy interval contract。

## Global Constraints

- Connector endpointはexact `http://127.0.0.1:9222`。Gig `:9223`への接続・writeは0。
- 一wake、一browser session、一target、一pageを維持し、workflowはbrowser/session/targetを作成・closeしない。
- 対象窓はAsia/Tokyoの今日00:00を含む14日、end day 00:00 exclusive。
- 対象は無料、受付中、東京対面、Calendar非衝突のみ。価格・受付・identityが曖昧ならfail closed。
- canonical URLはexact `https://<lowercase-ascii-group>.doorkeeper.jp/events/<positive-id>`。query、fragment、credential、port、`www`、wrong pathを拒否する。
- Doorkeeper APIはalphaかつPublic API Access token必須なので追加しない。公開browser DOM/JSON-LDだけを使う。
- credential、cookie、email、氏名、raw form value、private Calendar titleはcode/test/auditへ保存しない。
- auditはexact `discovered_count`, `within_window_count`, `eligible_count`, `calendar_free_count`, `selected_count`だけをcallbackへ渡す。
- direct actionは外部作用0のstable safe failureにする。production router/Harness/native/evidence/Calendar transport/operations/scheduleはこのtaskで変更しない。

## Grounded Contract

- Doorkeeper参加者ヘルプ: accountがなくてもevent pageの`申し込む`からemailで参加でき、無料eventは必要事項入力後の`申し込む`で完了pageへ進む。
  - https://support.doorkeeper.jp/article/65-article
  - 核心: `Doorkeeperのアカウントを持っていなくても、誰でも簡単にイベントに参加することができます`。
- Doorkeeper公式API docs: Event resourceは`id`, `starts_at`, `ends_at`, `address`, `public_url`を持つが、API requestは認証必須でalpha。
  - https://www.doorkeeper.jp/developer/api
  - 核心: `API requests without authentication will also fail.`
- Doorkeeper東京一覧:
  - https://www.doorkeeper.jp/prefectures/tokyo/events
  - 実測: page 1は50 rowsで2026-08-11〜08-19、page 2は50 rowsで08-19〜08-26。14日窓のexact東京会場rowは12。
- 実detail `https://techgym.doorkeeper.jp/events/198719`:
  - JSON-LDは`Event`、OfflineEventAttendanceMode、東京住所、Offer price `0` JPY、InStock、exact canonical URLを持つ。
  - visible exact `申し込む`は1、modalはrequired email 1とsubmit `申し込む`を持つ。
- 2026-08-11のread-only実測は`observed/normalized/window/free-open/calendar-free = 100/100/12/8/0`。無料受付中8件はすべて実Calendar conflictで、外部申込0が正しい。

---

### Task 1: Doorkeeper public discovery and parent readback

**Files:**
- Create: `apps/mr-bot/lib/connector-doorkeeper-workflow.js`
- Create: `apps/mr-bot/lib/connector-doorkeeper-workflow.test.js`

**Interfaces:**
- Produces: `createDoorkeeperScriptFirstWorkflow(options = {})`
- Returned workflow: `discoverCandidates({ page, calendar })`, `runDirectAction({ page, candidate })`, `readProviderState({ page, candidate })`
- Optional injected functions: `now`, `readListingPage`, `readEventDetail`, `readRegistrationView`, `isCalendarFree`, `onDiscoveryAudit`
- `readListingPage(page, pageNumber)` returns `{ rows: [{ canonical_url, day: "YYYY-MM-DD", venue_url }], has_next: boolean }`
- `readEventDetail(page, canonicalUrl)` returns `{ jsonld, body_text, controls: [{ text, visible }] }`
- `readRegistrationView(page, candidate)` returns `{ page_url, canonical_links: [{ href, visible }], controls: [{ text, visible }], body_text }`
- Candidate shape: `{ provider: "doorkeeper", event_ref: "doorkeeper-event://event/<id>", canonical_url, title, starts_at, ends_at, registration_status: "available", ticket_price_status: "free", ticket_price_minor: 0 }`

- [x] **Step 1: Write the failing canonical/listing test**

  Add a test that imports the missing module and drives two listing pages through injected readers. The literal fixtures must prove ordered dedup, exact URL acceptance, page stop after the first page whose maximum day reaches the exclusive window end, and rejection of malformed origins/paths.

  ```js
  const { createDoorkeeperScriptFirstWorkflow } = require("./connector-doorkeeper-workflow.js");
  const NOW = new Date("2026-08-11T03:00:00.000Z");

  function binding(id, group = "tokyo-builders") {
    return {
      event_ref: `doorkeeper-event://event/${id}`,
      canonical_url: `https://${group}.doorkeeper.jp/events/${id}`,
    };
  }

  function detail(id, group = "tokyo-builders") {
    const row = binding(id, group);
    return {
      jsonld: {
        "@type": "Event",
        name: `Tokyo Free Event ${id}`,
        url: row.canonical_url,
        startDate: "2026-08-20T18:00:00+09:00",
        endDate: "2026-08-20T20:00:00+09:00",
        eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
        location: { "@type": "Place", address: "東京都千代田区1-1" },
        offers: [{
          "@type": "Offer",
          availability: "https://schema.org/InStock",
          price: "0",
          priceCurrency: "JPY",
          url: row.canonical_url,
        }],
      },
      body_text: `Tokyo Free Event ${id}`,
      controls: [{ text: "申し込む", visible: true }],
    };
  }

  test("Doorkeeper reads ordered Tokyo listing pages and accepts only exact canonical events", async () => {
    const first = binding("101");
    const second = binding("202", "ascii-group");
    const pages = [];
    const detailReads = [];
    const workflow = createDoorkeeperScriptFirstWorkflow({
      now: () => new Date(NOW),
      async readListingPage(_page, pageNumber) {
        pages.push(pageNumber);
        if (pageNumber === 1) return {
          rows: [
            { canonical_url: first.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
            { canonical_url: first.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
            { canonical_url: "https://www.doorkeeper.jp/events/101", day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
            { canonical_url: "https://tokyo-builders.doorkeeper.jp/events/101?x=1", day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
          ],
          has_next: true,
        };
        assert.equal(pageNumber, 2);
        return {
          rows: [
            { canonical_url: second.canonical_url, day: "2026-08-24", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
            { canonical_url: binding("303").canonical_url, day: "2026-08-25", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
          ],
          has_next: true,
        };
      },
      async readEventDetail(_page, canonicalUrl) {
        detailReads.push(canonicalUrl);
        return canonicalUrl === first.canonical_url ? detail("101") : detail("202", "ascii-group");
      },
    });

    const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
    assert.deepEqual(pages, [1, 2]);
    assert.deepEqual(detailReads, [first.canonical_url, second.canonical_url]);
    assert.deepEqual(result.map(({ event_ref, canonical_url }) => ({ event_ref, canonical_url })), [first, second]);
  });
  ```

- [x] **Step 2: Run RED and verify the expected failure**

  Run:

  ```bash
  cd apps/mr-bot
  node --test lib/connector-doorkeeper-workflow.test.js
  ```

  Expected: FAIL because `connector-doorkeeper-workflow.js` does not exist. A syntax error or unrelated failure does not count as RED.

- [x] **Step 3: Add failing eligibility, audit, Calendar, and readback tests**

  Use hand-authored literal JSON-LD; do not derive expected values with production helpers.

  ```js
  const eligibleJsonLd = {
    "@type": "Event",
    name: "Tokyo Free Event",
    url: "https://tokyo-builders.doorkeeper.jp/events/101",
    startDate: "2026-08-20T18:00:00+09:00",
    endDate: "2026-08-20T20:00:00+09:00",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: { "@type": "Place", address: "東京都千代田区1-1" },
    offers: [{
      "@type": "Offer",
      availability: "https://schema.org/InStock",
      price: "0",
      priceCurrency: "JPY",
      url: "https://tokyo-builders.doorkeeper.jp/events/101",
    }],
  };
  ```

  Required mutation-catching cases:

  1. JSON-LD URL or id mismatch rejects with `DOORKEEPER_DETAIL_IDENTITY_MISMATCH_FAILED`.
  2. online mode, non-Tokyo address, invalid interval, outside 14-day window, paid price, non-JPY, no offer, any non-InStock offer, offer URL mismatch, missing/duplicate/hidden exact `申し込む`, and `中止|延期|受付終了|満席|キャンセル待ち` reject.
  3. multiple offers pass only when every offer is exact URL, InStock, JPY, and numeric zero.
  4. unrelated Calendar overlap blocks; an exact SHA-256 Connector idempotency interval is recoverable only when no other busy interval overlaps.
  5. audit is exactly `100/100/12/8/0` for the measured-shape fixture and keys contain no URL/title/profile/auth data.
  6. parent readback returns `absent` only on the exact canonical event page with one visible `申し込む`.
  7. parent readback returns `registered` only when one exact candidate canonical link and one completion marker (`申し込みが完了しました` or `Your registration is complete`) coexist, with no payment/waitlist/error marker. Wrong event, duplicate marker/link, hidden marker, or ambiguous URL returns `unavailable`.
  8. direct action returns `{ status: "failed", safe_reason: "doorkeeper_direct_requires_harness" }` and invokes no submit dependency.

- [x] **Step 4: Re-run RED and confirm behavior failures**

  Run the same focused command. Expected: tests load after a temporary export shell exists, but fail on missing discovery/readback behavior. Do not add production behavior before observing these failures.

- [x] **Step 5: Implement the minimal workflow**

  Use only stdlib and the existing schedule helper.

  ```js
  "use strict";

  const { createHash } = require("node:crypto");
  const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

  const TIME_ZONE = "Asia/Tokyo";
  const LIST_URL = "https://www.doorkeeper.jp/prefectures/tokyo/events";
  const LIST_PAGE_LIMIT = 10;
  const EVENT_REF = /^doorkeeper-event:\/\/event\/[1-9][0-9]*$/;
  const EVENT_URL = /^https:\/\/([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.doorkeeper\.jp\/events\/([1-9][0-9]*)$/;
  const TOKYO_VENUE_URL = "https://www.doorkeeper.jp/prefectures/tokyo";
  const OFFLINE_MODE = "https://schema.org/OfflineEventAttendanceMode";
  const IN_STOCK = "https://schema.org/InStock";
  ```

  Default listing reader rules:

  - navigate page 1 to `LIST_URL`, later pages to `${LIST_URL}?page=${page}` with `domcontentloaded`, 30 seconds;
  - read `.events-list-items-wrap`; each row returns title anchor href, `.events-list-item-time-date` text, and venue anchor href;
  - parse only exact `YYYY年M月D日`; preserve DOM order;
  - continue until no next page or the largest valid day reaches/exceeds the exclusive end day;
  - if a next page still exists after page 10 before reaching the end, throw `DOORKEEPER_DISCOVERY_PAGE_LIMIT_FAILED`;
  - detail navigation/read happens only after canonical dedup and exact Tokyo venue/window filtering.

  Default detail reader rules:

  - navigate the exact canonical URL on the same page;
  - read JSON-LD Event nodes, body text, and visible `a,button,input[type=submit]` labels;
  - require exact Event URL/id, valid start/end, offline mode, Tokyo address, every Offer exact/free/InStock/JPY, one visible exact `申し込む`, and no unavailable marker;
  - call `isCalendarFree` only after free/open eligibility;
  - order exact-covered candidates before unprocessed candidates, matching existing provider recovery behavior.

  Parent readback must compare candidate identity before returning `registered` or `absent`; all ambiguous states return `unavailable`.

- [x] **Step 6: Run GREEN and adjacent regression tests**

  Run:

  ```bash
  cd apps/mr-bot
  node --test lib/connector-doorkeeper-workflow.test.js
  node --test lib/connector-meetup-workflow.test.js lib/connector-peatix-workflow.test.js lib/connector-connpass-workflow.test.js
  node --check lib/connector-doorkeeper-workflow.js
  ```

  Expected: all tests PASS, zero warnings, zero external writes.

- [x] **Step 7: Self-review against the spec**

  Verify:

  - only the two owned files changed;
  - no provider routing/Harness/native/evidence/operations/schedule edits;
  - no API token, new dependency, agent/service/DB/cache/scheduler;
  - no private values in fixtures/output;
  - `git diff --check` is clean.

- [x] **Step 8: Commit the reviewed task**

  ```bash
  git add apps/mr-bot/lib/connector-doorkeeper-workflow.js apps/mr-bot/lib/connector-doorkeeper-workflow.test.js
  git commit -m "feat(connector): add Doorkeeper discovery workflow"
  ```

## Plan Self-Review

- Spec coverage: this slice covers public discovery, deterministic gates, Calendar conflict handling, five-count audit callback, parent state, and stable direct safe failure. Router/Harness/native/evidence/Calendar transport/live registration remain explicitly outside this task and require later slices.
- Placeholder scan: prohibited placeholder markers and unspecified error-handling steps are absent.
- Type consistency: workflow method names and candidate fields match `createProductionProviderRouter` and `runMinimalConnectorWake` contracts already used by Luma/Connpass/Peatix/Meetup.
- Ponytail result: existing runner, browser rail, Calendar logic, SHA identity rule, and workflow interface are reused; only the provider-specific parser/state reader is new.

## Result

- Luna implemented the workflow and observable tests in the two owned files only. Initial RED was `MODULE_NOT_FOUND`; final focused verification is 15/15 PASS.
- Fresh Sol review first found three Important contract gaps. Two bounded remediation rounds corrected the exact five-key audit, post-navigation URL identity checks, and unsafe-marker handling in both body and visible controls. Final verdict is spec PASS / code quality SHIP with no findings.
- Independent Sol verification reproduced focused 15/15 PASS, syntax PASS, `git diff --check` PASS, and exact two-file ownership. Adjacent suites are 48/49 because the same date-sensitive Peatix fixture fails on the unchanged base commit.
- Reviewed commits `f6c7e3eb4`, `d0078f05c`, and `fee320763` are pushed and fast-forwarded into `feature/connector-native-completion` at `fee320763`.
- This slice intentionally does not route Doorkeeper into production and does not submit. Production router/Harness/native/audit persistence and official live acceptance remain the next slice. All four Connector launchd labels remain unloaded.
