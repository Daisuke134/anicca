# CFO-2a3.3b1 — Provider Billing Hourly Counts Summary Plan

> Workflow: Ponytail full → Superpowers TDD. Sol plans/verifies; Luna owns production/test/package edits.

**Goal:** Call the completed local Google invoice capture from the existing hourly entrypoint and add one exact
counts-only `providerBilling` object to its local stdout/return value. Moneytree finance and Telegram continue even
when provider billing is unavailable.

**Truth boundary:** A captured Google invoice is `provider_billed`, but it is still unreconciled to the existing
Life-Manager-only USD provisional estimate because scope and currency do not match. Therefore a successful latest
invoice publishes `confirmedCount = 1` and `unresolvedCount = 1`. It does not publish a reconciled business cost.

**Ponytail full decision**

1. Do not add a runner/service/queue/DB/OTel pipeline/retry/self-heal loop, another state file, Telegram wording,
   amount output, or launchd edit.
2. Reuse `scripts/cfo-hourly-local.js`, `makeGogMail`, `captureLatestGoogleCloudInvoice`, its immutable state, the
   existing single hourly clock, and the existing redacted stdout summary.
3. OpenTelemetry remains the request/token correlation path. The provider invoice's immutable record remains its
   billing truth; this slice only exposes aggregate collection status to the hourly control loop.
4. Maximum three existing files. Soft targets: <= 35 added production LOC, <= 55 added test LOC, and one `test:cfo`
   registration token. Stop and reduce scope before exceeding them.

## Contract

The hourly `main()` return gains one deeply frozen/exact object:

```json
{
  "providerBilling": {
    "status": "confirmed_unresolved | unavailable",
    "confirmedCount": 1,
    "unresolvedCount": 1,
    "unavailableCount": 0
  }
}
```

The same `providerBilling` object is added to the one local stdout JSON object. It never enters the Moneytree
snapshot or Telegram delivery input.

- `confirmed_unresolved`: the capture receipt is exact enough to prove one Google `provider_billed` JPY invoice,
  its record/source refs match, and its amount is a canonical non-negative integer string. Counts are `1/1/0`.
- `unavailable`: account configuration is absent, capture throws, or the receipt is invalid. Counts are `0/0/1`.
- No amount, currency total, hash, record ID, scope ref, account, Gmail locator, path, provider error, or secret is
  included in stdout or the public summary.
- Billing failure never blocks the existing Moneytree read, snapshot, or Telegram report and never changes the
  finance exit code.

## Task 1: RED

Modify `scripts/cfo-hourly-local.test.js` with the minimum two behavior proofs:

1. with configured local Gmail and injected capture/mail seams, `main` uses one clock, calls usage → billing →
   finance, passes only the resolved local state root/observed time/mail to capture, and emits exact `1/1/0` counts
   without amount/IDs in stdout or Telegram input;
2. missing configuration, thrown capture, and malformed receipt each emit exact `0/0/1`, preserve the finance
   result/delivery, and redact hostile error/data. Keep variants table-driven and retain existing tests.

Register the existing hourly test file once in `test:cfo`. Run its focused test before production edits and record
the exact missing `providerBilling` RED.

## Task 2: GREEN

Modify only `scripts/cfo-hourly-local.js`:

- import native `os/path`, the existing `makeGogMail`, and completed capture;
- resolve state root from `LIFE_MANAGER_STATE_HOME`, otherwise `~/.local/state/life-manager`;
- evaluate `options.now` once in `main`, pass that same Date to billing and `runHourlyCfo`;
- when `GOG_ACCOUNT` is configured, call the injected/default capture once with the injected/default mail;
- validate only the load-bearing confirmed receipt fields, reduce to the exact counts object, and freeze it;
- on every absent/invalid/error path return `unavailable` without logging or forwarding the raw failure;
- add counts only to stdout and `main()` return; leave `runHourlyCfo`, Moneytree snapshot, Telegram input, and exit-code
  logic unchanged.

Run focused, `npm run test:cfo`, and full `npm test`.

## Task 3: REVIEW AND CLOSE

Fresh Sol review checks count truth, one clock/capture, state-root resolution, finance isolation, redaction, and YAGNI.
The same Luna fixes required findings. Sol independently reruns focused/CFO/full plus syntax/diff/LOC, performs an
isolated real `main()` E2E with Telegram delivery injected to no-send, verifies exact counts and one immutable record,
updates specs, commits, and pushes. No launchd change in b1; CFO-2a3.3b2 owns live cutover and rollback proof.

