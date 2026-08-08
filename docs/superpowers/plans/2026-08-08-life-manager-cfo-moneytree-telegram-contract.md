# Life Manager CFO Moneytree Telegram Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze a pure, privacy-safe Japanese/English Telegram finance renderer for Moneytree-first CFO states before any scheduled source or send code is added.

**Architecture:** A closed normalized view model enters one pure CommonJS renderer. Copy lives in the existing i18n SSOT. The renderer formats four states and four drill-down views into Telegram HTML plus fixed inline callbacks; it performs no network, database, filesystem, or Moneytree work.

**Tech Stack:** Node.js 20+, CommonJS, `node:test`, Node standard library only, Telegram Bot API message shape.

## Global Constraints

- Parent design: `docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md`.
- Task 1–2 implementation scope is CFO-0d only. Do not implement Moneytree reads, persistence, Telegram sends, callback handlers, schedulers, business P&L, token cost, tax, spending advice, or Binance.
- RED must be observed before production edits in each task.
- No real balance, merchant, account identifier, path, token, payload, or user fixture may enter Git.
- Unknown is not zero. `partial` and `action_required` cannot render a complete-net-worth claim.
- `recovered` requires `repair.freshReread === true`, `repair.reconciled === true`, and every required source to be fresh; otherwise validation fails.
- Callback payloads contain only view, compact owner-local date, and revision; every payload is at most 64 UTF-8 bytes.
- No dependency additions.
- Only the current task's files are staged. Each task ends with focused tests, `git diff --check`, commit, and push.

## File Map and Size Targets

| File | Responsibility | Soft target |
|---|---|---:|
| `apps/life-call/lib/cfo-telegram.js` | Closed input validation, JPY/text formatting, view renderer, buttons | 170 production LOC |
| `apps/life-call/lib/cfo-telegram.test.js` | Four states/views, JA/EN, privacy, honesty, callback fixtures | 150 test LOC |
| `apps/life-call/lib/i18n.js` | CFO copy dictionary only | +55 production LOC |
| `apps/life-call/package.json` | Add one test file to existing `test:cfo` | +1 LOC |
| Parent/child specs and this plan | State/evidence update only | +12 documentation LOC |

The four-file total is split into two implementation commits; no implementation task edits more than three files. Task 1's measured summary contract is 106 LOC, leaving at most 64 LOC for all Task 2 views and buttons. Keeping one closed pure renderer avoids an extra module and cross-file state contract; this is the reason the single file may exceed 100 LOC. If either production file exceeds its soft target, stop and simplify before continuing.

## Closed Renderer Input

Use this exact synthetic shape in tests:

```js
{
  schemaVersion: 1,
  reportingDate: "2026-08-08",
  revision: 1,
  state: "complete", // complete | partial | recovered | action_required
  currency: "JPY",
  totals: {
    assetsMinor: 420000,
    liabilitiesMinor: 30000,
    netWorthMinor: 390000,
    changeMinor: 1200,
  },
  sources: [{
    sourceId: "moneytree_mufg",
    label: "三菱UFJ銀行",
    status: "fresh", // fresh | stale | unavailable
    asOf: "2026-08-08T06:02:00+09:00",
    amountMinor: 420000,
    verificationStatus: "provider_reported",
  }],
  excluded: [],
  repair: null,
  action: null,
}
```

For `partial`, at least one excluded item is required and `totals.netWorthMinor` must be `null`. For `action_required`, `action` is `{ kind: "reconsent", sourceLabel: "Moneytree", retryLabel: "接続後に自動再確認" }`; net worth remains `null`. For `recovered`, `repair` is `{ sourceLabel: "Moneytree", freshReread: true, reconciled: true }`.

Exports:

```js
renderCfoTelegram({ locale, view, snapshot }) => {
  text: string,
  extra: { reply_markup: { inline_keyboard: Array<Array<{ text, callback_data }>> } }
}

callbackData({ view, reportingDate, revision }) => string
evidenceLabel(locale, verificationStatus) => string
```

Allowed views are `summary`, `accounts`, `accuracy`, and `why`. Allowed evidence statuses are `provider_billed`, `provider_reported`, `locally_estimated`, and `unavailable`.

---

### Task 1: Truthful summary states and i18n copy

**Files:**
- Create: `apps/life-call/lib/cfo-telegram.test.js`
- Create: `apps/life-call/lib/cfo-telegram.js`
- Modify: `apps/life-call/lib/i18n.js`

**Interfaces:**
- Pure sync function; no dependency injection is needed because effects are forbidden.
- Amounts are integer JPY minor units and format with locale-aware grouping.
- All interpolated labels are Telegram-HTML escaped.

- [x] **Step 1: Write RED tests for all four states**

Start with a `completeSnapshot()` factory containing only synthetic values. Add these tests:

```js
test("complete Japanese summary answers amount, change, freshness, and action", () => {
  const result = renderCfoTelegram({ locale: "ja", view: "summary", snapshot: completeSnapshot() });
  assert.match(result.text, /今日のお金/);
  assert.match(result.text, /確認できた資産\s+¥420,000/);
  assert.match(result.text, /差し引き\s+¥390,000/);
  assert.match(result.text, /前回から\s+\+¥1,200/);
  assert.match(result.text, /三菱UFJ銀行/);
  assert.match(result.text, /今すること：ありません/);
});

test("partial and action-required never claim a complete net worth", () => {
  for (const snapshot of [partialSnapshot(), actionRequiredSnapshot()]) {
    const text = renderCfoTelegram({ locale: "ja", view: "summary", snapshot }).text;
    assert.doesNotMatch(text, /純資産/);
    assert.doesNotMatch(text, /¥0(?:\D|$)/);
    assert.match(text, /不明|合計に入れていません/);
  }
});

test("recovered is impossible without fresh reread and reconciliation", () => {
  const snapshot = recoveredSnapshot();
  snapshot.repair.freshReread = false;
  assert.throws(
    () => renderCfoTelegram({ locale: "ja", view: "summary", snapshot }),
    /^Error: cfo_telegram_invalid:recovery_unproven$/,
  );
});

test("English summary uses the same facts without technical language", () => {
  const text = renderCfoTelegram({ locale: "en", view: "summary", snapshot: completeSnapshot() }).text;
  assert.match(text, /Today.s money/);
  assert.match(text, /Confirmed assets\s+JPY 420,000/);
  assert.match(text, /Nothing right now/);
});
```

Also assert:

- `totals` values must be safe integers or `null`; strings, `NaN`, and floats fail.
- reporting date is exact `YYYY-MM-DD`; revision is a positive integer.
- stale/unavailable source with `complete` or `recovered` fails closed.
- `partial` requires an excluded label and null net worth.
- `action_required` requires an action and null net worth.
- recovered text contains a short repair note but no stack/error/debug vocabulary.

- [x] **Step 2: Run RED**

```bash
cd apps/life-call
node --test lib/cfo-telegram.test.js
```

Expected: FAIL because `./cfo-telegram.js` does not exist.

- [x] **Step 3: Add the smallest CFO i18n dictionary**

Append one `CFO_STRINGS` object to `lib/i18n.js` and export it. Keep sentences as plain-language fragments rather than prebuilt HTML. Minimum keys:

```js
const CFO_STRINGS = Object.freeze({
  ja: Object.freeze({
    title: "💰 今日のお金",
    confirmedAssets: "確認できた資産",
    confirmedLiabilities: "確認できた負債",
    confirmedDifference: "差し引き",
    change: "前回から",
    noAction: "今すること：ありません",
    partialTitle: "⚠️ 確認できた範囲のお金",
    excluded: "合計に入れていません",
    recovered: "✅ 更新の問題を自動修復し、最新データを再確認しました。",
    actionTitle: "🔐 Moneytreeの接続を1回だけ更新してください",
    unknown: "不明",
  }),
  en: Object.freeze({
    title: "💰 Today’s money",
    confirmedAssets: "Confirmed assets",
    confirmedLiabilities: "Confirmed liabilities",
    confirmedDifference: "Difference",
    change: "Since last report",
    noAction: "Action now: Nothing right now",
    partialTitle: "⚠️ Money I could confirm",
    excluded: "Not included in the total",
    recovered: "✅ I repaired the update and confirmed fresh data again.",
    actionTitle: "🔐 Reconnect Moneytree once",
    unknown: "Unknown",
  }),
});
```

Add only the remaining fragments needed by the tested output. Do not add business, token, tax, spending, or Binance copy.

- [x] **Step 4: Implement strict validation and summary rendering**

Use small closed constants and formatters:

```js
const STATES = new Set(["complete", "partial", "recovered", "action_required"]);
const VIEWS = new Set(["summary", "accounts", "accuracy", "why"]);
const EVIDENCE = Object.freeze({
  provider_billed: { ja: "確定", en: "Confirmed" },
  provider_reported: { ja: "実測", en: "Measured" },
  locally_estimated: { ja: "推定", en: "Estimated" },
  unavailable: { ja: "不明", en: "Unknown" },
});

function formatAmount(locale, value) {
  if (value == null) return CFO_STRINGS[locale].unknown;
  return locale === "ja"
    ? `¥${new Intl.NumberFormat("ja-JP").format(value)}`
    : `JPY ${new Intl.NumberFormat("en-US").format(value)}`;
}
```

Validation reads only the closed fields above. It rejects unsupported locale/view/state/currency, unsafe integers, missing sources, inconsistent state data, and unproven recovery. Escape `&`, `<`, and `>` in every interpolated label. Do not include `JSON.stringify(snapshot)` or raw errors in the result.

- [x] **Step 5: Run GREEN and size check**

```bash
cd apps/life-call
node --test lib/cfo-telegram.test.js
wc -l lib/cfo-telegram.js
cd ../..
git diff --check
```

Expected: Task 1 tests pass; production module is at or below 120 LOC before Task 2; diff check exits zero.

- [x] **Step 6: Commit and push Task 1**

```bash
git add apps/life-call/lib/cfo-telegram.js apps/life-call/lib/cfo-telegram.test.js apps/life-call/lib/i18n.js
git commit -m "feat(cfo): render truthful Telegram summaries"
git push
```

---

### Task 2: Drill-down callbacks, privacy fixtures, and normal test wiring

**Files:**
- Modify: `apps/life-call/lib/cfo-telegram.test.js`
- Modify: `apps/life-call/lib/cfo-telegram.js`
- Modify: `apps/life-call/package.json`

- [x] **Step 1: Add RED tests for the four views and privacy boundary**

```js
test("all drill-down callbacks are deterministic and at most 64 bytes", () => {
  for (const view of ["summary", "accounts", "accuracy", "why"]) {
    const result = renderCfoTelegram({ locale: "ja", view, snapshot: completeSnapshot() });
    for (const row of result.extra.reply_markup.inline_keyboard) {
      for (const button of row) {
        assert.ok(Buffer.byteLength(button.callback_data, "utf8") <= 64);
        assert.match(button.callback_data, /^cfo:(summary|accounts|accuracy|why):20260808:1$/);
      }
    }
  }
});

test("drill-downs explain accounts and evidence without private payload fields", () => {
  const snapshot = completeSnapshot();
  snapshot.sources[0].label = "三菱UFJ銀行 <普通預金>";
  snapshot.sources[0].accountNumber = "1234567";
  snapshot.rawPayload = { credential: "secret-value" };
  const outputs = ["summary", "accounts", "accuracy", "why"]
    .map((view) => renderCfoTelegram({ locale: "ja", view, snapshot }));
  const serialized = JSON.stringify(outputs);
  assert.doesNotMatch(serialized, /1234567|secret-value|rawPayload|credential/);
  assert.match(outputs[1].text, /&lt;普通預金&gt;/);
  assert.match(outputs[2].text, /実測/);
  assert.match(outputs[3].text, /資産.*負債/s);
});

test("fixed callback builder rejects invalid view, date, and revision", () => {
  assert.equal(callbackData({ view: "accounts", reportingDate: "2026-08-08", revision: 1 }), "cfo:accounts:20260808:1");
  assert.throws(() => callbackData({ view: "connect", reportingDate: "2026-08-08", revision: 1 }), /^Error: cfo_telegram_invalid:/);
});
```

Also assert every non-summary view has a route back to `summary`, evidence status labels round-trip in Japanese and English, unavailable amounts render `不明/Unknown`, and no output contains the words `stack`, `exception`, `JSON`, `payload`, or `token`.

- [x] **Step 2: Run RED**

```bash
cd apps/life-call
node --test lib/cfo-telegram.test.js
```

Expected: FAIL because drill-down rendering and/or callback exports are incomplete.

- [x] **Step 3: Implement fixed callbacks and four views**

Use the one compact format:

```js
function callbackData({ view, reportingDate, revision }) {
  if (!VIEWS.has(view) || !/^\d{4}-\d{2}-\d{2}$/.test(reportingDate) || !Number.isInteger(revision) || revision < 1) {
    throw new Error("cfo_telegram_invalid:callback");
  }
  const value = `cfo:${view}:${reportingDate.replaceAll("-", "")}:${revision}`;
  if (Buffer.byteLength(value, "utf8") > 64) throw new Error("cfo_telegram_invalid:callback_too_long");
  return value;
}
```

The renderer builds buttons from view names, not caller-supplied callback strings. `accounts` shows each redacted label, amount or Unknown, and freshness. `accuracy` shows the four evidence labels and source `asOf`. `why` states that the confirmed difference is confirmed assets minus confirmed liabilities and names excluded items. In `partial`/`action_required`, call it a confirmed subtotal/difference, never complete net worth.

- [x] **Step 4: Wire into the existing CFO and normal test path**

Change only `test:cfo`:

```json
"test:cfo": "node --test lib/cfo-registry.test.js lib/cfo-inventory.test.js lib/cfo-telegram.test.js scripts/cfo-business-inventory.test.js"
```

Because `pretest` already calls `npm run test:cfo`, no second test hook is added.

- [x] **Step 5: Verify focused and regression paths**

```bash
cd apps/life-call
npm run test:cfo
npm test
cd ../..
git diff --check
```

Expected: all CFO tests and the full package test pass; no network or Telegram send occurs.

- [x] **Step 6: Fresh review**

A fresh read-only reviewer checks only the Task 1–2 diff against the approved child spec. Required questions:

1. Can stale, partial, or unavailable input produce a complete-net-worth claim?
2. Can `recovered` render without fresh reread and reconciliation proof?
3. Can caller data enter `callback_data` or leak private fields?
4. Are the four views readable and deterministic in both locales?
5. Did the implementation add any effect, abstraction, or later-milestone scope?

Fix Critical/Important findings with RED → GREEN and repeat this focused review once. Do not create a generic code-review stage.

- [x] **Step 7: Close CFO-0d, commit, and push**

Update:

- this plan's checkboxes and observed test counts,
- child spec CFO-0d acceptance checkboxes,
- parent spec `CFO-0d` checkbox and first unfinished item to `CFO-1a`.

Then:

```bash
git add apps/life-call/lib/cfo-telegram.js apps/life-call/lib/cfo-telegram.test.js apps/life-call/package.json \
  docs/superpowers/plans/2026-08-08-life-manager-cfo-moneytree-telegram-contract.md \
  docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md \
  docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md
git commit -m "feat(cfo): freeze Moneytree Telegram contract"
git push
```

Completion means a pure, tested UI contract only. It is not a real Moneytree sync or Telegram delivery. The next active item is CFO-1a.

### Task 1–2 closure evidence

Task 1 committed as `a42839db7` and was reviewed Approved. Task 2 committed as `d85aaca6d`; review-round 1 found one Important exclusion-display issue, fixed with RED → GREEN in `38d34993d`, and the scoped re-review was Approved. Focused renderer verification is 13/13, CFO verification is 48/48, and the full package is 680/680 after the existing lockfile dependency install. This closes the pure UI contract only: no Moneytree sync and no real finance Telegram message has been delivered. The next active item is CFO-1a.
