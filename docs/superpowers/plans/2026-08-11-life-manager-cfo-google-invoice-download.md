# CFO-2a3.2b1 — Google Invoice Private Download Plan

> Workflow: Ponytail full → Superpowers TDD. Sol plans/verifies; Luna owns production/test edits.

**Goal:** Add the smallest read-only boundary that downloads the already-located Google invoice PDF to a
caller-owned private path and returns only safe transfer metadata. Parsing, hashing, persistence, scheduler wiring,
and Telegram remain outside this slice.

**Observed contract:** A real authenticated local probe of
`gog gmail attachment <messageId> <attachmentId> --out=<path> -j --gmail-no-send` created a non-empty `%PDF` file
with mode `0600` and returned JSON with exactly `bytes`, `cached`, and `path`. The probe used a private temporary
directory and removed it immediately; no identifier, filename, path, or amount was printed or committed.

**Ponytail full decision**

1. Do not add a generic attachment service, downloader class, retry system, filesystem abstraction, parser,
   receipt store, scheduler, DB, OpenTelemetry, or Telegram behavior.
2. Reuse the existing authenticated `makeGogMail` transport, its injected command runner, and the locator contract.
3. Use only Node's native `path` module for path validation.
4. Change two existing files only. Soft target: <= 20 production LOC and <= 35 test LOC; stop and reduce scope if
   either target or two files is exceeded materially.

## Task 1: RED

Add exactly two focused tests to `apps/life-call/lib/cfo-google-invoice-mail.test.js`:

1. a valid locator and absolute `.pdf` path issue exactly one fixed read-only command and return frozen
   `{ bytes, cached }`, without returning the path or identifiers;
2. one table-driven test returns `null` without throw/log for absent account, invalid locator IDs/source, unsafe or
   relative output path, command failure, invalid JSON, path mismatch, non-positive/non-integer bytes, or non-boolean
   cached value.

Run the focused test and record the expected missing-method failure.

## Task 2: GREEN

Add one method to the existing `makeGogMail` return object:

`downloadGoogleCloudInvoice(locator, outPath)` → frozen `{ bytes, cached }` or `null`.

Rules:

- require the configured account, the locator's exact source `google_cloud_invoice_gmail`, a hex message ID, a
  base64url attachment ID, and an absolute `.pdf` output path without NUL/newline characters;
- issue exactly one command:
  `gmail attachment <messageId> <attachmentId> --out=<outPath> -j --gmail-no-send`;
- accept only JSON whose `path` equals the requested path, `bytes` is a positive safe integer, and `cached` is a
  boolean;
- freeze and return only `{ bytes, cached }`; catch every command/data error and return `null`;
- do not stat, read, hash, parse, delete, persist, retry, schedule, or send anything in this transport method.

Run the focused file, `npm run test:cfo`, and full `npm test`.

## Task 3: REVIEW AND CLOSE

Fresh Sol review checks only command argv/count, injection boundaries, fail-closed behavior, privacy, and YAGNI.
The same Luna fixes required findings. Sol independently reruns focused/CFO/full tests plus syntax/diff/LOC checks,
then performs one real local download into a private temporary directory, verifies non-empty PDF magic and mode
`0600` without printing private values, removes the temporary content, updates both specs, commits, and pushes.

