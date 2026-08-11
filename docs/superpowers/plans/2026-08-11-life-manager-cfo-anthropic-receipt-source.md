# CFO-2a3c.1 — Anthropic Gmail Source Implementation Plan

> Execute with Superpowers TDD. Sol owns this plan/spec and verification; Luna owns the two implementation files.

**Goal:** Read the newest successful official Anthropic subscription receipt through the existing authenticated
`gog` transport and return one frozen memory-only evidence object without logging, persistence, or external writes.

**Ponytail gate:** Reuse `makeGogMail` and its injected `run` boundary. Do not add a module, dependency, abstraction,
scheduler, parser, store, retry, browser path, Moneytree path, or Telegram change.

**Soft target:** exactly 2 existing files, at most 60 gross added LOC total.

| Element | File | Soft target |
|---|---|---:|
| Transport method | `apps/life-call/lib/transport/mail-gog.js` | <= 27 added LOC |
| Focused TDD | `apps/life-call/lib/cfo-google-invoice-mail.test.js` | <= 33 added LOC |

## Contract

Add `readLatestAnthropicSubscriptionReceipt()` to the object returned by `makeGogMail`.

It issues exactly these three read-only commands when a valid hit exists:

```js
[
  ["gmail", "messages", "search",
   'from:(mail.anthropic.com) subject:"Your receipt from Anthropic, PBC" newer_than:400d',
   "-j", "--max=10", "--gmail-no-send"],
  ["gmail", "raw", "<validated hex message id>", "-j", "--gmail-no-send"],
  ["gmail", "get", "<validated hex message id>", "-j", "--format=full", "--sanitize-content",
   "--gmail-no-send"],
]
```

Search candidates are accepted only when:

- `id` is nonempty hexadecimal;
- `from` contains one syntactically valid address whose domain is exactly `mail.anthropic.com`;
- `subject` exactly matches `Your receipt from Anthropic, PBC #dddd-dddd-dddd`;
- `date` is a valid local minute accepted by the existing `parseReceiptInterval`;
- candidates are sorted by date descending and only the newest valid candidate is authenticated and fetched.

The raw Gmail API result must have `payload.headers` as an array and exactly one top-level
`Authentication-Results` header. Its value must start with `mx.google.com;` and contain both:

```text
dkim=pass ... header.i=@mail.anthropic.com OR header.d=mail.anthropic.com
dmarc=pass ... header.from=mail.anthropic.com
```

Matching is case-insensitive and limited to each semicolon-delimited authentication clause. SPF alone is
insufficient. A missing, duplicate, non-Google, failed, relaxed-domain, or malformed authentication result returns
`null` before the sanitized body is fetched.

The fetched JSON must be an ordinary object with a nonempty string `body` of at most 20,000 characters. Its `headers`
must repeat the selected `from` and `subject`. Success returns a deeply frozen exact three-key object:

```js
{
  source: "anthropic_subscription_receipt_gmail",
  receivedAtLocal: "YYYY-MM-DD HH:mm",
  body: "<sanitized memory-only body>"
}
```

The method returns `null` for absent account, command failure, invalid JSON, no valid hit, sender/subject/date mismatch,
authentication failure, get-header mismatch, missing/empty/oversized body, or any other malformed result. It never logs,
sends, retries, persists, or returns raw command errors. Receipt/invoice IDs remain only inside the memory-only body
for CFO-2a3c.2 and are never asserted from the real account in tests or output.

## Task 1 — RED

Modify only `apps/life-call/lib/cfo-google-invoice-mail.test.js`.

Add one success test using synthetic values:

```js
const ANTHROPIC_QUERY = 'from:(mail.anthropic.com) subject:"Your receipt from Anthropic, PBC" newer_than:400d';
const anthropicHit = (id, date, from = "Anthropic, PBC <receipt@mail.anthropic.com>",
  subject = "Your receipt from Anthropic, PBC #1234-5678-9012") => ({ id, date, from, subject });
```

Return one older valid hit, one newer invalid-domain hit, and one newest valid hit. Return a synthetic raw Gmail object
with exactly one `mx.google.com` Authentication-Results header containing strict DKIM and DMARC pass clauses. Assert
the exact three commands,
exact three-key frozen result, and that the body is the exact injected sanitized synthetic body.

Add one compact table test covering: absent account, search failure/invalid JSON, all hits invalid, raw failure/invalid
JSON, duplicate/non-Google/missing/failing/relaxed-domain authentication, get failure/invalid JSON, mismatched fetched
sender, empty body, and oversized body. Assert `null` and
zero logs for every case. Do not test internal combinations that cannot change money truth, data loss, duplicate
external effects, or secret exposure.

Run from `apps/life-call`:

```bash
node --test lib/cfo-google-invoice-mail.test.js
```

Expected RED: the success test fails only because `readLatestAnthropicSubscriptionReceipt` does not exist.

## Task 2 — GREEN

Modify only `apps/life-call/lib/transport/mail-gog.js`. Reuse `parseReceiptInterval`, the existing `exec` closure, and
the Google source's address extraction/sort pattern. Implement the contract directly in the returned object. Do not
refactor the existing Google methods.

Run:

```bash
node --test lib/cfo-google-invoice-mail.test.js
npm run test:cfo
npm test
node --check lib/transport/mail-gog.js
node --check lib/cfo-google-invoice-mail.test.js
git diff --check
```

Expected GREEN: all gates pass; diff contains exactly the two planned files and at most 60 gross additions.

## Task 3 — Sol verification and closure

Sol independently reruns every GREEN gate, inspects the exact diff and working-tree ownership, and performs one real
read-only probe through `makeGogMail`. The probe asserts only source, frozen/exact keys, nonempty body, exact Google
DKIM/DMARC authentication, and that the body contains the already-observed plan/amount/arithmetic tokens. It must not print the body,
Gmail ID, receipt/invoice number, email, payment method, URLs, or amount. Then update the child SSOT with measured
evidence, commit, push, and continue immediately to CFO-2a3c.2.
