# CFO-2a3.2b2 — Google Invoice Local Parse and Immutable Append Plan

> Workflow: Ponytail full → Superpowers TDD. Sol plans/verifies; Luna owns production/test/package edits.

**Goal:** Compose the completed locator/download boundary, the installed `pdftotext`, the existing invoice
normalizer, and the repository's content-addressed local-state convention into one truthful confirmed Google Cloud
invoice record. A rerun of the same PDF converges to the existing immutable record.

**Observed real format:** The current Japanese Google invoice is three pages. Safe local probes proved one
`アカウント ID` token shaped as three uppercase-alphanumeric groups of six, two Japanese service-period dates
immediately after that row, internally consistent duplicate `小計`/`消費税`/`合計` amounts, JPY markers, a
month-start/month-end period, and exact `subtotal + tax = total`. No account, date, amount, text, or path was printed
or committed.

**Ponytail full decision**

1. Do not add a generic invoice/parser/storage framework, OCR, LLM parsing, PDF library, DB, retry system,
   reconciliation scheduler, OpenTelemetry, or Telegram behavior.
2. Reuse `makeGogMail` locator/download, native `crypto/fs/os/path/child_process`, installed `pdftotext`,
   `normalizeGoogleCloudInvoice`, and the existing 0700-directory/0600-file/content-addressed state convention.
3. Accept only the one observed Japanese Google layout. An unknown provider/layout fails with a fixed redacted
   error; it is never guessed into a financial amount.
4. Maximum three files. Soft targets: <= 85 production LOC, <= 85 test LOC, and one package-script token. If either
   code target is exceeded, stop and split before adding abstractions.

## Contract

Create `captureLatestGoogleCloudInvoice({ stateRoot, observedAt, mail, runText })`:

- `stateRoot` is an absolute non-root local state path; `observedAt` is RFC3339; `mail` provides the completed
  locator/download methods; optional `runText(pdfPath)` defaults to one
  `pdftotext -layout <private-pdf> -` process;
- return a deeply frozen exact receipt
  `{ status: "appended" | "existing", record_id: "sha256:<pdf-sha256>", confirmed }`;
- throw only fixed `cfo_google_invoice_capture_invalid:<reason>` errors and never log raw input/error data.

The immutable file is exactly the normalized `confirmed` JSON at:

`<stateRoot>/cfo/provider-billing/google-cloud/<pdf-sha256>.json`

All directories are `0700`; the file is `0600`. The PDF hash is the stable source identity. On rerun, read the
existing file, reproduce its normalized form using its original `observed_at`, and require byte-identical canonical
JSON before returning `existing`; never rewrite it.

## Task 1: RED

Create one focused test file with exactly two tests and register it once in `test:cfo`:

1. synthetic observed-layout text plus a private synthetic `%PDF` proves parse → normalize → append, exact frozen
   receipt, hashed-only stored evidence, modes, temporary cleanup, and a later rerun returning the same immutable
   record with `status = existing` and one file only;
2. one table-driven test proves source/download/PDF/text/arithmetic failures and a pre-existing conflicting record
   fail closed with fixed redacted errors, no new final record, no rewrite, and temporary cleanup.

Run the focused test before production creation and record the exact missing-module RED.

## Task 2: GREEN

Create only `apps/life-call/lib/cfo-google-invoice-local-source.js`:

1. make one private `0700` temporary directory and use the mail locator/download exactly once;
2. require a regular non-empty `0600` file, transfer-byte equality, and `%PDF` magic; hash the actual bytes;
3. extract text once and accept only:
   - one account ID matching `[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}` on the `アカウント ID` row;
   - exactly two Japanese dates in that row plus the next three lines, same year/month, first day 1 and second day
     the actual month end;
   - at least one Yen amount for each of `小計`, `消費税`, and `合計`, with every repeated value identical;
   - JPY markers on subtotal and total rows and canonical non-negative integer Yen values;
4. call `normalizeGoogleCloudInvoice`; raw account/text/PDF never enters the record;
5. append or validate the immutable content-addressed record, fsync the file and directory on first append;
6. always remove private temporary content in `finally`; add no scheduler or Telegram wiring.

Run focused, `npm run test:cfo`, and full `npm test`.

## Task 3: REVIEW AND CLOSE

Fresh Sol review checks only observed-format truth, arithmetic, raw-data exclusion, immutability/dedupe, cleanup,
failure redaction, and YAGNI. The same Luna fixes required findings. Sol independently reruns focused/CFO/full,
syntax/diff/LOC checks, then performs one real no-send/no-publish E2E in an isolated state root: actual PDF → actual
`pdftotext` → normalized record, verify PDF arithmetic via independent safe booleans, rerun dedupe, record modes,
raw-data absence, and cleanup. Remove the isolated state root after inspection, update specs, commit, and push.

