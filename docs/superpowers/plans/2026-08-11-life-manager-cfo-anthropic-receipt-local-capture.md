# CFO-2a3c.2 — Anthropic Receipt Local Capture Plan

> Execute with Superpowers TDD. Sol owns this plan/spec and verification; Luna owns production/test/package changes.

**Goal:** Convert the authenticated, sanitized Anthropic receipt evidence from CFO-2a3c.1 into one exact, secret-free,
immutable local subscription-cost record.

**Ponytail gate:** Reuse the existing Gmail evidence method and the Google invoice source's stdlib-only hash-addressed
storage pattern. Do not add a generic parser/store, database, dependency, scheduler, browser, Moneytree call,
OpenTelemetry span, retry, or Telegram change.

**Soft target:** exactly 3 files and at most 100 gross added LOC.

| Element | File | Soft target |
|---|---|---:|
| Parser + immutable store | `apps/life-call/lib/cfo-anthropic-receipt-local-source.js` | <= 48 LOC |
| Focused TDD | `apps/life-call/lib/cfo-anthropic-receipt-local-source.test.js` | <= 51 LOC |
| Durable suite registration | `apps/life-call/package.json` | 1 token/line edit |

## Contract

Export `captureLatestAnthropicSubscriptionReceipt({ stateRoot, mail })`.

`stateRoot` must be a canonical absolute non-root path with no NUL/newline. `mail` must expose
`readLatestAnthropicSubscriptionReceipt`. The function calls that method exactly once. `null` is
`cfo_anthropic_receipt_capture_invalid:source_unavailable`. Evidence must have exactly the frozen three-key
CFO-2a3c.1 shape: `source`, `receivedAtLocal`, `body`; the source is
`anthropic_subscription_receipt_gmail`, the local minute is valid, and body is nonempty and at most 20,000 chars.

Parse only the one observed single-receipt Stripe text layout. Each labeled fact below must occur exactly once:

```text
Receipt from Anthropic, PBC $<total> Paid <Month D, YYYY>
<Mon D>–<Mon D, YYYY> Max plan - 20x Qty 1 $<subtotal>
Subtotal $<subtotal>
Total excluding tax $<subtotal>
JCT - Japan (10%) $<tax>
Total $<total>
Amount paid $<total>
```

The en dash is literal. English month names are closed. The billing start must equal the paid date; the end must be
the same day in the immediately following calendar month. Every amount has exactly two decimals, converts to a safe
integer minor value, and obeys `plan price = subtotal = total excluding tax`, `tax = subtotal * 10%`, and
`subtotal + tax = header total = Total = Amount paid`. `$` maps to `USD` only for this exact authenticated template;
Sol's real E2E must independently re-prove that the same receipt's official invoice PDF contains `USD`. Any layout,
symbol, plan, quantity, period, duplicate label, or arithmetic change fails closed. This first closed template also
requires `subtotal === 200.00`, `tax === 20.00`, and every total/paid value `=== 220.00`; even a different internally
consistent amount fails with `receipt_amount` until a newer official invoice is reviewed and the contract is revised.

The normalized record has exactly these recursively frozen keys and string values:

```js
{
  schema_version: "lm_subscription_receipt_v1",
  provider: "anthropic",
  plan: "max_20x",
  billing_period_start: "YYYY-MM-DD",
  billing_period_end: "YYYY-MM-DD",
  subtotal: "200.00",
  tax: "20.00",
  total: "220.00",
  currency: "USD",
  paid_date: "YYYY-MM-DD",
  source_hash: "sha256:<64 lowercase hex>",
  evidence_status: "provider_receipt"
}
```

`source_hash` is SHA-256 over the exact UTF-8 sanitized body. Store JSON at
`<stateRoot>/cfo/provider-billing/anthropic/<hash>.json`; directories are `0700`, the file is `0600`, the file and
directory are fsynced, and an existing same path is accepted only when mode and bytes equal the rebuilt exact record.
Use a unique `0600` temporary file plus hard-link publication, as the existing Google source does; always remove the
temporary on every result. Never persist or return raw body, received-local time, email, Gmail ID, receipt/invoice
number, payment method, URLs, or arbitrary text.

Success returns a recursively frozen exact three-key receipt:

```js
{ status: "appended" | "existing", record_id: "sha256:<hash>", confirmed: <exact normalized record> }
```

All errors are fixed and redacted:

```text
cfo_anthropic_receipt_capture_invalid:<invalid_input|source_unavailable|receipt_format|receipt_period|receipt_amount|record_conflict|capture_failed|cleanup_failed>
```

No error includes provider/body/path/ID/amount text; no logs, retries, provider writes, or external sends.

## Task 1 — RED

Create `apps/life-call/lib/cfo-anthropic-receipt-local-source.test.js` and add only its filename to the existing
`test:cfo` command in `package.json`.

Use a private `mkdtemp` state root and one synthetic receipt body containing fake receipt/invoice/payment/email/URL
sentinels plus the exact observed labels. The normal test asserts first `appended`, rerun `existing`, one source call
per capture, exact record and receipt keys/values, recursive freeze, one byte-identical JSON file, `0600` file,
`0700` directories, and absence of every sentinel/raw-body fragment from record/receipt/path.

Add one compact money-truth table for wrong plan, wrong next-month period, duplicate amount label, unsafe/invalid
amount, tax mismatch, total mismatch, an internally consistent but unapproved `210.00 + 21.00 = 231.00` price, and
unavailable source. Assert exact fixed error only, zero logs, and no final record. Add one existing-file conflict case
proving the original bytes are preserved and the fixed conflict error is returned. Do not add internal-shape
combinations unrelated to money truth, data loss, or secret exposure.

Run:

```bash
node --test lib/cfo-anthropic-receipt-local-source.test.js
```

Expected RED: failure only because the new module/export is absent.

## Task 2 — GREEN

Create only `apps/life-call/lib/cfo-anthropic-receipt-local-source.js`. Keep parsing and storage direct and local;
copy/tweak the proven small Google source patterns without refactoring it. Implement the exact contract and make the
focused test pass.

Run:

```bash
node --test lib/cfo-anthropic-receipt-local-source.test.js
npm run test:cfo
npm test
node --check lib/cfo-anthropic-receipt-local-source.js
node --check lib/cfo-anthropic-receipt-local-source.test.js
git diff --check
```

Expected GREEN: all gates pass; diff is exactly the two new files plus `package.json`, with at most 100 gross additions.

## Task 3 — Sol verification and closure

Sol independently reruns every gate and a fresh Sol reviewer checks only false spend, arithmetic, data loss, secret
leakage, and scope. Sol then runs one real authenticated E2E against an isolated private state root: capture twice,
prove `appended` then `existing`, exact current period/plan/amount record, one byte-identical `0600` file and `0700`
directories, no private tokens, and full cleanup. In the same read-only E2E, independently fetch the authenticated
email's official invoice PDF to a `0700` temporary directory, prove `%PDF`, ISO `USD`, and matching paid amount, and
delete it. Print only booleans/counts; never print raw values, IDs, paths, URLs, body, or PDF text. Then update the child
SSOT, commit, push, and continue immediately to CFO-2a3c.3.
