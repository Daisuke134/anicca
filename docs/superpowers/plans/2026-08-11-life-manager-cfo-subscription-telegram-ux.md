# CFO-2a3c.3a — Subscription Telegram Snapshot UX Plan

> Execute with Superpowers TDD. Sol owns spec/plan/verification; Luna owns the two implementation files.

**Goal:** Make one confirmed Anthropic subscription receipt a durable optional fact in the existing CFO snapshot and
show it in both the hourly Telegram summary and a tappable AI-cost detail view.

**Ponytail gate:** Extend the existing JSONB report and renderer only. JSONB needs no migration. Keep schema version 1
and accept old snapshots without `aiCost`. Do not add a table, RPC, sender, scheduler, source read, generic currency
framework, API forecast, or OpenAI receipt parser.

**Soft target:** exactly 2 existing files, at most 100 gross added LOC.

| Element | File | Soft target |
|---|---|---:|
| Optional schema + renderer/view/button | `apps/life-call/lib/cfo-telegram.js` | <= 55 LOC |
| Focused TDD | `apps/life-call/lib/cfo-telegram.test.js` | <= 45 LOC |

## Contract

`snapshot.aiCost` is optional so every persisted old snapshot remains valid. When present it must be an ordinary exact
eight-key object:

```js
{
  provider: "anthropic",
  plan: "max_20x",
  amount: "220.00",
  currency: "USD",
  billingPeriodStart: "2026-07-20",
  billingPeriodEnd: "2026-08-20",
  evidenceStatus: "provider_receipt",
  unavailableProviders: ["openai"]
}
```

This slice remains pinned to the reviewed receipt: provider/plan/amount/currency/evidence must equal those literals.
Both dates must be real YYYY-MM-DD dates and end must be later than start. `unavailableProviders` must be a dense,
ordinary, exact one-item array containing only `openai`; it means the OpenAI/Codex cash amount is unknown, never zero.
Before sanitizing or reading any value, validate the `aiCost` object and its nested array with `Reflect.ownKeys`, own
data descriptors, and exact prototypes. Unknown keys, symbols, accessors, custom prototypes, different values,
malformed dates, raw/private strings, sparse arrays, or array extras fail with a fixed
`cfo_telegram_invalid:invalid_ai_cost`. This new strict closed-shape promise is limited to `aiCost`; preserve the
existing legacy root sanitization behavior unchanged.

Add `ai_cost` to the closed view enum, callback parser, and summary button rows. Callback bytes remain <=64. Old
snapshots without `aiCost` render exactly as before and their existing buttons/callbacks stay valid.

Japanese summary, appended after the existing source/repair text and before the final action line:

```text
AI費用
Claude $220.00 / 月（領収書確認済み）
Codex 請求額未確認
```

English uses `AI costs`, `Claude $220.00 / month (receipt confirmed)`, and `Codex amount not confirmed`.
The section and AI button are present for every snapshot state when `aiCost` exists, including `action_required`; the
existing reconnect/action text remains visible. Both are absent when `aiCost` is absent.

The `ai_cost` detail view is available only when `aiCost` exists and contains only:

```text
AI費用
Claude Max 20x
支払 $220.00
期間 2026-07-20〜2026-08-20
根拠 領収書確認済み
Codex 請求額未確認
API換算 まだ計算していません
```

No record/body hash, Gmail/receipt/invoice ID, email, card, URL, path, raw body, provider error, or token estimate appears.
When `aiCost` is absent, no AI section is added and an `ai_cost` render request fails with fixed `invalid_ai_cost`.
The detail view has only a summary-back button; the summary has one `AI費用` button in addition to existing rows.

## Task 1 — RED

Modify only `apps/life-call/lib/cfo-telegram.test.js`.

Add `aiCostSnapshot()` by attaching the exact object above to `completeSnapshot()`. One compact success test asserts:

- summary contains the exact three Japanese lines;
- English summary contains the three English lines;
- `ai_cost` view contains plan, paid amount, period, evidence, Codex unknown, and forecast unavailable;
- summary keyboard contains exact callback `cfo:ai_cost:20260808:1`; detail has only summary-back;
- summary/detail contain none of fixed private sentinels or hash/URL/path patterns;
- a snapshot without `aiCost` is byte-for-byte unchanged from the current summary fixture and `ai_cost` fails fixed.

Add one compact invalid table for: extra key, wrong amount/currency/provider/plan/evidence, invalid/reversed date, wrong or
sparse/extra-key/symbol/accessor/custom-prototype unavailable array, and object accessor/symbol/custom prototype. Every
case must fail with exact `invalid_ai_cost` and no mutation/log. Validate before `sanitize()` can remove a private key.

Freeze the complete current no-`aiCost` `{ text, extra }` result as a literal expected value and deep-compare the whole
result, proving old summary bytes and keyboard are unchanged and contain no AI button. Also cover
`actionRequiredSnapshot()` plus `aiCost`: AI lines, reconnect text, and the conditional AI button must coexist.

Extend the existing callback-handler test with `cfo:ai_cost:20260810:1` and a fetched `report_payload.aiCost`. Assert the
exact snapshot query, returned `view: "ai_cost"`, edited AI detail text/keyboard, exactly one edit and one callback answer,
and zero send calls. This proves a tap re-renders the persisted fact rather than process memory.

Run:

```bash
cd apps/life-call
npm ci --no-audit --no-fund
node --test lib/cfo-telegram.test.js
```

Expected RED: new cases fail because `aiCost` and `ai_cost` are not accepted/rendered.

## Task 2 — GREEN

Modify only `apps/life-call/lib/cfo-telegram.js`. Add optional validation directly beside the existing closed snapshot
contract, extend the existing view/button/callback literals, and render the two small text blocks. Do not refactor
unrelated finance rendering or i18n files.

Run:

```bash
cd apps/life-call
node --test lib/cfo-telegram.test.js
npm run test:cfo
npm test
node --check lib/cfo-telegram.js
node --check lib/cfo-telegram.test.js
git diff --check
test "$(git status --short | awk '{print $2}' | LC_ALL=C sort)" = "$(printf '%s\n' lib/cfo-telegram.js lib/cfo-telegram.test.js)"
test "$(git diff --numstat -- lib/cfo-telegram.js lib/cfo-telegram.test.js | awk '{n += $1} END {print n + 0}')" -le 100
```

Expected GREEN: every gate passes; diff is exactly two files and <=100 gross additions.

## Task 3 — Sol verification and closure

Sol independently reruns all gates and a fresh Sol reviewer checks only false amounts, old-snapshot compatibility,
callback persistence, private leakage, and scope. Sol renders one actual persisted current snapshot in memory with the
real confirmed record mapped to `aiCost`, asserts only safe text/keyboard booleans, updates the child SSOT, commits,
pushes, and continues immediately to CFO-2a3c.3b. No Telegram or live snapshot write occurs in this slice.
